from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FeatureFrame:
    """Container for engineered features.

    `X` should be a tabular structure suitable for model inference.
    For now this is typed as `Any` to avoid forcing a hard dependency in
    import-time for developer tooling.
    """

    X: Any
    meta: dict[str, Any]


def build_features_from_history(history_df: Any, *, ticker: str) -> FeatureFrame:
    """Build a minimal feature set from a historical price dataframe.

    This is infrastructure-only and does not implement any business logic.
    """

    # Keep this implementation deliberately lightweight.
    # The Prediction Engine can expand these features later.
    import pandas as pd  # local import to keep import-time side effects low

    if history_df is None or len(history_df) == 0:
        X = pd.DataFrame()
    else:
        df = history_df.copy()
        # Basic numeric feature examples.
        if "close" in df.columns:
            df["close_return_1"] = df["close"].pct_change()
        X = df

    return FeatureFrame(X=X, meta={"ticker": ticker})

