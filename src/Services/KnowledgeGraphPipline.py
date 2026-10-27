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

    def ExtractJournal(self):
        # textJurnal =  """
        # Penyakit bercak daun pada tanaman singkong umumnya disebabkan oleh jamur Cercospora henningsii. 
        # Gejala awalnya ditandai dengan munculnya bintik-bintik kecil berwarna cokelat yang dikelilingi oleh halo kuning. 
        # Pengendalian dapat dilakukan dengan fungisida berbahan aktif mankozeb.
        # """
        # gDriveLink = os.getenv("FOLDER_GDRIVE")
        # print(gDriveLink)

        try:
            gDriveService = GoogleDriveService()
            listFiles = gDriveService.listFilesInFolder(self.GDRIVEFOLDERID)
    
            txt = ""
            for file in listFiles:
                txt = gDriveService.extractTxtToRamDevice(file["id"])
            print(txt)
        except Exception as e:
            print(e)
        # return textJurnal

    def generateBotInstruction(self):
        textJurnal = self.ExtractJournal()
        msgs = [
            {
                "role": "user",
                "content": "Anda adalah data engineer agrikultur yang bertugas mengekstrak teks jurnal menjadi struktur Knowledge Graph dalam format JSON murni yang valid tanpa teks tambahan. \n\n"+
                f" Ekstrak entitas (Penyakit, Gejala, Solusi) dan relasinya dari teks berikut ke dalam format JSON:\n\n{textJurnal} \n\n"+
                " Pada setiap element JSON nya, buat strukturnya menjadi (Id, type, name) \n\n "+
                " persingkat element name menjadi hanya 1 kalimat saja \n\n"
            }
        ]

        return msgs

    def generateBotProccess(self):
        msgs = self.generateBotInstruction()

        # inpts = self.CONNECTION.tokenizer.apply_chat_template(
        #     msgs,
        #     add_generation_prompt=True,
        #     tokenize=True,
        #     return_dict=True,
        #     return_tensors="pt"
        # ).to(self.CONNECTION.model.device)
    
        print("\n")
        self.logger.info("Memulai proses extraksi dengan LLM...")
        print("\n")
        # outputs = self.CONNECTION.model.generate(
        #     **inpts,
        #     max_new_tokens=512,
        #     temperature=0.0,
        #     do_sample=False
        # )
    
        # inputLen = inpts["input_ids"].shape[-1]
        # generateTokens = outputs[0][inputLen:]

        # return generateTokens
        return ""

    def run(self):
        generateTokens = self.generateBotProccess()
        # hasilJson = self.CONNECTION.tokenizer.decode(generateTokens, skip_special_tokens=True)

        # print("\n")
        # self.logger.info("Membuat JSON ke file DataMentah.json...")
        # CreateFileJson.saveFile(hasilJson, self.pathOutput, self.fileOutput)

    