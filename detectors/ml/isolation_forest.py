import pandas as pd
from sklearn.ensemble import IsolationForest

from detectors.base_detector import BaseDetector

class IsolationForestDetector(BaseDetector):

    def __init__(self, n_estimators=200, max_samples="auto",
                 contamination="auto", random_state=42):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.random_state = random_state

    def fit(self, df: pd.DataFrame) -> "BaseDetector":
        self.columns_ = df.columns
        self.model_ = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            contamination=self.contamination,
            random_state=self.random_state
        )
        self.model_.fit(df)
        return self

    def score(self, df: pd.DataFrame) -> pd.Series:
        X = df[self.columns_]
        scores = - self.model_.decision_function(X)
        return pd.Series(scores, index=df.index, name="if_anomaly_score")
