import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

INDEX_HTML = Path(__file__).resolve().parent / "index.html"
POLA_OKTET = re.compile(r"[0-9]{1,3}")
POLA_PREFIX_API = re.compile(r"0|[1-9][0-9]*")


def _ip_ke_int(ip) -> int:
    if not isinstance(ip, str):
        raise ValueError("Alamat IP harus berupa teks.")
    oktet = ip.split(".")
    if len(oktet) != 4:
        raise ValueError("Alamat IP harus terdiri dari tepat 4 oktet yang dipisah titik.")
    nilai = 0
    for o in oktet:
        if not POLA_OKTET.fullmatch(o):
            raise ValueError(
                "Alamat IP tidak valid: tiap oktet hanya boleh berisi angka 0-9, "
                "tanpa spasi atau karakter lain."
            )
        if len(o) > 1 and o.startswith("0"):
            raise ValueError("Alamat IP tidak valid: oktet tidak boleh diawali angka nol.")
        if int(o) > 255:
            raise ValueError("Alamat IP tidak valid: tiap oktet harus bernilai 0 sampai 255.")
        nilai = (nilai << 8) | int(o)
    return nilai


def _int_ke_ip(nilai: int) -> str:
    return ".".join(str((nilai >> geser) & 255) for geser in (24, 16, 8, 0))


def hitung_subnet(ip: str, prefix: int) -> dict:
    ip_int = _ip_ke_int(ip)
    if not isinstance(prefix, int) or isinstance(prefix, bool):
        raise ValueError("Prefix harus berupa bilangan bulat.")
    if not 0 <= prefix <= 32:
        raise ValueError("Prefix harus bernilai 0 sampai 32.")

    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    network = ip_int & mask
    broadcast = network | (~mask & 0xFFFFFFFF)

    if prefix == 32:
        first, last, usable, bcast = ip_int, ip_int, 1, None
    elif prefix == 31:
        first, last, usable, bcast = network, network + 1, 2, None
    else:
        first, last = network + 1, broadcast - 1
        usable, bcast = 2 ** (32 - prefix) - 2, _int_ke_ip(broadcast)

    return {
        "mask": _int_ke_ip(mask),
        "network": _int_ke_ip(network),
        "broadcast": bcast,
        "first_host": _int_ke_ip(first),
        "last_host": _int_ke_ip(last),
        "usable_hosts": usable,
    }


def _galat(pesan: str) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": pesan})


@app.exception_handler(RequestValidationError)
async def _validasi_ke_400(request: Request, exc: RequestValidationError):
    return _galat("Permintaan tidak valid.")


@app.get("/api/subnet")
def api_subnet(ip: str | None = None, prefix: str | None = None):
    try:
        if ip is None:
            raise ValueError("Parameter ip wajib diisi.")
        if prefix is None:
            raise ValueError("Parameter prefix wajib diisi.")
        if not POLA_PREFIX_API.fullmatch(prefix) or len(prefix) > 3:
            raise ValueError("Prefix harus berupa bilangan bulat 0 sampai 32, tanpa angka nol di depan.")
        return hitung_subnet(ip, int(prefix))
    except ValueError as e:
        return _galat(str(e))


@app.get("/", response_class=HTMLResponse)
def halaman():
    return INDEX_HTML.read_text(encoding="utf-8")


def alokasi_vlsm(network_cidr: str, kebutuhan_host: list[int]) -> list[dict]:
    raise NotImplementedError


@app.post("/api/vlsm")
def api_vlsm():
    raise NotImplementedError
