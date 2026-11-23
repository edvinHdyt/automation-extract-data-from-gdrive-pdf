# Pipeline Ekstraksi Knowledge Graph Penyakit Bercak Daun

Pipeline untuk mengekstrak Knowledge Graph (Penyakit, Penyebab, Penanganan) dari beberapa jurnal PDF pertanian menggunakan LLM (Gemma-2), dengan keluaran JSON berstruktur ID yang siap diinjeksikan ke KG.

---

## 1. Checkpoint Saat Ini

**Posisi:** Tahap pembersihan teks hampir selesai. Berikutnya adalah **chunking**.

| Tahap | Status | Catatan |
|---|---|---|
| 1. Akses Google Drive (Service Account) | Selesai | `list_files_in_folder`, download ke RAM |
| 2. Baca PDF dengan PyMuPDF (per halaman) | Selesai | Pengganti pdfplumber, kolom tidak lagi bercampur |
| 3. Buang header/footer | Selesai | Berbasis pengulangan teks antar halaman |
| 4. Trim awal dan akhir dokumen | Selesai | Potong dari setelah PENDAHULUAN sampai sebelum DAFTAR PUSTAKA |
| 5. Buang caption gambar/tabel | Selesai | `removeCaptions`; rujukan "(Gambar 1)" di dalam kalimat sengaja dibiarkan |
| 6. Sambung paragraf terpotong antar halaman | Selesai | `joinBrokenParagraphs` |
| 7. Chunking | Belum | Plafon ~3000 karakter, overlap kecil |
| 8. Prompt few-shot + panggil LLM | Belum | Template sudah dirancang |
| 9. Parse + validasi JSON per chunk | Belum | |
| 10. Merge antar-chunk | Belum | 1 JSON per jurnal |
| 11. Merge antar-jurnal | Belum | Label sumber jurnal pada relasi |
| 12. Injeksi ke KG | Belum | Neo4j atau NetworkX (belum diputuskan) |

**Yang perlu dicek sebelum lanjut ke chunking:**
- Jalankan `removeCaptions` lalu `joinBrokenParagraphs` pada jurnal Curvularia dan cek hasilnya (elemen yang masih diawali huruf kecil harus sudah tidak ada).
- Uji seluruh rangkaian pada **jurnal 2 dan 3**. Penanda heading (PENDAHULUAN, DAFTAR PUSTAKA) bisa berbeda dan jika tidak cocok, tidak ada yang terpotong tanpa pesan error.

---

## 2. Gambaran Alur Keseluruhan

```
Google Drive (3 jurnal PDF)
        |
[Tahap A] Per jurnal (diulang 3x)
   1. Download PDF ke RAM
   2. PyMuPDF -> blok per halaman
   3. Buang header/footer, urutkan baca
   4. Trim awal/akhir dokumen
   5. Buang caption, sambung paragraf antar halaman
   6. Chunking
   7. Tiap chunk -> LLM (few-shot) -> JSON
   8. Validasi JSON
   9. Merge antar-chunk -> 1 JSON per jurnal, simpan checkpoint
        |
[Tahap B] Merge antar-jurnal (Python saja, tanpa LLM)
        |
[Tahap C] Injeksi ke Knowledge Graph
```

Prinsip penting: **LLM hanya menerima satu chunk setiap panggilan.** Teks beberapa jurnal tidak pernah digabung sebelum masuk model. Yang digabung adalah hasil JSON-nya.

---

## 3. Penjelasan Per Langkah

### Tahap A: Proses per jurnal

#### Langkah 1. Download PDF ke RAM
Google Drive API dengan Service Account. Folder Drive di-share ke `client_email` milik Service Account (boleh akun Google berbeda dengan akun Cloud Console). PDF diunduh ke `io.BytesIO`, tanpa file fisik. Setelah selesai, buffer ditutup (`close()`), variabel dihapus (`del`), dan `gc.collect()` dipanggil di akhir tiap iterasi.

#### Langkah 2. Baca PDF dengan PyMuPDF
`page.get_text("blocks")` per halaman. Satu blok kurang lebih satu paragraf, baris yang patah karena lebar kolom sudah tersambung. Teks dirapikan dengan `" ".join(text.split())` dan kata terpotong tanda hubung (`-\n`) disambung.

Kenapa bukan pdfplumber: `extract_text()` memakai `\n` di setiap baris visual (bukan batas paragraf) dan layout dua kolom tercampur sehingga kalimat kolom kiri dan kanan saling menyisip.

#### Langkah 3. Buang header/footer dan urutkan baca
- **Pass 1:** baca semua halaman. Blok di zona tepi (atas 8%, bawah 7%) dan pendek (<=150 karakter) dihitung kemunculannya setelah dinormalisasi (angka diganti `#`, lowercase).
- **Penentuan:** teks tepi yang muncul di >=2 halaman dianggap header/footer. Ini menangkap nomor halaman dan header yang bergantian genap/ganjil.
- **Pass 2:** header/footer dibuang. Sisanya diurutkan: blok yang lebarnya >60% halaman (judul, abstrak) menjadi pemisah, dan di antara dua pemisah dibaca kolom kiri dulu baru kolom kanan.

Parameter yang bisa disetel: `topZone`, `bottomZone`, `maxHeaderLen`, `minRepeat`, `fullWidthRatio`.

#### Langkah 4. Trim awal dan akhir dokumen (`trimParagraphs`)
Memotong list paragraf dari setelah heading **PENDAHULUAN** sampai sebelum **DAFTAR PUSTAKA**. Dengan satu langkah ini, judul, penulis, afiliasi, abstrak (Inggris dan Indonesia), dan daftar pustaka hilang.

- `START_RE` dicari dari depan, `END_RE` dicari dari belakang (mengambil kemunculan terakhir).
- `END_RE` hanya mengecek **awal** elemen (tanpa `$`) karena PyMuPDF sering menempelkan heading dengan isi, contoh: `"DAFTAR PUSTAKA De Lucca, AJ. 2007..."`.
- Fallback aman: jika penanda tidak ditemukan, tidak ada yang dipotong. Tambahkan log peringatan agar jurnal itu dicek manual.
- Jurnal baru dengan heading berbeda ("Latar Belakang", "Introduction", "Acknowledgment") cukup ditambahkan variasinya ke regex. Hindari aturan khusus per jurnal.

#### Langkah 5. Buang caption dan sambung paragraf
Urutan wajib: **caption dibuang dulu, baru paragraf disambung.** Kalau terbalik, lanjutan caption yang diawali huruf kecil akan menempel ke paragraf isi.

- `removeCaptions`: membuang elemen yang diawali "Gambar/Tabel/Figure/Table N", lanjutannya yang pendek dan berawalan huruf kecil, serta blok label gambar pendek (<=300 karakter). Rujukan di dalam kalimat panjang seperti "(Gambar 1)." **sengaja dibiarkan** karena itu bagian dari isi.
- `joinBrokenParagraphs`: elemen yang diawali huruf kecil, atau elemen sebelumnya panjang (>=150 karakter) tapi tidak berakhir tanda baca akhir kalimat (contoh `"(Jackson,"` + `"2010). Gejala..."`), digabung dengan elemen sebelumnya.
- Heading di tengah teks (BAHAN DAN METODE, SIMPULAN, dll.) dibiarkan dulu. Tidak merusak ekstraksi dan kadang membantu konteks.

Hasil langkah 1-5: **satu list paragraf bersih per jurnal.**

#### Langkah 6. Chunking
Mengelompokkan paragraf menjadi chunk dengan **plafon ~3000 karakter** (bukan target pas).

```
untuk setiap paragraf:
    jika panjang(chunk_sekarang) + panjang(paragraf) > BATAS:
        kirim chunk_sekarang ke LLM
        chunk baru = overlap kecil dari ujung chunk lama + paragraf ini
    jika tidak:
        tambahkan paragraf ke chunk_sekarang
setelah loop: sisa chunk tetap diproses
```

- Pengecekan dilakukan **sebelum** menambah paragraf, sehingga paragraf tidak pernah terpotong. Ukuran chunk bervariasi (2100, 2500, 2980 semuanya valid).
- Sisa chunk di akhir loop wajib diproses (sering berisi simpulan).
- Paragraf tunggal yang lebih panjang dari plafon dibiarkan menjadi chunk sendiri.
- Overlap menjaga konteks ketika chunk berikutnya hanya menulis "penyakit ini..." tanpa menyebut nama penyakitnya.
- Alasan perlu chunking: batas konteks Gemma-2 (~8K token) sudah terpakai instruksi dan contoh few-shot, kualitas model kecil turun pada input panjang, dan output JSON panjang berisiko terpotong sehingga gagal di-parse.
- 3000 **karakter** (sekitar 450-500 kata), bukan 3000 kata. Mulai dari kisaran 2000-3000.

#### Langkah 7. Prompt few-shot dan panggil LLM
Format **multi-turn** (pasangan `user` teks jurnal dan `assistant` JSON). Gemma-2 tidak punya role `system`, jadi aturan ditempel di turn `user` pertama.

Aturan ekstraksi:
1. Tipe entitas: `Penyakit`, `Penyebab` (jamur/bakteri/virus/hama), `Penanganan` (fungisida, tindakan budidaya).
2. Predikat: `Disebabkan oleh` (Penyakit -> Penyebab) dan `Ditangani dengan` (Penyakit -> Penanganan).
3. Output wajib punya `entities` dan `relations`.
4. `subject` dan `object` memakai **id**, bukan nama.
5. Entitas unik ditulis sekali, id dipakai ulang.
6. Nama singkat dan baku ("Cercospora", bukan kalimat deskriptif).
7. Hanya ekstrak yang eksplisit di teks. Jika tidak ada, kembalikan array kosong.
8. Abaikan tabel, caption, statistik, daftar pustaka.
9. Keluarkan hanya JSON.

Tiga contoh few-shot:
1. Relasi sederhana (1 penyakit, 1 penyebab, 1 penanganan).
2. Beberapa penyakit memakai penanganan yang sama (id dipakai ulang, tidak duplikat).
3. Teks tanpa informasi relevan, output `{"entities": [], "relations": []}` (mencegah halusinasi pada chunk metodologi).

Panggil dengan `apply_chat_template(..., add_generation_prompt=True)` dan `temperature=0` (atau `do_sample=False`).

Struktur JSON target (sesuai diagram: Penyakit di tengah, Penyebab di kiri, Penanganan di kanan):

```json
{
  "entities": [
    {"id": "1", "type": "Penyakit", "name": "Bercak Daun"},
    {"id": "2", "type": "Penyebab", "name": "Cercospora"},
    {"id": "3", "type": "Penanganan", "name": "Fungisida"}
  ],
  "relations": [
    {"id": "r1", "subject": "1", "predicate": "Disebabkan oleh", "object": "2"},
    {"id": "r2", "subject": "1", "predicate": "Ditangani dengan", "object": "3"}
  ]
}
```

Satu chunk menghasilkan satu JSON. JSON kosong adalah hal normal.

#### Langkah 8. Parse dan validasi JSON per chunk
Few-shot menurunkan error tapi tidak menghilangkannya, jadi:
- **Parse aman:** `json.loads` dalam try/except. Cadangan: potong dari `{` pertama sampai `}` terakhir, atau retry.
- **Validasi referensi:** setiap `subject`/`object` harus ada di `entities`. Relasi dengan id tidak valid dibuang.
- **Validasi tipe:** `Disebabkan oleh` hanya Penyakit -> Penyebab, `Ditangani dengan` hanya Penyakit -> Penanganan.

#### Langkah 9. Merge antar-chunk
Id hanya unik di dalam satu chunk (id "1" di chunk 1 dan chunk 5 bisa berbeda entitas), jadi saat digabung:
1. Nama dinormalisasi (lowercase, strip) sebagai kunci dedup.
2. Id global dibuat ulang.
3. `subject`/`object` pada relasi dipetakan ke id global.
4. Relasi duplikat dibuang.

Hasilnya satu JSON per jurnal. **Simpan ke file** (misal `JsonOutput/jurnal1.json`) sebagai checkpoint agar kegagalan di jurnal ke-3 tidak mengulang jurnal 1 dan 2.

### Tahap B: Merge antar-jurnal

Fungsi `merge_graphs` yang sama dipakai lagi (inputnya sama-sama list `{entities, relations}`), murni Python tanpa LLM. Di sinilah graph saling tersambung: jika dua jurnal sama-sama menyebut "Fungisida", keduanya menjadi satu node.

Tambahkan atribut sumber pada relasi (misalnya `"source": "nama_jurnal.pdf"`) agar klaim bisa ditelusuri ke jurnal asalnya.

Opsional: LLM bisa membantu menyatukan nama mirip ("Cercospora henningsii" dan "Cercospora") dengan input **daftar nama entitas unik saja**, bukan teks jurnal. Untuk awal, normalisasi sederhana di Python biasanya cukup.

### Tahap C: Injeksi ke Knowledge Graph
Entitas menjadi node, relasi menjadi edge, di Neo4j atau NetworkX. Format JSON final mengikuti pilihan ini.

---

## 4. Kerangka Kode Utama

```python
def proses_satu_jurnal(file_id):
    paragraphs = drive_service.extractParagraphsFromDrive(file_id)  # langkah 2-3
    paragraphs = trimParagraphs(paragraphs)                          # langkah 4
    paragraphs = removeCaptions(paragraphs)                          # langkah 5
    paragraphs = joinBrokenParagraphs(paragraphs)                    # langkah 5
    chunks = chunk_paragraphs(paragraphs)                            # langkah 6 (belum dibuat)

    hasil = []
    for chunk in chunks:
        output = jalankan_llm(build_messages(chunk))                 # langkah 7
        data = parse_json_aman(output)                               # langkah 8
        if data:
            hasil.append(data)
    return merge_graphs(hasil)                                       # langkah 9


if __name__ == "__main__":
    files = drive_service.list_files_in_folder(folder_id)
    hasil_per_jurnal = []
    for f in files:
        hasil_per_jurnal.append(proses_satu_jurnal(f["id"]))
        gc.collect()
    kg_final = merge_graphs(hasil_per_jurnal)                        # tahap B
```

---

## 5. Catatan dan Keputusan Terbuka

- **Dokumen bilingual:** abstrak sudah ikut terbuang oleh trim. Jika nanti abstrak ingin dipertahankan (isinya padat penyakit-penyebab), mulai dari "ABSTRAK" dan buang bagian Inggris.
- **Normalisasi nama:** cukup lowercase dan strip, atau perlu menyatukan variasi nama ilmiah?
- **Chunk gagal:** diulang otomatis atau dilewati?
- **Tujuan akhir KG:** Neo4j atau NetworkX?
- **Kompatibilitas jurnal:** bagian yang bergantung gaya jurnal hanya penanda heading, urutan kolom, dan heading di tengah teks. Header/footer, chunking, prompt, dan merge tidak bergantung gaya.
- **Urutan baca:** halaman campuran satu dan dua kolom ditangani lewat blok lebar penuh sebagai pemisah. Jika ada jurnal dengan layout lain, cek hasil per halaman.

## 6. Langkah Berikutnya

1. Uji `removeCaptions` dan `joinBrokenParagraphs` pada jurnal 1.
2. Jalankan seluruh rangkaian pembersihan pada jurnal 2 dan 3, lalu cetak 3 elemen pertama dan terakhir tiap jurnal.
3. Buat `chunk_paragraphs`.
4. Susun `build_messages` dan uji pada beberapa chunk saja sebelum memproses semuanya.
5. Buat validasi JSON, lalu `merge_graphs`.
