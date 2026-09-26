import pytest

from sample_data.fake_dataset import build_fake_dataset
from sample_data.fake_suggestion_list import build_fake_suggestions


@pytest.fixture
def sample_df():
    return build_fake_dataset()


@pytest.fixture
def sample_suggestions():
    return build_fake_suggestions()


def suggestion_by_id(suggestions, suggestion_id):
    return next(s for s in suggestions if s["id"] == suggestion_id)
