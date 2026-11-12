# [Feature] Kalkulator Subnet

## Deskripsi
Halaman web untuk guru SMK TKJ yang menghitung subnet IPv4 dari alamat IP dan prefix: mask, network, broadcast, host pertama, host terakhir, dan jumlah host. Aturan lengkap ada di SPEC.md.

## Tugas
- Tulis test_main.py lebih dulu (fase merah).
- Implementasikan hitung_subnet, GET /api/subnet, dan GET / di main.py.
- Hubungkan index.html ke API, termasuk pesan galat dari field detail.

## Kriteria Penerimaan
- Semua kasus pada tabel A, B, C (hitung_subnet) di SPEC.md lulus.
- Kasus API subnet dan GET / pada tabel E di SPEC.md lulus.
- test_main.py tidak diubah agar test lulus.
- CI hijau.

## Alur Kerja
issue -> branch -> test dulu -> implementasi -> commit -> pull request -> CI -> merge
