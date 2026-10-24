"""Turn per-reply scores into rates, a markdown table and a chart."""
from __future__ import annotations

from pathlib import Path

KEYS = ("valid", "kind_ok", "exact", "early", "late")


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    rate = (lambda k: sum(bool(r[k]) for r in rows) / n) if n else (lambda k: 0.0)
    return {"n": n, "valid": rate("valid"), "kind_acc": rate("kind_ok"), "exact": rate("exact"),
            "early": rate("early"), "late": rate("late")}


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def write_report(summaries: dict[str, dict[str, dict]], out_dir: Path) -> None:
    """summaries: {set_name: {system: summary}}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for set_name, systems in summaries.items():
        n = next(iter(systems.values()))["n"] if systems else 0
        lines += [f"### {set_name} ({n} replies)", "",
                  "| System | Exact date ↑ | Too early ↓ | Kind ↑ | Valid JSON ↑ |", "|---|---|---|---|---|"]
        for name, s in systems.items():
            lines.append(f"| {name} | {_pct(s['exact'])} | {_pct(s['early'])} | {_pct(s['kind_acc'])} | "
                         f"{_pct(s['valid'])} |")
        lines.append("")
    (out_dir / "table.md").write_text("\n".join(lines), encoding="utf-8")
    _chart(summaries, out_dir / "chart.png")


def _chart(summaries: dict[str, dict[str, dict]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sets = list(summaries)
    fig, axes = plt.subplots(1, len(sets), figsize=(5 * len(sets), 3.6), facecolor="#121212", squeeze=False)
    for ax, set_name in zip(axes[0], sets):
        systems = summaries[set_name]
        names, vals = list(systems), [100 * s["early"] for s in systems.values()]
        ax.set_facecolor("#121212")
        bars = ax.bar(names, vals, color="#FF6B35")
        ax.bar_label(bars, labels=[f"{v:.0f}%" for v in vals], color="#F2EDE4")
        ax.set_title(f"Too-early reminders · {set_name}", color="#F2EDE4")
        ax.tick_params(colors="#F2EDE4")
        for side in ax.spines.values():
            side.set_color("#0F4C5C")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
