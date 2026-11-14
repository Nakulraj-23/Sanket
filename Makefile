PY := .venv/bin/python
SITE := .venv/lib/python3.11/site-packages
SANKET_TORCH_SITE ?= /home/user/prahari/.venv/lib/python3.11/site-packages

.PHONY: setup link-torch data seed train train-nn bench retrain serve web test lint replay space-bundle

setup:
	python3.11 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

link-torch:
	@if [ -d "$(SANKET_TORCH_SITE)" ]; then \
	  echo "$(SANKET_TORCH_SITE)" > $(SITE)/_torch_link.pth; \
	  $(PY) -c "import torch, onnx, numpy, sklearn; print('torch', torch.__version__)"; \
	  $(PY) -c "import numpy, sklearn; assert '/sanket/.venv/' in numpy.__file__ and '/sanket/.venv/' in sklearn.__file__; print('numpy and sklearn load from this venv')"; \
	else echo "torch site not found: $(SANKET_TORCH_SITE)"; fi

data:
	@if [ -f sanket/pipeline/split.py ]; then $(PY) -m sanket.pipeline.split; else echo "not built yet"; fi

seed:
	@if [ -f scripts/seed.py ]; then $(PY) scripts/seed.py; else echo "not built yet"; fi

train:
	@if [ -f sanket/models/train_baseline.py ]; then $(PY) -m sanket.models.train_baseline; else echo "not built yet"; fi

train-nn:
	@if [ -f sanket/models/nn/train.py ]; then $(PY) -m sanket.models.nn.train; else echo "not built yet"; fi

bench:
	@if [ -f sanket/bench.py ]; then $(PY) -m sanket.bench; else echo "not built yet"; fi

retrain:
	@if [ -f sanket/retrain.py ]; then $(PY) -m sanket.retrain; else echo "not built yet"; fi

serve:
	@if [ -f sanket/api/app.py ]; then $(PY) -m uvicorn sanket.api.app:app --port $${PORT:-8000}; else echo "not built yet"; fi

web:
	@if [ -f web/package.json ]; then cd web && npm run dev; else echo "not built yet"; fi

test:
	$(PY) -m pytest -q

lint:
	.venv/bin/ruff check .

replay:
	@if [ -f scripts/make_replay.py ]; then $(PY) scripts/make_replay.py; else echo "not built yet"; fi

space-bundle:
	@if [ -f scripts/space_bundle.py ]; then $(PY) scripts/space_bundle.py; else echo "not built yet"; fi
