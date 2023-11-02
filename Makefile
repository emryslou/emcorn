test_init:
	python -m pip install -r tests/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
tests:
	python -m pytest tests/test*