"""Ablation: predict the team directly with a 7-class model, or by summing intent probabilities.

Run with `python -m sanket.models.ablation`. Prints numbers only; the result is logged by hand
in docs/EXPERIMENTS.md. The shipped design does not change with the result.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression

from sanket.models.baseline import BaselineModel, BaselineParams
from sanket.models.evaluate import load_split
from sanket.routing.thresholds import team_matrix
from sanket.taxonomy import TEAM_NAMES, team_of


def main() -> None:
    """Fit both team predictors on train and report team accuracy on val and test."""
    train, val, test = load_split("train"), load_split("val"), load_split("test")
    params = BaselineParams(C=5, use_char=True)
    model = BaselineModel.fit(train["text"].tolist(), train["intent"].tolist(), params)
    y_train = [team_of(i) for i in train["intent"]]
    direct = LogisticRegression(C=params.C, max_iter=300, random_state=42)
    direct.fit(model._features(train["text"].tolist()), y_train)
    for name, df in (("val", val), ("test", test)):
        texts = df["text"].tolist()
        true = np.array([team_of(i) for i in df["intent"]])
        summed = np.array(TEAM_NAMES)[team_matrix(model.predict_proba(texts)).argmax(axis=1)]
        direct_pred = direct.predict(model._features(texts))
        print(f"{name}: summed {np.mean(summed == true):.4f}  direct {np.mean(direct_pred == true):.4f}")


if __name__ == "__main__":
    main()
