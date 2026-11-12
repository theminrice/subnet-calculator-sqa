# SPEC: Kalkulator Subnet & VLSM

## 1. Tujuan

Aplikasi web untuk guru SMK TKJ yang menghitung subnet IPv4 dan membagi network menjadi beberapa subnet dengan VLSM. Kebenaran hasil harus bisa dinilai guru tanpa membaca kode, jadi seluruh aturan dan kasus uji ditulis di dokumen ini.

Teknologi: Python 3.12, FastAPI, satu halaman `index.html`. Logika perhitungan berada di `main.py`, test di `test_main.py` (pytest).

## 2. Aturan Validasi

### Alamat IP

- Tepat 4 oktet dipisah titik.
- Tiap oktet hanya berisi digit ASCII `0-9`, bernilai 0 sampai 255.
- Tanpa nol di depan: `192.168.01.1` ditolak.
- Tanpa spasi di awal, akhir, maupun tengah.
- Ditolak: oktet kosong (`192..1.1`), titik di ujung, oktet negatif, hex (`0xC0.168.1.1`), digit non-ASCII (misalnya angka Arab), teks bukan angka, dan string kosong.

### Prefix

- Bilangan bulat 0 sampai 32.
- Pada fungsi Python: harus bertipe `int` (bukan `bool`, `float`, atau `str`).
- Pada API (query string): hanya teks `0` atau angka tanpa nol di depan. `024`, `+24`, `/24`, ` 24`, `24.5`, `abc`, dan kosong ditolak.

### Alamat khusus

Loopback (`127.0.0.1`), link-local (`169.254.x.x`), multicast (`224.0.0.1`), dan alamat khusus lain dihitung seperti biasa, tanpa peringatan.

### Network induk VLSM

- Format `a.b.c.d/p`, prefix wajib ada.
- Alamat harus alamat network yang tepat: `192.168.1.5/24` ditolak.
- Prefix 0 sampai 30. `/31` dan `/32` ditolak karena blok terkecil adalah `/30`.

### Kebutuhan host VLSM

- Daftar tidak boleh kosong.
- Tiap nilai bilangan bulat (`int`, bukan `bool`) dan >= 1. Nilai `0`, negatif, desimal, dan teks ditolak.

### Perilaku saat tidak valid

- Fungsi Python: `raise ValueError` dengan pesan berbahasa Indonesia yang menyebut penyebabnya.
- API: HTTP 400 dengan body `{"detail": "<pesan>"}` (lihat bagian Kontrak API).

## 3. Kontrak Fungsi

### `hitung_subnet(ip: str, prefix: int) -> dict`

Kunci hasil: `mask`, `network`, `broadcast`, `first_host`, `last_host`, `usable_hosts`.

| Prefix | usable_hosts | first_host | last_host | broadcast |
| --- | --- | --- | --- | --- |
| 0 sampai 30 | 2^(32 - prefix) - 2 | network + 1 | broadcast - 1 | alamat terakhir blok |
| 31 | 2 (RFC 3021, point-to-point) | network | network + 1 | `None` |
| 32 | 1 | IP itu | IP itu | `None` |

- `network` = IP AND subnet mask, dihitung secara bitwise. IP boleh berupa alamat mana pun di dalam blok (alamat network, broadcast, atau tengah blok), hasilnya sama.
- `mask` ditulis bertitik, misalnya `255.255.255.128`.
- `usable_hosts` bertipe `int`.

### `alokasi_vlsm(network_cidr: str, kebutuhan_host: list[int]) -> list[dict]`

1. Validasi `network_cidr` dan `kebutuhan_host` sesuai bagian Aturan Validasi.
2. Hitung ukuran blok tiap kebutuhan: pangkat 2 terkecil yang >= kebutuhan + 2, minimal 4 alamat (`/30`). Kebutuhan 1 dan 2 sama-sama `/30`.
3. Urutkan kebutuhan dari terbesar. Kebutuhan yang sama mengikuti urutan input (stabil).
4. Alokasikan berurutan mulai dari alamat network induk, tanpa celah.
5. Raise `ValueError` bila jumlah ukuran blok melebihi ukuran network induk.

Hasil: daftar `dict` **menurut urutan alokasi** (kebutuhan terbesar dulu), bukan urutan input. Tiap `dict` memuat `kebutuhan`, `network_cidr` (misalnya `192.168.1.0/25`), dan semua kunci hasil `hitung_subnet` untuk blok itu.

## 4. Kontrak API

Semua kesalahan input (parameter hilang, nilai tidak valid, body bukan JSON, field hilang, tipe salah) menghasilkan **HTTP 400** dengan body `{"detail": "<pesan>"}`. Aplikasi tidak boleh mengembalikan 422 bawaan FastAPI; ubah kesalahan validasi FastAPI menjadi 400.

| Endpoint | Perilaku |
| --- | --- |
| `GET /api/subnet?ip=&prefix=` | 200 dengan JSON hasil `hitung_subnet`. `broadcast` bernilai `null` untuk `/31` dan `/32`. Input tidak valid: 400. |
| `POST /api/vlsm` | Body JSON `{"network": "192.168.1.0/24", "kebutuhan_host": [100, 50, 20, 2]}`. 200 dengan JSON berupa **daftar** hasil `alokasi_vlsm`. Input tidak valid atau tidak muat: 400. |
| `GET /` | 200, isi `index.html` sebagai HTML. |

- Metode yang salah (misalnya `POST /api/subnet`) menghasilkan 405 bawaan FastAPI.
- `main.py` membaca `index.html` lewat jalur relatif terhadap `main.py` itu sendiri (bukan terhadap direktori kerja), agar tetap jalan di container dan di Vercel.

## 5. Halaman Web

Satu halaman `index.html` dengan dua tab.

**Tab Subnet**: kolom IP, kolom prefix (0 sampai 32), tombol Hitung, dan kartu hasil berisi mask, network, broadcast, first host, last host, usable hosts. Untuk `/31` dan `/32`, broadcast ditampilkan sebagai tanda "tidak ada".

**Tab VLSM**: kolom network (CIDR), daftar kebutuhan host yang bisa ditambah dan dihapus, tombol Hitung, dan tabel hasil menurut urutan alokasi.

Tiga keadaan: kosong, sukses, dan error. Pesan error dari field `detail` ditampilkan jelas di bawah kolom yang bermasalah. Halaman memanggil API lewat `fetch`, tanpa framework dan tanpa dependensi eksternal.

## 6. Tabel Test Case

### A. `hitung_subnet`: kasus normal

| Input | Hasil yang diharapkan |
| --- | --- |
| 172.16.5.130/25 | mask 255.255.255.128, network 172.16.5.128, broadcast 172.16.5.255, first .129, last .254, 126 host |
| 192.168.1.10/24 | network 192.168.1.0, broadcast 192.168.1.255, first .1, last .254, 254 host |
| 10.1.2.3/8 | network 10.0.0.0, broadcast 10.255.255.255, 16.777.214 host |
| 192.168.1.100/26 | network 192.168.1.64, broadcast .127, first .65, last .126, 62 host |
| 192.168.1.64/26 | sama dengan baris di atas (IP = alamat network, tidak ditolak) |
| 192.168.1.127/26 | sama dengan baris di atas (IP = alamat broadcast, tidak ditolak) |
| 192.168.1.255/23 | network 192.168.0.0, broadcast 192.168.1.255, first 192.168.0.1, last 192.168.1.254, 510 host |
| 10.0.0.0/30 | first .1, last .2, broadcast .3, 2 host |
| 0.0.0.0/0 | network 0.0.0.0, broadcast 255.255.255.255, 4.294.967.294 host |
| 200.1.1.1/1 | network 128.0.0.0, broadcast 255.255.255.255, 2.147.483.646 host |
| 127.0.0.1/8, 169.254.1.1/16, 224.0.0.1/4 | dihitung biasa |

### B. `hitung_subnet`: /31 dan /32

| Input | Hasil yang diharapkan |
| --- | --- |
| 192.168.1.0/31 | point-to-point, 2 host (first .0, last .1), broadcast `None` |
| 192.168.1.5/32 | 1 host, first = last = 192.168.1.5, broadcast `None` |
| 255.255.255.255/32 | 1 host, network 255.255.255.255, broadcast `None` |

### C. `hitung_subnet`: input tidak valid (semua `ValueError`)

| Kelompok | Contoh input |
| --- | --- |
| Oktet di luar 0-255 | 256.1.1.1 / 24 |
| Nol di depan | 192.168.01.1 / 24 |
| Jumlah oktet salah | 192.168.1, 192.168.1.1.1 |
| Oktet kosong, titik di ujung | 192..1.1, 192.168.1.1. |
| Oktet negatif | 192.168.1.-1 |
| Bukan angka atau kosong | abc, string kosong |
| Spasi | " 192.168.1.1", "192.168.1.1 ", "192. 168.1.1" |
| Hex | 0xC0.168.1.1 |
| Digit non-ASCII | ١٩٢.168.1.1 |
| IP berisi CIDR | "192.168.1.1/24" dengan prefix 24 |
| Prefix di luar rentang | 33, -1 |
| Prefix bukan `int` | "24", 24.5, `True`, `None` |

### D. `alokasi_vlsm`

| Input | Hasil yang diharapkan |
| --- | --- |
| 192.168.1.0/24; [100, 50, 20, 2] | /25 di .0, /26 di .128, /27 di .192, /30 di .224 |
| 192.168.1.0/24; [200, 100] | `ValueError` (tidak muat) |
| 192.168.1.0/24; [62, 62, 62, 62] | empat /26 di .0, .64, .128, .192 |
| 192.168.1.0/24; [62, 62, 62, 62, 2] | `ValueError` |
| 10.0.0.0/16; [126] dan [127] | 126 menjadi /25, 127 menjadi /24 |
| 192.168.1.0/24; [3] | /29 |
| 192.168.1.0/24; [1, 2] | keduanya /30 |
| 192.168.1.0/24; [2, 100, 20, 50] | urutan hasil 100, 50, 20, 2 (menurut alokasi) |
| 192.168.1.0/24; [30, 30, 30] | tiga /27 di .0, .32, .64 (urutan stabil) |
| 10.0.0.0/22; [500, 200] | /23 di 10.0.0.0, /24 di 10.0.2.0 |
| 192.168.1.0/30; [2] | /30 di .0 |
| 192.168.1.0/30; [1, 1] | `ValueError` |
| 192.168.1.5/24; [10] | `ValueError` (bukan alamat network) |
| 192.168.1.0; 192.168.1.0/33; 192.168.1.0/024 | `ValueError` |
| 192.168.1.0/31; [1] dan 192.168.1.5/32; [1] | `ValueError` (minimal /30) |
| [] | `ValueError` |
| [0], [-5], [2.5], ["abc"], [True] | `ValueError` |
| [5000000000] | `ValueError` (tidak muat) |

### E. API

| Permintaan | Hasil yang diharapkan |
| --- | --- |
| GET /api/subnet?ip=172.16.5.130&prefix=25 | 200, JSON dengan 6 kunci, network 172.16.5.128, broadcast 172.16.5.255, usable_hosts 126 |
| GET /api/subnet?ip=192.168.1.0&prefix=31 | 200, broadcast `null`, usable_hosts 2 |
| GET /api/subnet?ip=256.1.1.1&prefix=24 | 400, body memuat `detail` |
| GET /api/subnet?ip=192.168.1.1 (prefix hilang) | 400 |
| GET /api/subnet?ip=192.168.1.1&prefix=abc | 400 |
| GET /api/subnet?ip=192.168.1.1&prefix=024 | 400 |
| POST /api/vlsm, body valid (100, 50, 20, 2) | 200, daftar 4 blok, `network_cidr` berurutan 192.168.1.0/25, 192.168.1.128/26, 192.168.1.192/27, 192.168.1.224/30 |
| POST /api/vlsm, kebutuhan [200, 100] | 400 dengan `detail` |
| POST /api/vlsm, body bukan JSON | 400 |
| POST /api/vlsm, field `network` atau `kebutuhan_host` hilang | 400 |
| POST /api/vlsm, `kebutuhan_host` bukan daftar bilangan bulat | 400 |
| GET / | 200, HTML |
| POST /api/subnet | 405 |

## 7. Di Luar Cakupan

- IPv6.
- Autentikasi, akun pengguna, dan penyimpanan data.
- Penyimpanan riwayat perhitungan.
- Ekspor hasil (PDF, CSV).
- Peringatan atau penandaan alamat khusus (loopback, link-local, multicast).
- Format input selain `ip` dan `prefix` terpisah (misalnya `ip/mask` bertitik) pada API.
- Perhitungan VLSM dengan blok lebih kecil dari `/30`.
