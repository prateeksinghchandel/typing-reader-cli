from pathlib import Path

class Reader:

    def load(self, chapter: Path) -> str:
        return chapter.read_text(encoding="utf-8")