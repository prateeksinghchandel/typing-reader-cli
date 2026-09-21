from __future__ import annotations

import textwrap

class TextLayout:

    def wrap(self, text: str, width: int) -> list[str]:
        wrapper = textwrap.TextWrapper(width=width)
        return wrapper.wrap(text=text)
