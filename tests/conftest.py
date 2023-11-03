import pytest
from emcorn.http import HttpParser

@pytest.fixture
def http_parser():
    return HttpParser()

