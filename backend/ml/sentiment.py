from __future__ import annotations
from typing import List, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


DEFAULT_SEED = [
    ("great quality and fast delivery", 1),
    ("excellent product highly recommend", 1),
    ("very satisfied and happy", 1),
    ("bad quality and slow shipping", 0),
    ("terrible experience not recommended", 0),
    ("very disappointed and unhappy", 0),
]


def train_and_predict(train_samples: List[Dict[str, Any]] | None, texts: List[str]) -> Dict[str, Any]:
    # If no training data provided, fall back to a tiny default seed
    if not train_samples:
        train_samples = [{"text": t, "label": y} for t, y in DEFAULT_SEED]

    X_train = [r.get("text", "") for r in train_samples]
    y_train = [int(r.get("label", 0)) for r in train_samples]

    vec = TfidfVectorizer(max_features=2000, ngram_range=(1,2))
    Xtr = vec.fit_transform(X_train)
    clf = LogisticRegression(max_iter=300)
    clf.fit(Xtr, y_train)

    Xte = vec.transform(texts)
    probs = clf.predict_proba(Xte) if hasattr(clf, 'predict_proba') else None
    preds = clf.predict(Xte)

    out = []
    for i, p in enumerate(preds):
        score = float(probs[i, 1]) if probs is not None else float(p)
        out.append({
            "text": texts[i],
            "label": int(p),
            "score": score
        })

    return {"results": out, "meta": {"classes": [0,1]}}
