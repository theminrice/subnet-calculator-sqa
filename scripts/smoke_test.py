"""Smoke test (smoke test) untuk Kalkulator Subnet & VLSM yang sudah berjalan.

Pemakaian:
    uv run python scripts/smoke_test.py <URL dasar>
Contoh:
    uv run python scripts/smoke_test.py http://127.0.0.1:8000

Keluar dengan kode 0 bila semua pemeriksaan lulus, 1 bila ada yang gagal.
Kesalahan sementara (server belum siap atau cold start) dicoba ulang beberapa kali.
"""
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request

PERCOBAAN = int(os.environ.get("SMOKE_PERCOBAAN", "6"))
JEDA_DETIK = int(os.environ.get("SMOKE_JEDA", "15"))


def minta(base, path, metode="GET", isi=None):
    url = base.rstrip("/") + path
    data = None
    header = {}
    if isi is not None:
        data = json.dumps(isi).encode("utf-8")
        header["Content-Type"] = "application/json"
    terakhir = (0, "")
    for percobaan in range(1, PERCOBAAN + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=header, method=metode)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            terakhir = (e.code, e.read().decode("utf-8", "replace"))
            if e.code < 500:
                return terakhir
        except (OSError, http.client.HTTPException) as e:
            # server belum siap: koneksi ditolak, terputus, atau habis waktu
            terakhir = (0, str(e))
        if percobaan < PERCOBAAN:
            time.sleep(JEDA_DETIK)
    return terakhir


def cek_halaman(base):
    status, teks = minta(base, "/")
    assert status == 200, f"status {status}, seharusnya 200"
    assert "<html" in teks.lower(), "isi bukan halaman HTML"


def cek_subnet(base):
    status, teks = minta(base, "/api/subnet?ip=172.16.5.130&prefix=25")
    assert status == 200, f"status {status}, seharusnya 200"
    hasil = json.loads(teks)
    assert hasil["network"] == "172.16.5.128", f"network {hasil['network']}"
    assert hasil["broadcast"] == "172.16.5.255", f"broadcast {hasil['broadcast']}"
    assert hasil["usable_hosts"] == 126, f"usable_hosts {hasil['usable_hosts']}"


def cek_input_invalid(base):
    status, _ = minta(base, "/api/subnet?ip=256.1.1.1&prefix=24")
    assert status == 400, f"status {status}, seharusnya 400"


def cek_vlsm(base):
    isi = {"network": "192.168.1.0/24", "kebutuhan_host": [100, 50, 20, 2]}
    status, teks = minta(base, "/api/vlsm", "POST", isi)
    assert status == 200, f"status {status}, seharusnya 200"
    hasil = [b["network_cidr"] for b in json.loads(teks)]
    harapan = ["192.168.1.0/25", "192.168.1.128/26", "192.168.1.192/27", "192.168.1.224/30"]
    assert hasil == harapan, f"hasil {hasil}"


PEMERIKSAAN = [
    ("Halaman utama (GET /)", cek_halaman),
    ("Subnet 172.16.5.130/25", cek_subnet),
    ("Input tidak valid ditolak (400)", cek_input_invalid),
    ("VLSM 100, 50, 20, 2 host", cek_vlsm),
]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    base = sys.argv[1]
    gagal = 0
    for nama, fungsi in PEMERIKSAAN:
        try:
            fungsi(base)
            print(f"[LULUS] {nama}")
        except Exception as e:  # noqa: BLE001
            gagal += 1
            print(f"[GAGAL] {nama}: {e}")
    print(f"Ringkasan: {len(PEMERIKSAAN) - gagal} lulus, {gagal} gagal")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
