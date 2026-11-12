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


def _parse_network_induk(network_cidr) -> tuple[int, int]:
    if not isinstance(network_cidr, str):
        raise ValueError("Network induk harus berupa teks dengan format a.b.c.d/p.")
    bagian = network_cidr.split("/")
    if len(bagian) != 2:
        raise ValueError("Network induk harus berformat a.b.c.d/p dan prefix wajib ada.")
    ip_teks, prefix_teks = bagian
    if not POLA_PREFIX_API.fullmatch(prefix_teks) or len(prefix_teks) > 3:
        raise ValueError("Network induk: prefix harus berupa bilangan bulat tanpa angka nol di depan.")
    prefix = int(prefix_teks)
    if prefix > 30:
        raise ValueError("Network induk: prefix harus 0 sampai 30 (blok terkecil adalah /30).")
    ip_int = _ip_ke_int(ip_teks)
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    if ip_int & mask != ip_int:
        raise ValueError(
            f"Network induk bukan alamat network yang tepat: seharusnya {_int_ke_ip(ip_int & mask)}/{prefix}."
        )
    return ip_int, prefix


def alokasi_vlsm(network_cidr: str, kebutuhan_host: list[int]) -> list[dict]:
    awal, prefix_induk = _parse_network_induk(network_cidr)
    if not isinstance(kebutuhan_host, list) or not kebutuhan_host:
        raise ValueError("Kebutuhan host harus berupa daftar yang tidak kosong.")
    for k in kebutuhan_host:
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("Kebutuhan host harus berupa bilangan bulat minimal 1.")

    urutan = sorted(kebutuhan_host, reverse=True)  # sort stabil: urutan input dipertahankan
    ukuran = [max(4, 1 << (k + 1).bit_length()) for k in urutan]
    if sum(ukuran) > 2 ** (32 - prefix_induk):
        raise ValueError(
            f"Kebutuhan host tidak muat di network {_int_ke_ip(awal)}/{prefix_induk}: "
            f"dibutuhkan {sum(ukuran)} alamat, tersedia {2 ** (32 - prefix_induk)}."
        )

    hasil, alamat = [], awal
    for k, u in zip(urutan, ukuran):
        prefix = 32 - (u.bit_length() - 1)
        blok = hitung_subnet(_int_ke_ip(alamat), prefix)
        hasil.append({"kebutuhan": k, "network_cidr": f"{blok['network']}/{prefix}", **blok})
        alamat += u
    return hasil


@app.post("/api/vlsm")
async def api_vlsm(request: Request):
    try:
        isi = await request.json()
    except ValueError:
        return _galat("Body harus berupa JSON yang valid.")
    if not isinstance(isi, dict):
        return _galat("Body harus berupa objek JSON dengan field network dan kebutuhan_host.")
    for nama in ("network", "kebutuhan_host"):
        if nama not in isi:
            return _galat(f"Field {nama} wajib diisi.")
    try:
        return alokasi_vlsm(isi["network"], isi["kebutuhan_host"])
    except ValueError as e:
        return _galat(str(e))


@app.get("/", response_class=HTMLResponse)
def halaman():
    return INDEX_HTML.read_text(encoding="utf-8")
