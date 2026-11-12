import pytest
from fastapi.testclient import TestClient

from main import app, hitung_subnet

client = TestClient(app)


def hasil(mask, network, broadcast, first, last, usable):
    return {
        "mask": mask,
        "network": network,
        "broadcast": broadcast,
        "first_host": first,
        "last_host": last,
        "usable_hosts": usable,
    }


BLOK_64 = hasil("255.255.255.192", "192.168.1.64", "192.168.1.127", "192.168.1.65", "192.168.1.126", 62)

KASUS_NORMAL = [
    ("172.16.5.130", 25, hasil("255.255.255.128", "172.16.5.128", "172.16.5.255", "172.16.5.129", "172.16.5.254", 126)),
    ("192.168.1.10", 24, hasil("255.255.255.0", "192.168.1.0", "192.168.1.255", "192.168.1.1", "192.168.1.254", 254)),
    ("10.1.2.3", 8, hasil("255.0.0.0", "10.0.0.0", "10.255.255.255", "10.0.0.1", "10.255.255.254", 16777214)),
    ("192.168.1.100", 26, BLOK_64),
    ("192.168.1.64", 26, BLOK_64),
    ("192.168.1.127", 26, BLOK_64),
    ("192.168.1.255", 23, hasil("255.255.254.0", "192.168.0.0", "192.168.1.255", "192.168.0.1", "192.168.1.254", 510)),
    ("10.0.0.0", 30, hasil("255.255.255.252", "10.0.0.0", "10.0.0.3", "10.0.0.1", "10.0.0.2", 2)),
    ("0.0.0.0", 0, hasil("0.0.0.0", "0.0.0.0", "255.255.255.255", "0.0.0.1", "255.255.255.254", 4294967294)),
    ("200.1.1.1", 1, hasil("128.0.0.0", "128.0.0.0", "255.255.255.255", "128.0.0.1", "255.255.255.254", 2147483646)),
    ("127.0.0.1", 8, hasil("255.0.0.0", "127.0.0.0", "127.255.255.255", "127.0.0.1", "127.255.255.254", 16777214)),
    ("169.254.1.1", 16, hasil("255.255.0.0", "169.254.0.0", "169.254.255.255", "169.254.0.1", "169.254.255.254", 65534)),
    ("224.0.0.1", 4, hasil("240.0.0.0", "224.0.0.0", "239.255.255.255", "224.0.0.1", "239.255.255.254", 268435454)),
]

KASUS_31_32 = [
    ("192.168.1.0", 31, hasil("255.255.255.254", "192.168.1.0", None, "192.168.1.0", "192.168.1.1", 2)),
    ("192.168.1.5", 32, hasil("255.255.255.255", "192.168.1.5", None, "192.168.1.5", "192.168.1.5", 1)),
    ("255.255.255.255", 32, hasil("255.255.255.255", "255.255.255.255", None, "255.255.255.255", "255.255.255.255", 1)),
]

IP_TIDAK_VALID = [
    "256.1.1.1",
    "192.168.01.1",
    "192.168.1",
    "192.168.1.1.1",
    "192..1.1",
    "192.168.1.1.",
    "192.168.1.-1",
    "abc",
    "",
    " 192.168.1.1",
    "192.168.1.1 ",
    "192. 168.1.1",
    "192.168.1.1\n",
    "0xC0.168.1.1",
    "\u0661\u0669\u0662.168.1.1",
    "192.168.1.1/24",
    None,
]

PREFIX_TIDAK_VALID = [33, -1, "24", 24.5, True, None]


@pytest.mark.parametrize("ip, prefix, harapan", KASUS_NORMAL)
def test_subnet_normal(ip, prefix, harapan):
    assert hitung_subnet(ip, prefix) == harapan


@pytest.mark.parametrize("ip, prefix, harapan", KASUS_31_32)
def test_subnet_31_dan_32(ip, prefix, harapan):
    assert hitung_subnet(ip, prefix) == harapan


@pytest.mark.parametrize("ip", IP_TIDAK_VALID)
def test_ip_tidak_valid(ip):
    with pytest.raises(ValueError):
        hitung_subnet(ip, 24)


@pytest.mark.parametrize("prefix", PREFIX_TIDAK_VALID)
def test_prefix_tidak_valid(prefix):
    with pytest.raises(ValueError):
        hitung_subnet("192.168.1.1", prefix)


def test_usable_hosts_bertipe_int():
    assert type(hitung_subnet("10.0.0.0", 24)["usable_hosts"]) is int


def test_api_subnet_sukses():
    r = client.get("/api/subnet", params={"ip": "172.16.5.130", "prefix": "25"})
    assert r.status_code == 200
    data = r.json()
    assert set(data) == {"mask", "network", "broadcast", "first_host", "last_host", "usable_hosts"}
    assert data["network"] == "172.16.5.128"
    assert data["broadcast"] == "172.16.5.255"
    assert data["usable_hosts"] == 126


def test_api_subnet_31_broadcast_null():
    r = client.get("/api/subnet", params={"ip": "192.168.1.0", "prefix": "31"})
    assert r.status_code == 200
    assert r.json()["broadcast"] is None
    assert r.json()["usable_hosts"] == 2


@pytest.mark.parametrize(
    "params",
    [
        {"ip": "256.1.1.1", "prefix": "24"},
        {"ip": "192.168.1.1"},
        {"prefix": "24"},
        {"ip": "192.168.1.1", "prefix": "abc"},
        {"ip": "192.168.1.1", "prefix": "024"},
        {"ip": "192.168.1.1", "prefix": "+24"},
        {"ip": "192.168.1.1", "prefix": "/24"},
        {"ip": "192.168.1.1", "prefix": " 24"},
        {"ip": "192.168.1.1", "prefix": "24.5"},
        {"ip": "192.168.1.1", "prefix": ""},
        {"ip": "192.168.1.1", "prefix": "33"},
    ],
)
def test_api_subnet_input_tidak_valid(params):
    r = client.get("/api/subnet", params=params)
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], str) and r.json()["detail"]


def test_halaman_utama():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<html" in r.text.lower()


def test_metode_salah_405():
    assert client.post("/api/subnet").status_code == 405


# ---------- VLSM (Tahap 8) ----------
from main import alokasi_vlsm

KASUS_VLSM = [
    ("192.168.1.0/24", [100, 50, 20, 2], ["192.168.1.0/25", "192.168.1.128/26", "192.168.1.192/27", "192.168.1.224/30"]),
    ("192.168.1.0/24", [62, 62, 62, 62], ["192.168.1.0/26", "192.168.1.64/26", "192.168.1.128/26", "192.168.1.192/26"]),
    ("10.0.0.0/16", [126], ["10.0.0.0/25"]),
    ("10.0.0.0/16", [127], ["10.0.0.0/24"]),
    ("192.168.1.0/24", [3], ["192.168.1.0/29"]),
    ("192.168.1.0/24", [1, 2], ["192.168.1.0/30", "192.168.1.4/30"]),
    ("192.168.1.0/24", [2, 100, 20, 50], ["192.168.1.0/25", "192.168.1.128/26", "192.168.1.192/27", "192.168.1.224/30"]),
    ("192.168.1.0/24", [30, 30, 30], ["192.168.1.0/27", "192.168.1.32/27", "192.168.1.64/27"]),
    ("10.0.0.0/22", [500, 200], ["10.0.0.0/23", "10.0.2.0/24"]),
    ("192.168.1.0/30", [2], ["192.168.1.0/30"]),
]

KASUS_VLSM_GAGAL = [
    ("192.168.1.0/24", [200, 100]),
    ("192.168.1.0/24", [62, 62, 62, 62, 2]),
    ("192.168.1.0/30", [1, 1]),
    ("192.168.1.5/24", [10]),
    ("192.168.1.0", [10]),
    ("192.168.1.0/33", [10]),
    ("192.168.1.0/024", [10]),
    ("192.168.1.0/31", [1]),
    ("192.168.1.5/32", [1]),
    ("192.168.1.0/24", []),
    ("192.168.1.0/24", [0]),
    ("192.168.1.0/24", [-5]),
    ("192.168.1.0/24", [2.5]),
    ("192.168.1.0/24", ["abc"]),
    ("192.168.1.0/24", [True]),
    ("192.168.1.0/24", [5000000000]),
    ("192.168.1.0/24", None),
    (None, [10]),
]


@pytest.mark.parametrize("network, kebutuhan, harapan", KASUS_VLSM)
def test_vlsm_alokasi(network, kebutuhan, harapan):
    assert [b["network_cidr"] for b in alokasi_vlsm(network, kebutuhan)] == harapan


def test_vlsm_urutan_menurut_alokasi():
    hasil_vlsm = alokasi_vlsm("192.168.1.0/24", [2, 100, 20, 50])
    assert [b["kebutuhan"] for b in hasil_vlsm] == [100, 50, 20, 2]


def test_vlsm_isi_blok():
    blok = alokasi_vlsm("192.168.1.0/24", [100, 50, 20, 2])[0]
    assert blok == {
        "kebutuhan": 100,
        "network_cidr": "192.168.1.0/25",
        "mask": "255.255.255.128",
        "network": "192.168.1.0",
        "broadcast": "192.168.1.127",
        "first_host": "192.168.1.1",
        "last_host": "192.168.1.126",
        "usable_hosts": 126,
    }


@pytest.mark.parametrize("network, kebutuhan", KASUS_VLSM_GAGAL)
def test_vlsm_tidak_valid(network, kebutuhan):
    with pytest.raises(ValueError):
        alokasi_vlsm(network, kebutuhan)


def test_api_vlsm_sukses():
    r = client.post("/api/vlsm", json={"network": "192.168.1.0/24", "kebutuhan_host": [100, 50, 20, 2]})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 4
    assert [b["network_cidr"] for b in data] == [
        "192.168.1.0/25", "192.168.1.128/26", "192.168.1.192/27", "192.168.1.224/30",
    ]


def test_api_vlsm_tidak_muat():
    r = client.post("/api/vlsm", json={"network": "192.168.1.0/24", "kebutuhan_host": [200, 100]})
    assert r.status_code == 400
    assert r.json()["detail"]


def test_api_vlsm_bukan_json():
    r = client.post("/api/vlsm", content="bukan json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert "detail" in r.json()


@pytest.mark.parametrize(
    "isi",
    [
        {"kebutuhan_host": [10]},
        {"network": "192.168.1.0/24"},
        {},
        [1, 2, 3],
        {"network": "192.168.1.0/24", "kebutuhan_host": "100"},
        {"network": "192.168.1.0/24", "kebutuhan_host": 100},
        {"network": "192.168.1.0/24", "kebutuhan_host": ["abc"]},
        {"network": "192.168.1.0/24", "kebutuhan_host": [True]},
        {"network": "192.168.1.0/24", "kebutuhan_host": [2.5]},
        {"network": "192.168.1.0/24", "kebutuhan_host": []},
        {"network": 123, "kebutuhan_host": [10]},
    ],
)
def test_api_vlsm_input_tidak_valid(isi):
    r = client.post("/api/vlsm", json=isi)
    assert r.status_code == 400
    assert "detail" in r.json()
