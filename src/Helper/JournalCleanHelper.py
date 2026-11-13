
import re
class JournalCleanHelper:
    START_RE = re.compile(r"^\s*(\d+\.?\s*)?(pendahuluan|introduction)\s*$", re.IGNORECASE)
    END_RE = re.compile(
        r"^\s*(\d+\.?\s*)?(daftar\s+pustaka|references?|bibliography)\b",
        re.IGNORECASE
    )
    CAPTION_RE = re.compile(r"^\s*(gambar|tabel|figure|table|fig\.)\s*\d+", re.IGNORECASE)
    CAPTION_INLINE_RE = re.compile(r"\b(gambar|tabel|figure|table)\s+\d+\s*[.:]", re.IGNORECASE)
    TERMINAL = (".", "!", "?", ":", ";")

    @staticmethod
    def _normalize(text: str) -> str:
        # angka -> '#', supaya "119" dan "120" dianggap teks yang sama
        return re.sub(r"\d+", "#", text.lower()).strip()

    @staticmethod
    def _readBlocks(page):
        """Ambil blok teks per halaman: sudah disambung per paragraf + koordinat."""
        out = []
        for x0, y0, x1, y1, text, _, btype in page.get_text("blocks"):
            if btype != 0:
                continue
            text = text.replace("-\n", "")
            text = " ".join(text.split())
            if text:
                out.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": text})
        return out

    @staticmethod
    def _readingOrder(blocks, W, fullWidthRatio=0.6) -> list[str]:
        mid = W / 2
        blocks = sorted(blocks, key=lambda b: b["y0"])
        ordered, colBuffer = [], []

        def flush():
            left = sorted([b for b in colBuffer if b["x0"] < mid], key=lambda b: b["y0"])
            right = sorted([b for b in colBuffer if b["x0"] >= mid], key=lambda b: b["y0"])
            ordered.extend(left + right)
            colBuffer.clear()

        for b in blocks:
            if (b["x1"] - b["x0"]) > W * fullWidthRatio:
                flush()
                ordered.append(b)
            else:
                colBuffer.append(b)
        flush()
        return [b["text"] for b in ordered]

    def joinBrokenParagraphs(self, paragraphs: list[str], minParagraphLen: int = 150) -> list[str]:
        out = []
        for p in paragraphs:
            if out:
                prev = out[-1]
                startsLower = p[:1].islower()
                prevLongNoEnd = (len(prev) >= minParagraphLen
                                and not prev.rstrip().endswith(self.TERMINAL))
                # lanjutan: diawali huruf kecil, atau paragraf sebelumnya panjang
                # tapi belum berakhir tanda baca (misal "(Jackson," -> "2010). ...")
                if startsLower or prevLongNoEnd:
                    out[-1] = prev.rstrip() + " " + p.lstrip()
                    continue
            out.append(p)
        return out

    def removeCaptions(self, paragraphs: list[str],
                   maxContinuationLen: int = 120,
                   maxInlineLen: int = 300) -> list[str]:
        out = []
        skipNext = False
        for i, p in enumerate(paragraphs):
            if skipNext:
                skipNext = False
                # lanjutan caption: pendek dan diawali huruf kecil
                if len(p) <= maxContinuationLen and p[:1].islower():
                    continue

            # caption yang diawali "Gambar 1. ..."
            if self.CAPTION_RE.match(p):
                skipNext = True
                continue

            # blok label gambar pendek yang memuat "Gambar 2." di tengah teks
            if len(p) <= maxInlineLen and self.CAPTION_INLINE_RE.search(p):
                continue

            out.append(p)
        return out

    def trimParagraphs(self, paragraphs: list[str]) -> list[str]:
        start = 0
        for i, p in enumerate(paragraphs):
            if self.START_RE.match(p):
                start = i + 1          # +1: heading "PENDAHULUAN" sendiri tidak ikut
                break

        end = len(paragraphs)
        for i in range(len(paragraphs) - 1, start - 1, -1):   # cari dari belakang
            if self.END_RE.match(paragraphs[i]):
                end = i
                break

        return paragraphs[start:end]