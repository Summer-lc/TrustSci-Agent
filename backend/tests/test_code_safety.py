import pytest

from app.tools.code_safety import UnsafeGeneratedCode, validate_generated_model


def test_allows_numpy_and_sklearn_model() -> None:
    validate_generated_model("import numpy as np\nfrom sklearn.linear_model import LogisticRegression\nclass SeismicModel: pass")


@pytest.mark.parametrize("source", ["import os\nos.system('whoami')", "open('x').read()", "eval('1+1')"])
def test_rejects_dangerous_generated_code(source: str) -> None:
    with pytest.raises(UnsafeGeneratedCode):
        validate_generated_model(source)
