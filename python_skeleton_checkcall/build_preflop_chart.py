from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import csv
import re


RANKS = "23456789TJQKA"
DEALT_RE = re.compile(r"^(?P<name>.+) dealt \[(?P<cards>[^\]]+)\]$")
AWARDED_RE = re.compile(r"^(?P<name>.+) awarded (?P<delta>-?\d+)$")


@dataclass
class HandStat:
    played: int = 0
    wins: float = 0.0

    def win_pct(self) -> float:
        return 0.0 if self.played == 0 else (self.wins / self.played) * 100.0


def canonical_hand_key(cards: list[str]) -> str:
    ranks = [card[0] for card in cards]
    ranks.sort(key=lambda r: RANKS.index(r), reverse=True)
    return "".join(ranks)


def suit_category(cards: list[str]) -> str:
    suits = {card[1] for card in cards}
    if len(suits) == 3:
        return "offsuit"
    if len(suits) == 2:
        return "suited_two"
    return "suited_three"


def parse_gamelog(lines: list[str]) -> dict[str, dict[str, HandStat]]:
    stats: dict[str, dict[str, HandStat]] = {
        "offsuit": defaultdict(HandStat),
        "suited_two": defaultdict(HandStat),
        "suited_three": defaultdict(HandStat),
    }

    current_hands: dict[str, list[str]] = {}
    current_awards: dict[str, int] = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        dealt_match = DEALT_RE.match(line)
        if dealt_match:
            name = dealt_match.group("name")
            cards = dealt_match.group("cards").split()
            current_hands[name] = cards
            continue

        awarded_match = AWARDED_RE.match(line)
        if awarded_match:
            name = awarded_match.group("name")
            delta = int(awarded_match.group("delta"))
            current_awards[name] = delta

        if len(current_hands) == 2 and len(current_awards) == 2:
            deltas = list(current_awards.values())
            if deltas[0] == 0 and deltas[1] == 0:
                winners = {name: 0.5 for name in current_awards.keys()}
            else:
                winners = {name: 1.0 if delta > 0 else 0.0 for name, delta in current_awards.items()}

            for name, cards in current_hands.items():
                category = suit_category(cards)
                key = canonical_hand_key(cards)
                stats[category][key].played += 1
                stats[category][key].wins += winners.get(name, 0.0)

            current_hands = {}
            current_awards = {}

    return stats


def load_existing_stats(csv_path: Path) -> dict[str, HandStat]:
    if not csv_path.exists():
        return {}

    existing: dict[str, HandStat] = {}
    with csv_path.open(newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            hand = row.get("hand")
            if not hand:
                continue
            try:
                played = int(row.get("played", "0"))
            except ValueError:
                played = 0
            try:
                wins = float(row.get("wins", "0"))
            except ValueError:
                wins = 0.0
            existing[hand] = HandStat(played=played, wins=wins)
    return existing


def write_chart(stats: dict[str, dict[str, HandStat]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for category, hands in stats.items():
        output_path = output_dir / f"preflop_chart_{category}.csv"
        existing = load_existing_stats(output_path)
        for hand, stat in existing.items():
            hands[hand].played += stat.played
            hands[hand].wins += stat.wins
        rows = []
        for hand, stat in hands.items():
            rows.append((hand, stat.played, f"{stat.wins:.1f}", f"{stat.win_pct():.4f}"))

        rows.sort(key=lambda row: (-int(row[1]), row[0]))

        with output_path.open("w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["hand", "played", "wins", "win_pct"])
            writer.writerows(rows)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    gamelog_path = repo_root / "gamelog_checkcall_3m.txt"
    if not gamelog_path.exists():
        raise FileNotFoundError(f"Missing gamelog: {gamelog_path}")

    lines = gamelog_path.read_text().splitlines()
    stats = parse_gamelog(lines)
    output_dir = Path(__file__).resolve().parent / "output"
    write_chart(stats, output_dir)


if __name__ == "__main__":
    main()
