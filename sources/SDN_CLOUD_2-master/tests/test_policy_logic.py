from ml.common import one_hot_prediction


def test_one_hot_prediction():
    mapping = one_hot_prediction("congestion")
    assert mapping["congestion"] == 1
    assert sum(mapping.values()) == 1
