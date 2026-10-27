import os
import io
import re
import pdfplumber
from google.oauth2  import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from utils.LoggerTrait import LoggerTrait

class GoogleDriveService(LoggerTrait):
    credentialPath: str
    service: build
    SCOPES: list

    def __init__(self, credentialPath: str = "credentials.json"):
        try:
            self.SCOPES = ["https://www.googleapis.com/auth/drive"]
            self.creds = service_account.Credentials.from_service_account_file(
                credentialPath,
                scopes = self.SCOPES
            )

            self.service = build("drive", "v3", credentials=self.creds)
        except Exception as e:
            self.logger.error("Terjadi kesalahan autentikasi Gdrive")
            raise Exception(f"Terjadi kesalahan autentikasi: {e}")

    def listFilesInFolder(self, folderId: str) -> list:
        query = f"'{folderId}' in parents and trashed = false"

        res = self.service.files().list(
            q=query,
            pageSize=50,
            fields="files(id, name, mimeType)"
        ).execute()

        items = res.get("files", [])

        if len(items)  == 0:
            self.logger.error("Tidak ada file")
            return []

        return items

    def extractTxtToRamDevice(self, fileId: str) -> str:
        req = self.service.files().get_media(fileId=fileId)

        pdfBuffer = io.BytesIO()
        downloader = MediaIoBaseDownload(pdfBuffer, req)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        pdfBuffer.seek(0)

        cleanedPages = []
        with pdfplumber.open(pdfBuffer) as pdf:
            for page in pdf.pages:
                tables = page.find_tables()

                # filter mengabaikan element dari tabel
                def not_in_table(obj):
                    for table in tables:
                        x0, top, x1, bottom = table.bbox
                        if(x0 <=obj["x0"]<= x1) and (top <= obj["top"] <= bottom):
                            return False
                    return True

                pageWithoutTables = page.filter(not_in_table)
                text = pageWithoutTables.extract_text()

                if text:
                    cleanedPages.append(text)

        pdfBuffer.close()
        del pdfBuffer
        
        fullTxt = "\n".join(cleanedPages)
        patternCaption = r'(?i)(Gambar|Tabel|Figure|Table)\s+\d+.*?(?=\n|$)'
        fullTxt = re.sub(patternCaption, '', fullTxt)

        return fullTxt


        
        