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
