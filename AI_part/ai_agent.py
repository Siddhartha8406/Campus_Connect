import os
import sys
import json
import warnings
from typing import Dict, Any, List

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib

MODEL_PATH = os.path.join(os.getcwd(), "models", "best_model_pipeline.joblib")

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

NUMERIC_FEATURES = {
    "AttendanceRate",
    "StudyHoursPerWeek",
    "PreviousGrade",
    "ExtracurricularActivities",
    "Study Hours",
    "Attendance (%)",
}

CATEGORICAL_FEATURES = {"Gender", "Online Classes Taken"}


def load_model(path: str = MODEL_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model not found: {path}")
    return joblib.load(path)


def _build_input_df(input_map: Dict[str, Any]) -> pd.DataFrame:
    row = {}
    for feat in REQUESTED_INPUTS:
        if feat in input_map:
            row[feat] = input_map[feat]
        else:
            row[feat] = "missing" if feat in CATEGORICAL_FEATURES else np.nan

    df = pd.DataFrame([row], columns=REQUESTED_INPUTS)

    # coerce numeric columns
    for n in NUMERIC_FEATURES:
        if n in df.columns:
            df[n] = pd.to_numeric(df[n], errors="coerce")

    # ensure categorical columns are strings
    for c in CATEGORICAL_FEATURES:
        if c in df.columns:
            df[c] = df[c].astype(str).fillna("missing")

    # --- add engineered features used at training time ---
    # 1) Study_x_Attendance (StudyHoursPerWeek * AttendanceRate)
    if "StudyHoursPerWeek" in df.columns and "AttendanceRate" in df.columns:
        df["Study_x_Attendance"] = df["StudyHoursPerWeek"].fillna(0) * df["AttendanceRate"].fillna(0)

    # 2) Study_dup_diff (StudyHoursPerWeek - Study Hours)
    if "StudyHoursPerWeek" in df.columns and "Study Hours" in df.columns:
        df["Study_dup_diff"] = df["StudyHoursPerWeek"].fillna(0) - df["Study Hours"].fillna(0)

    # 3) Avg_Study_Hours (average of the two study-hour columns when available)
    if "StudyHoursPerWeek" in df.columns or "Study Hours" in df.columns:
        a = df["StudyHoursPerWeek"] if "StudyHoursPerWeek" in df.columns else pd.Series([np.nan])
        b = df["Study Hours"] if "Study Hours" in df.columns else pd.Series([np.nan])
        df["Avg_Study_Hours"] = pd.concat([a, b], axis=1).mean(axis=1).fillna(0)

    # 4) Effort_Ratio (simple ratio: StudyHoursPerWeek / (PreviousGrade + 1) — avoid div by zero)
    if "StudyHoursPerWeek" in df.columns:
        prev = df["PreviousGrade"] if "PreviousGrade" in df.columns else pd.Series([np.nan])
        df["Effort_Ratio"] = df["StudyHoursPerWeek"].fillna(0) / (prev.fillna(0) + 1)

    # --- end engineered features ---

    return df


def _get_feature_names_from_preprocessor(preprocessor) -> List[str]:
    try:
        names = list(preprocessor.get_feature_names_out())
        return names
    except Exception:
        names = []
        try:
            for name, trans, cols in preprocessor.transformers_:
                if trans == "passthrough":
                    names.extend(cols)
                    continue
                try:
                    sub = trans
                    if hasattr(sub, "named_steps") and "onehot" in sub.named_steps:
                        ohe = sub.named_steps["onehot"]
                        try:
                            ohe_names = list(ohe.get_feature_names_out(input_features=cols))
                        except Exception:
                            ohe_names = list(ohe.get_feature_names_out())
                        names.extend(ohe_names)
                    elif hasattr(sub, "get_feature_names_out"):
                        names.extend(list(sub.get_feature_names_out()))
                    else:
                        names.extend(cols)
                except Exception:
                    names.extend(cols)
        except Exception:
            names = []
        return names


def predict_and_explain(model, input_map: Dict[str, Any]) -> float:
    df = _build_input_df(input_map)
    pred = model.predict(df)[0]
    pred = float(np.clip(round(float(pred), 2), 0.0, 100.0))
    return pred


def predict_from_params(
    gender: Any = None,
    attendance_rate: Any = None,
    study_hours_per_week: Any = None,
    previous_grade: Any = None,
    extracurricular_activities: Any = None,
    study_hours: Any = None,
    attendance_percent: Any = None,
    online_classes_taken: Any = None,
) -> float:
    input_map: Dict[str, Any] = {}
    if gender is not None:
        input_map["Gender"] = gender
    if attendance_rate is not None:
        input_map["AttendanceRate"] = attendance_rate
    if study_hours_per_week is not None:
        input_map["StudyHoursPerWeek"] = study_hours_per_week
    if previous_grade is not None:
        input_map["PreviousGrade"] = previous_grade
    if extracurricular_activities is not None:
        input_map["ExtracurricularActivities"] = extracurricular_activities
    if study_hours is not None:
        input_map["Study Hours"] = study_hours
    if attendance_percent is not None:
        input_map["Attendance (%)"] = attendance_percent
    if online_classes_taken is not None:
        input_map["Online Classes Taken"] = online_classes_taken

    model = load_model(MODEL_PATH)
    prediction = predict_and_explain(model, input_map)
    print("" + str(prediction))
    return prediction





if __name__ == "__main__":
    #predict_from_params(gender, attendance_rate, study_hours_per_week, 
    # previous_grade, extracurricular_activities, study_hours, attendance_percent, 
    # online_classes_taken)

    predict_from_params("Female",91.0,15.0,88.0,2.0,2.8,74.0,False) //87.0
    predict_from_params("Female",88.0,8.0,70.0,3.0,3.6,58.0,True) //62.0