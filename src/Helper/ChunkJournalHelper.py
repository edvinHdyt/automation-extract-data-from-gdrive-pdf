

class ChunkJournalHelper:

    @staticmethod
    def __joinedLen(parts:list[str])->int:
        return sum(len(x) for x in parts) + 2 * max(len(parts) - 1, 0)

    @staticmethod
    def chunkParagraphs(paragraphs: list[str],
                        maxChars: int = 3000,
                        overlapsChars: int = 300) -> list[str]:
        chunks = []
        current = []

        for p in paragraphs:
            if current and ChunkJournalHelper.__joinedLen(current + [p]) > maxChars:
                chunks.append("\n\n".join(current))

                carry = []
                for prev in reversed(current):
                    if ChunkJournalHelper.__joinedLen([prev] + carry) > overlapsChars:
                        break
                    carry.insert(0, prev)

                if ChunkJournalHelper.__joinedLen(carry + [p]) > maxChars:
                    carry  = []
                current = carry

            current.append(p)

        if current:
            chunks.append("\n\n".join(current))

        return chunks