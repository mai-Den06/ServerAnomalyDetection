from abc import ABC, abstractmethod
import pandas as pd

class BaseDetector(ABC):
    @abstractmethod
    def fit(self, df: pd.DataFrame) -> "BaseDetector":
        ...

    @abstractmethod
    def score(self, df: pd.DataFrame) -> pd.Series:
        """高いほど異常"""
        ...
