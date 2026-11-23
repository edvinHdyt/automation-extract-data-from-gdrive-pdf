from Lib.ModelConn import ModelConn
import utils.CreateFileJson as CreateFileJson
from utils.LoggerTrait import LoggerTrait
from Services.GoogleDriveService import GoogleDriveService
from Helper.ChunkJournalHelper import ChunkJournalHelper
from textwrap import dedent
import os
import json
from dotenv import load_dotenv
load_dotenv()

class KnowledgeGraphPipline(LoggerTrait):
    CONNECTION: ModelConn
    pathOutput: str
    fileOutput: str
    GDRIVEFOLDERID: str = os.getenv("GDRIVE_FOLDER_ID")

    def __init__(self, model: str, path:str, file: str):
        if (model == ""):
            self.logger.error("Model tidak boleh kosong!")
            raise Exception("Model tidak boleh kosong!")
        
        self.CONNECTION = ModelConn(model)
        self.pathOutput = path
        self.fileOutput = file


    def appendToFileJson(self, generateTokens):
        hasilJson = self.CONNECTION.tokenizer.decode(generateTokens, skip_special_tokens=True)
        
        print("\n")
        self.logger.info("Membuat JSON ke file DataMentah.json...")
        CreateFileJson.saveFile(hasilJson, self.pathOutput, self.fileOutput)

    def extractJournal(self):
        try:
            gDriveService = GoogleDriveService()
            listFiles = gDriveService.listFilesInFolder(self.GDRIVEFOLDERID)
    
            for file in listFiles:
                paragraphs = gDriveService.extractTxtToRamDevice(file["id"])
                # print(type(paragraph))

                chunks = ChunkJournalHelper.chunkParagraphs(paragraphs)

                for i, c in enumerate(chunks):
                    msgs = self.generateBotInstruction(chunks[i])
                    generateTokens = self.generateBotProccess(msgs)
                    self.appendToFileJson(generateTokens)

        except Exception as e:
            print(e)

    def generateBotInstruction(self, textJurnal: str):
        # msgs = [
        #     {
        #         "role": "user",
        #         "content": f"""Anda adalah AI spesialis ekstraksi data pertanian. Tugas Anda adalah mengekstrak informasi dari teks jurnal menjadi format Knowledge Graph (Node-Edge) dalam bentuk JSON murni.
        #         ATURAN EKSTRAKSI:
        #         1. Ekstrak 3 jenis entitas: "Penyakit", "Penyebab" (jamur/bakteri/hama), dan "Penanganan" (solusi/obat/tindakan).
        #         2. Buat relasi antar entitas menggunakan predikat: "Disebabkan oleh" atau "Ditangani dengan".
        #         3. Struktur JSON wajib memiliki array "entities" dan "relations".
        #         4. PENTING: Nilai "subject" dan "object" di dalam array "relations" HARUS menggunakan "id" dari array "entities", BUKAN nama teksnya.
        #         5. Abaikan tabel, gambar, angka statistik, dan daftar pustaka. Jangan tambahkan teks penjelasan apapun di luar blok JSON.

        #         CONTOH OUTPUT YANG DIHARAPKAN:
        #         {{
        #         "entities": [
        #             {{"id": "1", "type": "Penyakit", "name": "Hawar Daun"}},
        #             {{"id": "2", "type": "Penyebab", "name": "Xanthomonas"}},
        #             {{"id": "3", "type": "Penanganan", "name": "Fungisida"}}
        #         ],
        #         "relations": [
        #             {{"id": "r1", "subject": "1", "predicate": "Disebabkan oleh", "object": "2"}},
        #             {{"id": "r2", "subject": "1", "predicate": "Ditangani dengan", "object": "3"}}
        #         ]
        #         }}

        #         TEKS JURNAL:
        #         {textJurnal}

        #         OUTPUT JSON:"""
        #     }
        # ]

        INSTRUKSI = dedent("""\
            Anda adalah AI spesialis ekstraksi Knowledge Graph pertanian.
            Ekstrak informasi dari teks jurnal menjadi JSON murni.

            ATURAN:
            1. Tipe entitas yang diizinkan hanya: "Penyakit", "Penyebab" (jamur/bakteri/virus/hama), "Penanganan" (fungisida, tindakan budidaya, dll).
            2. Predikat yang diizinkan hanya: "Disebabkan oleh" (Penyakit -> Penyebab) dan "Ditangani dengan" (Penyakit -> Penanganan).
            3. Output wajib punya array "entities" dan "relations".
            4. "subject" dan "object" pada relations HARUS berisi id entitas, BUKAN nama.
            5. Setiap entitas unik ditulis SEKALI. Jika entitas yang sama muncul lagi, gunakan id yang sama.
            6. Gunakan nama singkat dan baku (contoh: "Cercospora", "Fungisida"), tanpa kalimat deskriptif.
            7. Hanya ekstrak yang tertulis eksplisit di teks. Jangan menebak. Tidak semua penyakit punya Penyebab atau Penanganan, dan itu boleh.
            8. Abaikan prosedur laboratorium, bahan, alat, tabel, caption gambar, statistik, dan daftar pustaka.
            9. Jika tidak ada informasi relevan, kembalikan {"entities": [], "relations": []}.
            10. Keluarkan HANYA JSON, tanpa penjelasan atau markdown.""")

        CONTOH = [
            # 1. relasi sederhana
            (
                "Bercak daun pada singkong disebabkan oleh jamur Cercospora. "
                "Penyakit ini dapat dikendalikan dengan penyemprotan fungisida.",
                {
                    "entities": [
                        {"id": "1", "type": "Penyakit", "name": "Bercak Daun"},
                        {"id": "2", "type": "Penyebab", "name": "Cercospora"},
                        {"id": "3", "type": "Penanganan", "name": "Fungisida"},
                    ],
                    "relations": [
                        {"id": "r1", "subject": "1", "predicate": "Disebabkan oleh", "object": "2"},
                        {"id": "r2", "subject": "1", "predicate": "Ditangani dengan", "object": "3"},
                    ],
                },
            ),
            # 2. penanganan dipakai bersama + satu penyakit tanpa penanganan
            (
                "Hawar daun disebabkan oleh bakteri Xanthomonas dan ditangani dengan fungisida "
                "serta pemangkasan daun terinfeksi. Karat daun disebabkan oleh Puccinia dan "
                "juga ditangani dengan pemangkasan. Busuk akar disebabkan oleh Fusarium.",
                {
                    "entities": [
                        {"id": "1", "type": "Penyakit", "name": "Hawar Daun"},
                        {"id": "2", "type": "Penyebab", "name": "Xanthomonas"},
                        {"id": "3", "type": "Penanganan", "name": "Fungisida"},
                        {"id": "4", "type": "Penanganan", "name": "Pemangkasan"},
                        {"id": "5", "type": "Penyakit", "name": "Karat Daun"},
                        {"id": "6", "type": "Penyebab", "name": "Puccinia"},
                        {"id": "7", "type": "Penyakit", "name": "Busuk Akar"},
                        {"id": "8", "type": "Penyebab", "name": "Fusarium"},
                    ],
                    "relations": [
                        {"id": "r1", "subject": "1", "predicate": "Disebabkan oleh", "object": "2"},
                        {"id": "r2", "subject": "1", "predicate": "Ditangani dengan", "object": "3"},
                        {"id": "r3", "subject": "1", "predicate": "Ditangani dengan", "object": "4"},
                        {"id": "r4", "subject": "5", "predicate": "Disebabkan oleh", "object": "6"},
                        {"id": "r5", "subject": "5", "predicate": "Ditangani dengan", "object": "4"},
                        {"id": "r6", "subject": "7", "predicate": "Disebabkan oleh", "object": "8"},
                    ],
                },
            ),
            # 3. bagian metode -> kosong
            (
                "Sampel daun dicuci dengan akuades steril, dicelupkan ke alkohol 70%, lalu "
                "ditanam pada media Potato Dextrose Agar dan diinkubasi pada suhu kamar selama "
                "tujuh hari. Suspensi disemprotkan dengan tambahan 2 tetes Tween 80.",
                {"entities": [], "relations": []},
            ),
        ]

        msgs = []
        for i, (teks, hasil) in enumerate(CONTOH):
            prefix = INSTRUKSI + "\n\nTEKS JURNAL:\n" if i == 0 else "TEKS JURNAL:\n"
            msgs.append({"role": "user", "content": prefix + teks})
            msgs.append({"role": "assistant", "content": json.dumps(hasil, ensure_ascii=False)})
        msgs.append({"role": "user", "content": "TEKS JURNAL:\n" + textJurnal})
        return msgs

    def generateBotProccess(self, msgs: list):
        inpts = self.CONNECTION.tokenizer.apply_chat_template(
            msgs,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt"
        ).to(self.CONNECTION.model.device)
    
        print("\n")
        self.logger.info("Memulai proses extraksi dengan LLM...")
        print("\n")
        outputs = self.CONNECTION.model.generate(
            **inpts,
            max_new_tokens=512,
            temperature=0.0,
            do_sample=False
        )
    
        inputLen = inpts["input_ids"].shape[-1]
        generateTokens = outputs[0][inputLen:]

        return generateTokens

    def run(self):
        self.extractJournal()
       

    