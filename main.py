from fastapi import FastAPI

app = FastAPI()


def hitung_subnet(ip: str, prefix: int) -> dict:
    raise NotImplementedError
