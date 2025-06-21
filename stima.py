#!/usr/bin/env python3
"""
Script to automatically generate an estimates summary from a markdown quote file.
Usage: python stima.py <markdown_file>
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Configurable parameters
MIN_HOURLY_RATE_DEFAULT = 34
MAX_HOURLY_RATE_DEFAULT = 36
MIN_WEEKLY_HOURS_DEFAULT = 10
MAX_WEEKLY_HOURS_DEFAULT = 13


def parse_markdown_file(file_path):
    """
    Parses the markdown file and extracts phases with their hourly estimates.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    phases = []
    lines = content.split("\n")

    current_phase = None

    for line in lines:
        # Find sections starting with ###
        if (
            line.strip().startswith("### ")
            and not line.strip().startswith("### Riepilogo")
            and not line.strip().startswith("### Stima Economica")
            and not line.strip().startswith("### Timeline")
        ):
            current_phase = line.strip()[4:]  # Remove "### "
            continue

        # Look for the line with "Stima ore"
        if current_phase and line.strip().startswith("**Stima ore**:"):
            # Extract hours using regex
            hours_match = re.search(r"(\d+)[-–](\d+)\s+ore", line)
            if hours_match:
                min_hours = int(hours_match.group(1))
                max_hours = int(hours_match.group(2))
                phases.append(
                    {
                        "name": current_phase,
                        "min_hours": min_hours,
                        "max_hours": max_hours,
                    }
                )
                current_phase = None

    return phases


def copy_to_clipboard(text):
    """
    Copies the text to the clipboard using xclip.
    """
    try:
        # Check if xclip is installed
        subprocess.run(["which", "xclip"], check=True, capture_output=True)

        # Copy to clipboard
        process = subprocess.Popen(
            ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
        )
        process.communicate(input=text.encode("utf-8"))

        if process.returncode == 0:
            return True
        else:
            return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def round_to_multiple(number, multiple=5):
    """
    Rounds a number to the nearest multiple.
    """
    return multiple * round(number / multiple)


def calculate_estimates(
    phases, min_hourly_rate, max_hourly_rate, min_weekly_hours, max_weekly_hours
):
    """
    Calculate total hours, price range and estimated timeline from phases data.
    Returns a tuple containing:
    (total_hours_min, total_hours_max, price_min, price_max, weeks_min, weeks_max)
    """
    # Calculate totals
    total_hours_min = sum(phase["min_hours"] for phase in phases)
    total_hours_max = sum(phase["max_hours"] for phase in phases)

    # Calculate price estimates
    min_price = round_to_multiple(total_hours_min * min_hourly_rate)
    max_price = round_to_multiple(total_hours_max * max_hourly_rate)

    # Calculate timeline
    weeks_min = round(
        total_hours_min / max_weekly_hours
    )  # Best case: min hours with max weekly hours
    weeks_max = round(
        total_hours_max / min_weekly_hours
    )  # Worst case: max hours with min weekly hours

    return (
        total_hours_min,
        total_hours_max,
        min_price,
        max_price,
        weeks_min,
        weeks_max,
    )


def generate_summary(
    phases, min_hourly_rate, max_hourly_rate, min_weekly_hours, max_weekly_hours
):
    """
    Generates the estimates summary in markdown format.
    """
    if not phases:
        print("No phases found in the file.")
        sys.exit(1)

    # Get all calculations from the new function
    (
        total_hours_min,
        total_hours_max,
        min_price,
        max_price,
        min_weeks,
        max_weeks,
    ) = calculate_estimates(
        phases, min_hourly_rate, max_hourly_rate, min_weekly_hours, max_weekly_hours
    )

    # Generate the markdown
    summary_lines = []
    summary_lines.append("---")
    summary_lines.append("")
    summary_lines.append("### Riepilogo stime")
    summary_lines.append("")
    summary_lines.append("| Fase | Ore Min | Ore Max |")
    summary_lines.append("| :--- | :---: | :---: |")

    for phase in phases:
        summary_lines.append(
            f"| {phase['name']} | {phase['min_hours']} | {phase['max_hours']} |"
        )

    summary_lines.append(
        f"| **TOTALE** | **{total_hours_min}** | **{total_hours_max}** |"
    )
    summary_lines.append("")
    summary_lines.append("### Stima economica")
    summary_lines.append("")
    summary_lines.append(
        f"**Range di prezzo: €{min_price:,.0f}".replace(",", ".")
        + f" - €{max_price:,.0f}**".replace(",", ".")
    )
    summary_lines.append("")
    summary_lines.append("### Timeline stimata")
    summary_lines.append("")
    summary_lines.append(f"**{min_weeks}-{max_weeks} settimane** per il completamento.")

    return "\n".join(summary_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Automatically generates an estimates summary from a markdown quote file."
    )
    parser.add_argument("file", help="Markdown quote file to analyze")
    parser.add_argument(
        "-m",
        "--min-hourly-rate",
        type=float,
        default=MIN_HOURLY_RATE_DEFAULT,
        help=f"Minimum hourly rate in euros (default: {MIN_HOURLY_RATE_DEFAULT})",
    )
    parser.add_argument(
        "-M",
        "--max-hourly-rate",
        type=float,
        default=MAX_HOURLY_RATE_DEFAULT,
        help=f"Maximum hourly rate in euros (default: {MAX_HOURLY_RATE_DEFAULT})",
    )
    parser.add_argument(
        "-w",
        "--min-weekly-hours",
        type=float,
        default=MIN_WEEKLY_HOURS_DEFAULT,
        help=f"Minimum weekly hours (default: {MIN_WEEKLY_HOURS_DEFAULT})",
    )
    parser.add_argument(
        "-W",
        "--max-weekly-hours",
        type=float,
        default=MAX_WEEKLY_HOURS_DEFAULT,
        help=f"Maximum weekly hours (default: {MAX_WEEKLY_HOURS_DEFAULT})",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file (default: print to stdout)",
    )
    parser.add_argument(
        "-c",
        "--no-clipboard",
        action="store_true",
        help="Do not automatically copy to clipboard",
    )

    args = parser.parse_args()

    # Check if the file exists
    if not Path(args.file).exists():
        print(f"Error: The file '{args.file}' does not exist.")
        sys.exit(1)

    # Analyze the file
    print(f"Analyzing file: {args.file}")
    print(f"Minimum hourly rate: €{args.min_hourly_rate}")
    print(f"Maximum hourly rate: €{args.max_hourly_rate}")
    print(f"Minimum weekly hours: {args.min_weekly_hours}")
    print(f"Maximum weekly hours: {args.max_weekly_hours}")
    print()

    phases = parse_markdown_file(args.file)

    if not phases:
        print("No phases found in the file. Ensure the format is correct.")
        sys.exit(1)

    print(f"Found {len(phases)} phases:")
    for phase in phases:
        print(f"  - {phase['name']}: {phase['min_hours']}-{phase['max_hours']} hours")
    print()

    # Generate the summary
    summary = generate_summary(
        phases,
        args.min_hourly_rate,
        args.max_hourly_rate,
        args.min_weekly_hours,
        args.max_weekly_hours,
    )

    # Output
    if args.output and args.output != "-":
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"Summary saved to: {args.output}")
        except Exception as e:
            print(f"Error saving file: {e}")
            sys.exit(1)
    else:
        print("=" * 50)
        print("GENERATED SUMMARY:")
        print("=" * 50)
        print(summary)

    # Copy to clipboard (unless --no-clipboard is specified)
    if not args.no_clipboard:
        if copy_to_clipboard(summary):
            print("\n✅ Summary copied to clipboard!")
            print("You can paste it into your markdown file with Ctrl+V")
        else:
            print("\n⚠️  Could not copy to clipboard.")
            print("Ensure xclip is installed: sudo apt install xclip")


if __name__ == "__main__":
    main()
