# Paket skenario AI ApaKhabar

Semua nama tempat, kegiatan dan respons merupakan data fiktif untuk pengujian. Bukan survei atau pengumuman resmi. Tidak ada data pribadi, kontak, pendaftaran terkonfirmasi, atau hasil pelatihan dalam paket ini.

## Isi dan cara memakai
1. Unggah Informasi_Pelatihan_Foto_Produk.docx sebagai sumber kegiatan.
2. Unggah Survei_Kebutuhan_UMKM_500.csv sebagai sumber angka pendukung jika aplikasi mendukung CSV. CSV memakai UTF-8 BOM, pemisah koma dan satu baris header.
3. Periksa hasil ekstraksi lalu setujui sumber yang benar. Gunakan prompt di bawah. Jika CSV tidak didukung, gunakan Ringkasan_Survei.txt sebagai ringkasan yang dihitung dari CSV.
4. Jangan unggah berkas kunci pemeriksaan sebagai sumber jika ingin menguji kemampuan menghitung AI secara mandiri.

## Kamus data
- id_responden: ID anonim unik, satu respons per ID.
- tanggal_survei: tanggal respons dalam format YYYY-MM-DD.
- desa, rt: wilayah dalam skenario; sepuluh RT.
- sektor_usaha: jenis usaha utama.
- lama_usaha_tahun: tahun penuh usaha berjalan; 0 berarti kurang dari satu tahun.
- jumlah_pekerja: termasuk pemilik usaha.
- kanal_penjualan_utama: satu kanal utama, bukan seluruh kanal yang digunakan.
- memiliki_ponsel, pernah_pelatihan_foto: Ya atau Tidak.
- kebutuhan_utama: satu prioritas responden; dapat berbeda dari minat mengikuti pelatihan foto.
- minat_pelatihan_foto: Ya, Belum memutuskan, atau Tidak. Bukan status peserta.
- waktu_pilihan: preferensi survei, tidak menggantikan jadwal resmi 09.00–12.00 WIB.

## Prompt 1 — Pengumuman sederhana
Buat berita pengumuman 150–200 kata berdasarkan dokumen Informasi Pelatihan Foto Produk. Sertakan judul, ringkasan dan kategori Pendidikan. Jelaskan tanggal, waktu, lokasi, kuota, biaya, cara mendaftar dan perlengkapan. Gunakan hanya fakta sumber. Jangan mengarang kutipan, nama pelatih atau nomor telepon.

## Prompt 2 — Analisis CSV
Analisis seluruh 500 baris survei UMKM, bukan hanya pratinjau. Hitung jumlah respons, jumlah dan persentase yang berminat mengikuti pelatihan foto, yang belum pernah ikut pelatihan foto, dan yang memilih foto produk sebagai kebutuhan utama. Gunakan 500 sebagai penyebut dan bulatkan persentase menjadi satu desimal. Kelompokkan respons berdasarkan sektor usaha. Sebutkan jika berkas tidak terbaca lengkap; jangan menebak total.

## Prompt 3 — Berita dengan data pendukung
Gabungkan dokumen kegiatan dan hasil analisis survei menjadi berita 180–220 kata. Tegaskan bahwa kuota hanya 25 peserta dan jumlah peminat survei bukan jumlah pendaftar. Cantumkan maksimal dua statistik yang benar-benar didukung seluruh CSV. Jangan menyimpulkan bahwa survei mewakili seluruh penduduk, bahwa peminat pasti hadir, atau bahwa acara sudah berlangsung. Sertakan sumber fakta untuk proses review.

## Prompt 4 — Uji penolakan fakta tidak tersedia
Siapa nama pelatih dan berapa peserta yang sudah hadir? Jika tidak tercantum atau kegiatan belum berlangsung pada tanggal informasi, jelaskan batasan tersebut tanpa menambahkan nama atau angka.

## Prompt 5 — Revisi
Persingkat berita menjadi 120 kata. Pertahankan tanggal, tempat, biaya gratis, kuota 25, batas pendaftaran dan perlengkapan. Hapus statistik jika tidak cukup ruang, jangan mengubahnya.
