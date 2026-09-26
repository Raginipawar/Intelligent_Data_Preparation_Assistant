"""
test_recommend_engine.py — Tests candidate algorithm ranking and reasoning generation.
"""
from app.meta_features import MetaFeatures
from app.recommend_engine import rank_recommendations
from app.recommend_schemas import TaskType


def test_classification_ranking():
    mf = MetaFeatures(
        n_rows=5000,
        n_columns=10,
        n_features=9,
        feature_to_sample_ratio=0.0018,
        task_type=TaskType.BINARY_CLASSIFICATION,
        target_column="churn",
        n_numerical=7,
        n_categorical=2,
        class_imbalance_ratio=1.5,
    )
    recs = rank_recommendations(mf)
    assert len(recs) == 7
    assert recs[0].rank == 1
    assert recs[0].recommendation_score >= recs[1].recommendation_score
    # Verify reasoning present
    assert len(recs[0].reasoning) > 0


def test_regression_ranking():
    mf = MetaFeatures(
        n_rows=200,
        n_columns=5,
        n_features=4,
        feature_to_sample_ratio=0.02,
        task_type=TaskType.REGRESSION,
        target_column="price",
        n_numerical=4,
    )
    recs = rank_recommendations(mf)
    assert len(recs) == 7
    assert any("Ridge" in r.algorithm for r in recs)
