import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from kana_rate.parsing import merge_intervals, parse_ass, parse_srt, strip_nonspoken
from kana_rate.reading import KanaReader


def _parse_items(path: Path):
    if path.suffix.lower() == ".srt":
        return parse_srt(str(path))
    if path.suffix.lower() == ".ass":
        return parse_ass(str(path))
    return []


def _episode_rate(items, reader: KanaReader, unit: str) -> float:
    texts = []
    intervals = []
    for start, end, text in items:
        if not text.strip():
            continue
        text = strip_nonspoken(text)
        if not text.strip():
            continue
        texts.append(text)
        intervals.append((start, end))

    total = 0
    for text in texts:
        reading = reader.to_kana(text)
        if unit == "mora":
            total += reader.count_mora(reading)
        else:
            total += reader.count_kana(reading)

    merged = merge_intervals(intervals)
    total_ms = sum(e - s for s, e in merged)
    minutes = total_ms / 1000.0 / 60.0 if total_ms > 0 else 0.0
    return (total / minutes) if minutes > 0 else 0.0


def _line_rates(items, reader: KanaReader, unit: str) -> list[float]:
    rates: list[float] = []
    for start, end, text in items:
        if not text.strip():
            continue
        text = strip_nonspoken(text)
        if not text.strip():
            continue
        duration_ms = end - start
        if duration_ms <= 0:
            continue
        reading = reader.to_kana(text)
        if unit == "mora":
            count = reader.count_mora(reading)
        else:
            count = reader.count_kana(reading)
        if count <= 0:
            continue
        rate = count / (duration_ms / 1000.0 / 60.0)
        rates.append(rate)
    return rates


def _collect_show_dirs(root: Path, exclude_subtitle_backup: bool) -> list[Path]:
    exts = {".srt", ".ass"}
    dirs = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in exts:
            continue
        if exclude_subtitle_backup and "SubtitleBackup" in path.parts:
            continue
        dirs.add(path.parent)
    return sorted(dirs)


def main():
    parser = argparse.ArgumentParser(
        description="Visualize per-episode and per-show subtitle rate distributions."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan for subtitle folders (default: current directory)",
    )
    parser.add_argument(
        "--unit",
        choices=["mora", "kana"],
        default="mora",
        help="Rate unit to compute (default: mora)",
    )
    parser.add_argument(
        "--granularity",
        choices=["episode", "line"],
        default="episode",
        help="Distribution granularity: per episode or per subtitle line (default: episode)",
    )
    parser.add_argument(
        "--include-subtitle-backup",
        action="store_true",
        help="Include SubtitleBackup folders",
    )
    parser.add_argument(
        "--out",
        default="rate_distributions",
        help="Output directory for per-show images (default: rate_distributions)",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    show_dirs = _collect_show_dirs(root, not args.include_subtitle_backup)
    if not show_dirs:
        print("No subtitle folders found.")
        return

    reader = KanaReader()

    show_rates: dict[str, list[float]] = {}
    for d in show_dirs:
        rates = []
        for fname in sorted(d.iterdir()):
            if fname.suffix.lower() not in (".srt", ".ass"):
                continue
            items = _parse_items(fname)
            if args.granularity == "episode":
                rate = _episode_rate(items, reader, args.unit)
                if rate > 0:
                    rates.append(rate)
            else:
                rates.extend(_line_rates(items, reader, args.unit))
        if rates:
            show_rates[d.name] = rates

    if not show_rates:
        print("No valid subtitle entries found.")
        return

    plt.rcParams["font.family"] = "Hiragino Sans"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    def safe_name(name: str) -> str:
        # Preserve Unicode (including CJK). Only replace path-unsafe characters.
        return "".join("_" if ch in ("/", "\0", ":") else ch for ch in name).strip()

    for show, rates in show_rates.items():
        fig, ax = plt.subplots(1, 1, figsize=(8, 4), constrained_layout=True)
        ax.hist(rates, bins=20)
        if args.granularity == "episode":
            subtitle = f"{len(rates)} eps"
        else:
            subtitle = f"{len(rates)} lines"
        ax.set_title(f"{show} ({subtitle}) - {args.unit}/min distribution")
        ax.set_xlabel(f"{args.unit}/min")
        ax.set_ylabel("Episode count")
        filename = safe_name(show) + f"_{args.unit}_{args.granularity}.png"
        out_path = out_dir / filename
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
