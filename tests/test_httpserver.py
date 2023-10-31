from emcorn import httpserver

class TestHttpServer(object):
    def test_demo(self):
        import time
        def app():
            for _ in range(10):
                print('app ....')
                time.sleep(0.4)
        srv = httpserver.HttpServer(app, 2).join()