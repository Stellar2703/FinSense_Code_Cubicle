from app.services.utils import anomaly_ratio

def test_anomaly_ratio():
    # normal
    is_anom, r = anomaly_ratio(9000, 8000)
    assert is_anom is False
    # anomaly 10x
    is_anom, r = anomaly_ratio(80000, 8000)
    assert is_anom is True
