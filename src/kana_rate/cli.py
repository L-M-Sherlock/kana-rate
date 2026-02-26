import argparse
import glob
import os

from .parsing import merge_intervals, parse_ass, parse_srt, strip_nonspoken
from .reading import KanaReader


def _analyze_items(items, reader: KanaReader):
    texts = []
    intervals = []
    for start, end, text in items:
        if not text.strip():
            continue
        texts.append(text)
        intervals.append((start, end))

    kana_total = 0
    for text in texts:
        text = strip_nonspoken(text)
        if not text.strip():
            continue
        kana_text = reader.to_kana(text)
        kana_total += reader.count_kana(kana_text)

    merged = merge_intervals(intervals)
    total_ms = sum(e - s for s, e in merged)
    minutes = total_ms / 1000.0 / 60.0 if total_ms > 0 else 0.0
    rate = (kana_total / minutes) if minutes > 0 else 0.0
    return kana_total, minutes, rate


def _collect_files(path: str):
    if os.path.isfile(path):
        return [path]
    escaped = glob.escape(path)
    srt_files = sorted(glob.glob(os.path.join(escaped, "*.srt")))
    if srt_files:
        return srt_files
    ass_files = sorted(glob.glob(os.path.join(escaped, "*.ass")))
    return ass_files


def main():
    parser = argparse.ArgumentParser(description="Compute kana-per-minute from subtitles.")
    parser.add_argument("path", help="Subtitle file or directory")
    args = parser.parse_args()

    files = _collect_files(args.path)
    if not files:
        print("No .srt or .ass files found.")
        return

    reader = KanaReader()
    total_kana = 0
    total_minutes = 0.0

    for path in files:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".srt":
            items = parse_srt(path)
        else:
            items = parse_ass(path)
        kana, minutes, rate = _analyze_items(items, reader)
        total_kana += kana
        total_minutes += minutes
        print(f"{os.path.basename(path)}\t{kana} kana\t{minutes:.2f} min\t{rate:.2f} kana/min")

    total_rate = (total_kana / total_minutes) if total_minutes > 0 else 0.0
    print(f"TOTAL\t{total_kana} kana\t{total_minutes:.2f} min\t{total_rate:.2f} kana/min")


if __name__ == "__main__":
    main()
