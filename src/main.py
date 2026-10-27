from Services.KnowledgeGraphPipline import KnowledgeGraphPipline
from Services.GoogleDriveService import GoogleDriveService
import os
from dotenv import load_dotenv
load_dotenv()

if __name__ == '__main__':
    path = "D:/Kuliah/Semester5/IS/Kelompok/LLM/JsonOutput"
    file = "DataMentah.json"

    pipline = KnowledgeGraphPipline(
        "unsloth/gemma-2-9b-it-bnb-4bit",
        path,
        file
    )

    pipline.run()

  


