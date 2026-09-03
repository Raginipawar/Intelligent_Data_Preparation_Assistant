import pytest

from sample_data.fake_health_report import build_fake_health_report


@pytest.fixture
def health_report():
    return build_fake_health_report()
