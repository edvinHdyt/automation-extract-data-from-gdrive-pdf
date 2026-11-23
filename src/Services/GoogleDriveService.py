import os
import io
import re
import pymupdf
from google.oauth2  import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from utils.LoggerTrait import LoggerTrait
from collections import Counter
from Helper.JournalCleanHelper import JournalCleanHelper

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

    def extractTxtToRamDevice(self, fileId: str,
                                   topZone=0.08, bottomZone=0.07,
                                   maxHeaderLen=150, minRepeat=2) -> list[str]:
        req = self.service.files().get_media(fileId=fileId)
        pdfBuffer = io.BytesIO()
        downloader = MediaIoBaseDownload(pdfBuffer, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        doc = pymupdf.open(stream=pdfBuffer.getvalue(), filetype="pdf")
        paragraphs = []
        try:
            # ---------- PASS 1: baca semua halaman, tandai kandidat header/footer ----------
            pages = []                 # list of (W, H, blocks)
            counter = Counter()

            helperJournalClean = JournalCleanHelper();

            for page in doc:
                W, H = page.rect.width, page.rect.height
                blocks = helperJournalClean._readBlocks(page)
                pages.append((W, H, blocks))

                for b in blocks:
                    inEdge = b["y1"] < H * topZone or b["y0"] > H * (1 - bottomZone)
                    if inEdge and len(b["text"]) <= maxHeaderLen:
                        counter[helperJournalClean._normalize(b["text"])] += 1

            # teks tepi yang muncul >= minRepeat kali = header/footer
            repeated = {t for t, n in counter.items() if n >= minRepeat}

            # ---------- PASS 2: buang header/footer, lalu urutkan baca ----------
            for W, H, blocks in pages:
                kept = []
                for b in blocks:
                    inEdge = b["y1"] < H * topZone or b["y0"] > H * (1 - bottomZone)
                    if inEdge and helperJournalClean._normalize(b["text"]) in repeated:
                        continue
                    kept.append(b)
                paragraphs.extend(helperJournalClean._readingOrder(kept, W))


            paragraphs = helperJournalClean.trimParagraphs(paragraphs)
            paragraphs = helperJournalClean.removeCaptions(paragraphs)
            paragraphs = helperJournalClean.joinBrokenParagraphs(paragraphs)
        finally:
            doc.close()
            pdfBuffer.close()

        return paragraphs
        
    

    

    


    
    