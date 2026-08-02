from pathlib import Path

class BookLoader:
    def __init__(self, library_path: str | Path):
        self.library= Path(library_path)
        if not self.library.is_dir():
             raise FileNotFoundError(f"{self.library} is not a directory")

    def list_books(self) -> list[Path]:
        books=[]
        for i in self.library.iterdir():
            if i.is_dir():
                books.append(i)
        return sorted(books, key=lambda p: p.name)

    def list_chapters(self,book: str) -> list[Path]:
        chapters= []
        book_path= self.library / book
        if not book_path.is_dir():
             raise FileNotFoundError(f"Book '{book}' not found")
        for i in book_path.iterdir():
                    if i.is_file() and i.suffix.lower() == ".txt":
                        chapters.append(i)
        return sorted(chapters, key=lambda p: p.name)

    def chapter_path(self, book: str, chapter: str) -> Path:
        path = self.library / book / chapter
        if not path.is_file():
             raise FileNotFoundError(f"Chapter '{chapter}' not found")
        return path
