# Skenario AI sederhana untuk ApaKhabar

Semua data, tempat, nama, dan kegiatan dalam paket ini fiktif untuk demonstrasi. Jangan dipublikasikan sebagai berita nyata.

## Alur singkat

1. Mulai percakapan baru. Unggah dokumen Word untuk skenario 1. Tunggu ekstraksi selesai, tinjau fakta, dan setujui sumber yang benar sesuai alur aplikasi.
2. Untuk skenario 2, unggah CSV dan gunakan ekstraksi umum terlebih dahulu. Mode umum dapat menghitung ringkasan tabel secara lokal sehingga mengurangi panggilan API. Verifikasi seluruh 500 baris terbaca. Persetujuan sumber tetap diperlukan.
3. Untuk skenario 3, pilih kedua sumber yang sudah disetujui. Salin prompt gabungan.
4. Gunakan prompt revisi pada draft yang dihasilkan. Jangan mengirim atau menerbitkan hasil demo.

Unggah hanya 01_Survei_UMKM_500.csv dan 02_Konteks_Pelatihan_UMKM.docx. Jangan unggah panduan ini atau kunci jawaban sebagai sumber AI.

## Skenario 1 — Dokumen menjadi pengumuman

File: 02_Konteks_Pelatihan_UMKM.docx saja.

Prompt:

> Buat berita pengumuman singkat dalam bahasa Indonesia tentang pelatihan foto produk UMKM berdasarkan dokumen ini. Sertakan judul, jadwal, tempat, kuota, biaya, cara mendaftar, dan perlengkapan yang harus dibawa. Gunakan hanya fakta yang tersedia. Jangan mengarang nama pelatih, kutipan, atau jumlah pendaftar. Jangan menyatakan kegiatan sudah berlangsung.

Hasil yang diperiksa: 28 November 2026; 09.00–12.00 WIB; Balai Desa Mekar Asri; gratis; kuota 30; batas pendaftaran 25 November atau lebih awal jika kuota terpenuhi; telepon pintar dan satu contoh produk.

## Skenario 2 — CSV menjadi analisis

File: 01_Survei_UMKM_500.csv. Definisi: satu baris adalah satu responden survei unik; minat bukan pendaftaran. Data dikumpulkan pada 1–10 November 2026 di Desa Mekar Asri. pernah_pelatihan merujuk pelatihan foto produk.

Prompt:

> Analisis seluruh baris CSV survei UMKM. Hitung jumlah responden unik, jumlah dan persentase yang berminat mengikuti pelatihan, yang belum pernah mengikuti pelatihan, dan yang memilih Foto produk sebagai kebutuhan utama. Tampilkan juga jumlah responden per sektor usaha. Gunakan jumlah seluruh responden sebagai penyebut. Jika seluruh data tidak tersedia, jelaskan keterbatasannya dan jangan menebak angka. Minat survei bukan pendaftaran atau kehadiran.

## Skenario 3 — Dokumen dan data menjadi berita

File: kedua sumber, setelah ekstraksi dan persetujuan.

Prompt:

> Buat berita singkat tentang rencana pelatihan foto produk UMKM Desa Mekar Asri berdasarkan dokumen kegiatan dan survei yang tersedia. Sertakan judul dan isi berita yang mudah dipahami warga. Gunakan paling banyak dua statistik survei yang telah terverifikasi. Jelaskan jadwal, tempat, biaya, kuota, batas pendaftaran, cara mendaftar, serta perlengkapan. Bedakan peminat survei, pendaftar, dan peserta hadir. Jangan menambahkan kutipan atau hasil kegiatan. Tunjukkan sumber fakta untuk peninjauan.

## Prompt revisi

> Ringkas draft terakhir menjadi sekitar 120 kata. Pertahankan tanggal, waktu, lokasi, gratis, kuota 30 peserta, cara dan batas pendaftaran, serta perlengkapan. Hapus statistik jika perlu. Jangan mengubah fakta.

## Prompt untuk menguji informasi yang tidak tersedia

> Siapa nama pelatih, berapa orang yang sudah mendaftar, dan berapa yang sudah hadir? Jawab berdasarkan sumber saja. Jika belum tersedia, nyatakan bahwa informasinya belum tersedia.

Hasil yang benar: nama pelatih belum ditetapkan; jumlah pendaftar dan jumlah hadir tidak tersedia. Angka peminat tidak boleh dipakai sebagai pengganti.

## Kunci pemeriksaan angka

| Ukuran | Jumlah | Persentase dari 500 |
|---|---:|---:|
| Responden unik | 500 | 100% |
| Berminat mengikuti pelatihan | 350 | 70% |
| Belum memutuskan | 100 | 20% |
| Tidak berminat | 50 | 10% |
| Belum pernah mengikuti pelatihan | 400 | 80% |
| Foto produk sebagai kebutuhan utama | 250 | 50% |
| Memiliki telepon pintar | 450 | 90% |

Sektor: Kuliner 200, Kerajinan 125, Pakaian 100, Jasa 75. Setiap dusun memiliki 125 responden. Semua angka dihitung dari CSV, bukan hasil AI.

## Cara menilai demo

Catat model, waktu respons, error API, ketepatan angka, kelengkapan fakta, dan apakah AI menambahkan fakta tanpa sumber. Pisahkan kegagalan koneksi dari kesalahan isi. Paket sudah diperiksa struktur dan hitungannya; belum menjadi bukti bahwa model tertentu lulus seluruh skenario. Tanggal sumber tetap 12 November 2026; lewatnya tanggal acara tidak membuktikan acara terlaksana.
