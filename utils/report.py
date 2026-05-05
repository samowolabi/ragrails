"""
Report printer — formats and prints analytics reports for any ingestor.
"""


def print_report(
    title: str,
    stats: dict,
    sections: list[tuple[str, list]] | None = None,
    start_resources: dict | None = None,
    end_resources: dict | None = None,
    width: int = 52,
) -> None:
    """
    Print a formatted analytics report for any ingestor.

    Args:
        title:            Report heading (e.g. "SCRAPE ANALYTICS REPORT")
        stats:            Flat dict of label → value rows to display
        sections:         Optional extra sections as [(heading, [row_strings])]
        start_resources:  snapshot() result taken before the run
        end_resources:    snapshot() result taken after the run
    """
    w = width
    print("\n" + "═" * w)
    print(f"  {title}")
    print("═" * w)
    for label, value in stats.items():
        print(f"  {label:<20} {value}")

    if sections:
        for heading, rows in sections:
            print("─" * w)
            print(f"  {heading}")
            for row in rows:
                print(f"  {row}")

    if start_resources and end_resources:
        print("─" * w)
        print("  💻  RESOURCE USAGE")
        print(f"  {'CPU (start)':<20} {start_resources['cpu_percent']:.1f}%")
        print(f"  {'CPU (end)':<20} {end_resources['cpu_percent']:.1f}%")
        print(f"  {'Memory (start)':<20} {start_resources['memory_mb']:.1f} MB")
        print(f"  {'Memory (end)':<20} {end_resources['memory_mb']:.1f} MB")
        print(f"  {'Memory delta':<20} {end_resources['memory_mb'] - start_resources['memory_mb']:+.1f} MB")

    print("═" * w + "\n")
