# [Feature] Mode VLSM

## Deskripsi
Mode VLSM: membagi network induk menjadi beberapa subnet menurut kebutuhan host, kebutuhan terbesar lebih dulu. Aturan lengkap ada di SPEC.md.

## Tugas
- Tulis test VLSM lebih dulu (fase merah).
- Implementasikan alokasi_vlsm dan POST /api/vlsm.
- Pastikan tab VLSM di index.html menampilkan hasil dan pesan galat.

## Kriteria Penerimaan
- Semua kasus pada tabel D (alokasi_vlsm) di SPEC.md lulus.
- Kasus POST /api/vlsm pada tabel E di SPEC.md lulus.
- test yang sudah ada tidak diubah.
- CI hijau.

## Alur Kerja
issue -> branch -> test dulu -> implementasi -> commit -> pull request -> CI -> merge
