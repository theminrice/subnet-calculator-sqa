

## Docker

Build image:

    docker build -t subnet-calculator .

Jalankan container:

    docker run -d --name subnet-app -p 8000:8000 subnet-calculator

Smoke test ke container lokal:

    uv run python scripts/smoke_test.py http://127.0.0.1:8000

Hentikan dan hapus container:

    docker rm -f subnet-app


## Deploy

URL produksi: https://subnet-calculator-sqa-xi.vercel.app

Smoke test:

    uv run python scripts/smoke_test.py https://subnet-calculator-sqa-xi.vercel.app
