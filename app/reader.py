import mmap
from pathlib import Path

class Reader:

    def __init__(self, page_size: int = 4096) -> None:
        self.page_size = page_size

    def load(self, chapter: Path) -> str:
        return chapter.read_text(encoding="utf-8")

    def _trim_to_utf8_boundary(self, raw: bytes) -> bytes:
        start = 0
        while start < len(raw) and (raw[start] & 0xC0) == 0x80:
            start += 1
        end = len(raw)
        while end > start and (raw[end - 1] & 0xC0) == 0x80:
            end -= 1
        return raw[start:end]

    def load_page(self, chapter: Path, offset: int = 0, size: int | None = None) -> str:
        if size is None:
            size = self.page_size
        with open(chapter, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                total = len(mm)
                raw_start = min(offset, total)
                raw_end = min(offset + size, total)
                raw = mm[raw_start:raw_end]
                trimmed = self._trim_to_utf8_boundary(raw)
                return trimmed.decode(encoding="utf-8")

    def page_count(self, chapter: Path) -> int:
        total = chapter.stat().st_size
        return max(1, (total + self.page_size - 1) // self.page_size)

    def load_text_range(self, chapter: Path, start: int, end: int) -> str:
        with open(chapter, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                raw = mm[start:end]
        return self._trim_to_utf8_boundary(raw).decode(encoding="utf-8")
