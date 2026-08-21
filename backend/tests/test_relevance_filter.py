from app.agents.baseline_discovery_agent import _is_relevant_repo


def test_relevance_filter_keeps_seismic_repos() -> None:
    assert _is_relevant_repo({"full_name": "a/seismic-cnn", "description": "CNN for seismic event classification"}) is True
    assert _is_relevant_repo({"full_name": "smousavi05/STEAD", "description": "earthquake dataset + model"}) is True
    assert _is_relevant_repo({"full_name": "a/EQTransformer", "description": "attention model for earthquakes"}) is True


def test_relevance_filter_drops_cross_domain_noise() -> None:
    assert _is_relevant_repo({"full_name": "a/DeepSentiPers", "description": "persian sentiment nlp"}) is False
    assert _is_relevant_repo({"full_name": "a/COVID-Lung", "description": "covid lung segmentation"}) is False
    assert _is_relevant_repo({"full_name": "a/Recommender", "description": "recommendation systems"}) is False


def test_relevance_filter_drops_no_positive_keyword() -> None:
    assert _is_relevant_repo({"full_name": "a/foo", "description": "a generic ML repo"}) is False
