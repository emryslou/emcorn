import emcorn

class TestInit(object):
    def test_demo(self, demo):
        assert emcorn.__version__ == '0.0.1'
