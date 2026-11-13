from Lib.ModelConn import ModelConn
import utils.CreateFileJson as CreateFileJson
from utils.LoggerTrait import LoggerTrait
from Services.GoogleDriveService import GoogleDriveService
import os
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
                txt = ""
                
                txt = gDriveService.extractTxtToRamDevice(file["id"])
                # print(txt)
                # msgs = self.generateBotInstruction(txt)
                # generateTokens = self.generateBotProccess(msgs)
                # self.appendToFileJson(generateTokens)

        except Exception as e:
            print(e)

    def generateBotInstruction(self, textJurnal: str):
        msgs = [
            {
                "role": "user",
                "content": f"""Anda adalah AI spesialis ekstraksi data pertanian. Tugas Anda adalah mengekstrak informasi dari teks jurnal menjadi format Knowledge Graph (Node-Edge) dalam bentuk JSON murni.
                ATURAN EKSTRAKSI:
                1. Ekstrak 3 jenis entitas: "Penyakit", "Penyebab" (jamur/bakteri/hama), dan "Penanganan" (solusi/obat/tindakan).
                2. Buat relasi antar entitas menggunakan predikat: "Disebabkan oleh" atau "Ditangani dengan".
                3. Struktur JSON wajib memiliki array "entities" dan "relations".
                4. PENTING: Nilai "subject" dan "object" di dalam array "relations" HARUS menggunakan "id" dari array "entities", BUKAN nama teksnya.
                5. Abaikan tabel, gambar, angka statistik, dan daftar pustaka. Jangan tambahkan teks penjelasan apapun di luar blok JSON.

                CONTOH OUTPUT YANG DIHARAPKAN:
                {{
                "entities": [
                    {{"id": "1", "type": "Penyakit", "name": "Hawar Daun"}},
                    {{"id": "2", "type": "Penyebab", "name": "Xanthomonas"}},
                    {{"id": "3", "type": "Penanganan", "name": "Fungisida"}}
                ],
                "relations": [
                    {{"id": "r1", "subject": "1", "predicate": "Disebabkan oleh", "object": "2"}},
                    {{"id": "r2", "subject": "1", "predicate": "Ditangani dengan", "object": "3"}}
                ]
                }}

                TEKS JURNAL:
                {textJurnal}

                OUTPUT JSON:"""
            }
        ]

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
       

    