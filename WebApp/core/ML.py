import os
import sys
import warnings
from pathlib import Path
from typing import Dict, List

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import cross_val_score, RandomizedSearchCV, KFold
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, StackingRegressor

CSV_DEFAULT = os.path.join(os.getcwd(), "student_performance_updated_1000.csv")
MODEL_DIR = os.path.join(os.getcwd(), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "best_model_pipeline.joblib")

# Input columns requested by you (use only these if present in CSV)
REQUESTED_INPUTS = [
    "Gender",
    "AttendanceRate",
    "StudyHoursPerWeek",
    "PreviousGrade",
    "ExtracurricularActivities",
    "Study Hours",
    "Attendance (%)",
    "Online Classes Taken",
]
TARGET = "FinalGrade"

# Common aliases to help locate columns in the provided CSV
ALIASES = {
    "Gender": ["Gender", "gender"],
    "AttendanceRate": ["AttendanceRate", "Attendance Rate", "AttendanceRate%", "Attendance (%)", "Attendance"],
    "StudyHoursPerWeek": ["StudyHoursPerWeek", "Study Hours", "Study_Hours", "StudyHours"],
    "PreviousGrade": ["PreviousGrade", "Previous_Grade", "Previous Grade", "Previous_Exam_Score", "PreviousGrade"],
    "ExtracurricularActivities": ["ExtracurricularActivities", "Extracurricular Activities", "Extracurricular"],
    "Study Hours": ["Study Hours"],
    "Attendance (%)": ["Attendance (%)"],
    "Online Classes Taken": ["Online Classes Taken", "Online_Classes_Taken", "OnlineClassesTaken", "Online Classes Taken"],
    "FinalGrade": ["FinalGrade", "Final Grade", "Final_Grade"],
}


def find_first_existing(col_list, candidates):
    for c in candidates:
        if c in col_list:
            return c
    return None


def load_and_select_features(csv_path):
    df = pd.read_csv(csv_path)
    cols = df.columns.tolist()

    # Build rename mapping to canonical names requested
    rename_map = {}
    for req in REQUESTED_INPUTS + [TARGET]:
        cand = ALIASES.get(req, [req])
        found = find_first_existing(cols, cand)
        if found:
            rename_map[found] = req

    df = df.rename(columns=rename_map)

    # Ensure target exists
    if TARGET not in df.columns:
        raise RuntimeError(f"Target column '{TARGET}' not found in CSV. Available columns: {cols}")

    # Select only requested input columns that exist
    features = [c for c in REQUESTED_INPUTS if c in df.columns]
    if not features:
        raise RuntimeError("None of the requested input features were found in the CSV after alias resolution.")

    # Drop rows with missing target
    df = df.dropna(subset=[TARGET]).copy()

    # Convert numeric-like columns to numeric
    numeric_candidates = [
        "AttendanceRate",
        "StudyHoursPerWeek",
        "PreviousGrade",
        "ExtracurricularActivities",
        "Study Hours",
        "Attendance (%)",
    ]
    for col in numeric_candidates:
        if col in df.columns:
            # Coerce errors to NaN, which will be handled by the SimpleImputer in the pipeline
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Ensure categorical columns are strings
    for col in ["Gender", "Online Classes Taken"]:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("missing")

    # Cast target to float
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    df = df.dropna(subset=[TARGET]).copy() # Drop NaNs introduced by coercion

    return df, features


def make_onehot_safe():
    # Helper to handle sklearn API changes for sparse output
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)
    except TypeError:
        try:
            return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        except TypeError:
            return OneHotEncoder(handle_unknown="ignore")


def build_preprocessor(numeric_features, categorical_features):
    num_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="mean")),
            ("scaler", StandardScaler()),
        ]
    ) if numeric_features else "passthrough"

    ohe = make_onehot_safe()
    cat_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", ohe),
        ]
    ) if categorical_features else "passthrough"

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipeline, numeric_features),
            ("cat", cat_pipeline, categorical_features),
        ],
        remainder="drop",
        sparse_threshold=0,
    )
    return preprocessor


def select_and_train(df, features):
    X = df[features].copy()
    y = df[TARGET].astype(float)

    # 1. Feature Engineering
    if "StudyHoursPerWeek" in X.columns and "PreviousGrade" in X.columns:
        X["Effort_Ratio"] = X["StudyHoursPerWeek"].fillna(0) / (X["PreviousGrade"].replace(0, 1).fillna(100))
    if "StudyHoursPerWeek" in X.columns and "Study Hours" in X.columns:
        X["Avg_Study_Hours"] = (X["StudyHoursPerWeek"].fillna(0) + X["Study Hours"].fillna(0)) / 2
        X = X.drop(columns=["StudyHoursPerWeek", "Study Hours"], errors='ignore')

    # Update feature lists
    all_features = list(X.columns)
    numeric_feats = []
    categorical_feats = []
    for f in all_features:
        if f in {"PreviousGrade", "ExtracurricularActivities", "AttendanceRate", "Attendance (%)", "Effort_Ratio", "Avg_Study_Hours"}:
            numeric_feats.append(f)
        else:
            categorical_feats.append(f)

    preprocessor = build_preprocessor(numeric_feats, categorical_feats)

    # 2. Candidate Estimators and Hyperparameter Search
    pipelines_and_params = []

    rf = RandomForestRegressor(random_state=42)
    rf_pipeline = Pipeline([("preprocessor", preprocessor), ("regressor", rf)])
    rf_param_dist = {
        "regressor__n_estimators": [300, 500],
        "regressor__max_depth": [10, 20, None],
        "regressor__min_samples_split": [5, 10],
    }
    pipelines_and_params.append(("RandomForest", rf_pipeline, rf_param_dist))

    hgb = HistGradientBoostingRegressor(random_state=42)
    hgb_pipeline = Pipeline([("preprocessor", preprocessor), ("regressor", hgb)])
    hgb_param_dist = {
        "regressor__learning_rate": [0.05, 0.1],
        "regressor__max_iter": [200, 400],
        "regressor__max_depth": [6, 12, None],
    }
    pipelines_and_params.append(("HistGradientBoosting", hgb_pipeline, hgb_param_dist))

    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    best_models = {}
    best_score = -np.inf

    print("Starting Randomized Hyperparameter Search for Base Models (20 Iterations each)...")

    for name, pipeline, params in pipelines_and_params:
        try:
            search = RandomizedSearchCV(
                pipeline,
                param_distributions=params,
                n_iter=20,
                scoring="r2",
                cv=cv,
                n_jobs=-1,
                random_state=42,
                verbose=0,
            )
            search.fit(X, y)
            best_models[name] = search.best_estimator_
            print(f"  {name} Best R2: {search.best_score_:.4f}")
            if search.best_score_ > best_score:
                best_score = search.best_score_
        except Exception as e:
            print(f"Error during {name} tuning: {e}")

    # 3. Build final model: use stacking properly (estimators are pipelines that include preprocessing)
    final_model = None
    selected_name = None

    if len(best_models) >= 2:
        try:
            print("\nTraining Stacking Regressor (will fit base pipelines internally)...")
            estimators = [(n, best_models[n]) for n in best_models.keys()]
            stacking_regressor = StackingRegressor(
                estimators=estimators,
                final_estimator=RandomForestRegressor(n_estimators=100, random_state=42),
                cv=5,
                n_jobs=-1,
                passthrough=False,
            )
            # stacking_regressor expects raw X and will call fit on each pipeline (which include preprocessing)
            stacking_regressor.fit(X, y)
            final_model = stacking_regressor
            selected_name = "Stacking-Tuned"
            # evaluate stacking via CV for reporting
            try:
                stack_scores = cross_val_score(stacking_regressor, X, y, cv=cv, scoring="r2", n_jobs=-1)
                stack_mean_score = float(np.nanmean(stack_scores))
                if stack_mean_score > best_score:
                    best_score = stack_mean_score
            except Exception:
                pass
        except Exception as e:
            print(f"Stacking failed, falling back to best single model: {e}")
            # fallback to best single tuned pipeline
            if best_models:
                selected_name = max(best_models.keys(), key=lambda k: 0)  # pick any
                final_model = best_models[selected_name]
            else:
                final_model = Pipeline([("preprocessor", preprocessor), ("regressor", RandomForestRegressor(random_state=42))])
                final_model.fit(X, y)
                selected_name = "Fallback-RF"
    else:
        # only one tuned base model found
        selected_name = list(best_models.keys())[0] if best_models else "Fallback-RF"
        final_model = best_models[selected_name] if best_models else Pipeline([("preprocessor", preprocessor), ("regressor", RandomForestRegressor(random_state=42))])
        final_model.fit(X, y)

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)

    return {"model_name": selected_name, "cv_r2": best_score, "model_path": MODEL_PATH, "features": all_features, "final_pipeline": final_model}


def calculate_feature_importance(pipeline_or_model, X, features):
    """Robust feature importance extraction for pipeline or stacking regressor."""
    try:
        # If we have a Pipeline with preprocessor, use it to get feature names and the regressor
        if isinstance(pipeline_or_model, Pipeline):
            preproc = pipeline_or_model.named_steps.get('preprocessor', None)
            reg = pipeline_or_model.named_steps.get('regressor', None)
            # get feature names where possible
            try:
                preproc.fit(X)
                feature_names = list(preproc.get_feature_names_out())
            except Exception:
                feature_names = features
            if hasattr(reg, 'feature_importances_'):
                importances = reg.feature_importances_
            else:
                print("\nCould not extract feature importances from the pipeline regressor.")
                return
        else:
            # StackingRegressor or other estimator
            model = pipeline_or_model
            # Try to use first fitted base estimator as proxy for importances
            try:
                first_est = model.estimators_[0]
                # if first_est is a pipeline, extract its regressor and preprocessor to get names
                if isinstance(first_est, Pipeline):
                    preproc = first_est.named_steps.get('preprocessor', None)
                    reg = first_est.named_steps.get('regressor', None)
                    try:
                        preproc.fit(X)
                        feature_names = list(preproc.get_feature_names_out())
                    except Exception:
                        feature_names = features
                    if hasattr(reg, 'feature_importances_'):
                        importances = reg.feature_importances_
                    else:
                        print("\nCould not extract importances from base estimator in stacking model.")
                        return
                else:
                    # if not a pipeline, we cannot reliably map importance to feature names here
                    print("\nStacking base estimator is not a pipeline; skipping feature importance.")
                    return
            except Exception as e:
                print(f"\nFailed to extract feature importance from stacking model: {e}")
                return

        importance_df = pd.DataFrame({'Feature': feature_names, 'Importance': importances})
        importance_df = importance_df.sort_values(by='Importance', ascending=False)
        print("\n--- TOP 5 FEATURE IMPORTANCES (Post-Preprocessing) ---")
        print(importance_df.head(5).to_string(index=False))
        print("-------------------------------------------------------")
    except Exception as e:
        print(f"Error calculating feature importance: {e}")


def main(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df, features = load_and_select_features(csv_path)
    result = select_and_train(df, features)
    print(f"\n--- TRAINING SUMMARY ---")
    print(f"Saved best model '{result['model_name']}' with CV R2={result['cv_r2']:.4f} -> {result['model_path']}")
    
    # Calculate and display feature importance using the final model and original data
    calculate_feature_importance(result['final_pipeline'], df[features], features)
    print("\nNext steps: Check feature importances to see which variables drive prediction.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else CSV_DEFAULT
    main(path)