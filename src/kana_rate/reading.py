import re
from typing import Iterable

from sudachipy import dictionary
from sudachipy import tokenizer as sudachi_tokenizer


KANA_RE = re.compile(r"[\u3040-\u309F\u30A0-\u30FF]")


class KanaReader:
    def __init__(self):
        self._tokenizer = dictionary.Dictionary().create()
        self._mode = sudachi_tokenizer.Tokenizer.SplitMode.C

    def to_kana(self, text: str) -> str:
        parts = []
        for token in self._tokenizer.tokenize(text, self._mode):
            reading = token.reading_form()
            if reading == "*":
                reading = token.surface()
            parts.append(reading)
        return "".join(parts)

    @staticmethod
    def count_kana(text: str) -> int:
        return len(KANA_RE.findall(text))


def total_kana_count(reader: KanaReader, texts: Iterable[str]) -> int:
    count = 0
    for t in texts:
        kana = reader.to_kana(t)
        count += reader.count_kana(kana)
    return count
