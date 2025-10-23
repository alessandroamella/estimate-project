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
MIN_WEEKLY_HOURS_DEFAULT = 12
MAX_WEEKLY_HOURS_DEFAULT = 16


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
            and not line.strip().startswith("### Riepilogo stime")
            and not line.strip().startswith("### Stima economica")
            and not line.strip().startswith("### Timeline stimata")
        ):
            current_phase = line.strip()[4:]  # Remove "### "
            continue

        # Look for the line with "Stima ore"
        if current_phase and line.strip().startswith("**Stima ore**:"):
            # Extract hours using regex - support both ranges and single values
            # First try to match range format (e.g., "10-15 ore")
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
            else:
                # Try to match single value format (e.g., "5 ore")
                single_hours_match = re.search(r"(\d+)\s+ore", line)
                if single_hours_match:
                    hours = int(single_hours_match.group(1))
                    phases.append(
                        {
                            "name": current_phase,
                            "min_hours": hours,
                            "max_hours": hours,
                        }
                    )
                    current_phase = None

    return phases


def copy_to_clipboard(text):
    """
    Copies the text to the clipboard using pbcopy (macOS) or xclip (Linux).
    """
    import platform

    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            # Use pbcopy on macOS
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(input=text.encode("utf-8"))
            return process.returncode == 0

        elif system == "Linux":
            # Check if xclip is installed on Linux
            subprocess.run(["which", "xclip"], check=True, capture_output=True)

            # Copy to clipboard using xclip
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
            )
            process.communicate(input=text.encode("utf-8"))
            return process.returncode == 0

        else:
            # Unsupported system
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
    phases,
    min_hourly_rate,
    max_hourly_rate,
    min_weekly_hours,
    max_weekly_hours,
    final_quote=False,
):
    """
    Generates the estimates summary in markdown format.
    If final_quote is True, generates a final quote with average values.
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

    if final_quote:
        # Calculate final values as averages
        final_hours = round((total_hours_min + total_hours_max) / 2)
        final_price = round_to_multiple((min_price + max_price) / 2)
        final_weeks = round((min_weeks + max_weeks) / 2)

        summary_lines.append("### Preventivo finale")
        summary_lines.append("")
        summary_lines.append("| Fase | Ore (media) |")
        summary_lines.append("| :--- | :---: |")

        # throw error if phases is empty
        if not phases:
            print("No phases found in the file.")
            sys.exit(1)

        for phase in phases:
            phase_hours = round((phase["min_hours"] + phase["max_hours"]) / 2)
            summary_lines.append(f"| {phase['name']} | {phase_hours} |")

        summary_lines.append(f"| **TOTALE** | **{final_hours}** |")
        summary_lines.append("")
        summary_lines.append("### Costo del progetto")
        summary_lines.append("")
        summary_lines.append(
            f"**Prezzo finale: €{final_price:,.0f}**".replace(",", ".")
        )
        summary_lines.append("")
        summary_lines.append("### Timeline")
        summary_lines.append("")
        summary_lines.append(f"**{final_weeks} settimane** per il completamento.")
    else:
        summary_lines.append("### Riepilogo stime")
        summary_lines.append("")
        summary_lines.append("| Fase | Ore Min | Ore Max |")
        summary_lines.append("| :--- | :---: | :---: |")

        for phase in phases:
            if phase["min_hours"] == phase["max_hours"]:
                # Single value - show only one column
                summary_lines.append(
                    f"| {phase['name']} | {phase['min_hours']} | {phase['max_hours']} |"
                )
            else:
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
        summary_lines.append(
            "_Nota: i costi indicati si riferiscono esclusivamente alle attività di sviluppo. Eventuali costi per servizi esterni (hosting, domini, licenze software, servizi cloud) non sono inclusi nella stima e saranno quantificati separatamente in base alle specifiche esigenze del progetto._"
        )
        summary_lines.append("")
        summary_lines.append("### Timeline stimata")
        summary_lines.append("")
        summary_lines.append(
            f"**{min_weeks}-{max_weeks} settimane** per il completamento."
        )
        summary_lines.append("")
        summary_lines.append(
            "_Nota: la timeline è indicativa e dipende dalla complessità delle implementazioni, eventuali revisioni richieste e disponibilità del team di sviluppo._"
        )

    summary_lines.append("")
    summary_lines.append("### Modalità di pagamento")
    summary_lines.append(
        "Acconto del 50% all'inizio del progetto oppure pagamento a milestone in base agli accordi stabiliti."
    )
    summary_lines.append("")
    summary_lines.append("### Considerazioni finali")
    summary_lines.append(
        "_Le stime si basano sulle specifiche tecniche fornite. Eventuali modifiche sostanziali potrebbero comportare variazioni di costo e timeline._"
    )

    return "\n".join(summary_lines)


def update_markdown_file(file_path, summary, no_edit=False):
    """
    Updates the markdown file by either replacing the existing summary section or appending the new summary.
    Returns True if successful, False otherwise.
    """
    if no_edit:
        return True

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Look for the summary section marker (both estimate and final quote)
        summary_markers = ["---\n\n### Riepilogo stime", "---\n\n### Preventivo finale"]

        summary_index = -1
        for marker in summary_markers:
            index = content.find(marker)
            if index != -1:
                summary_index = index
                break

        if summary_index != -1:
            # Replace everything from the summary marker to the end of file
            new_content = content[:summary_index] + summary
        else:
            # Append summary to the end of the file
            new_content = content.rstrip() + "\n\n" + summary

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(new_content)
        return True
    except Exception as e:
        print(f"Error updating file: {e}")
        return False


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
        "-f",
        "--final",
        action="store_true",
        help="Generate final quote with average values instead of estimate ranges",
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
    parser.add_argument(
        "--no-edit",
        "-e",
        default=False,
        action="store_true",
        help="Do not modify the input file",
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
    if args.final:
        print("Mode: Final quote (average values)")
    else:
        print("Mode: Estimate ranges")
    print()

    phases = parse_markdown_file(args.file)

    if not phases:
        print("No phases found in the file. Ensure the format is correct.")
        sys.exit(1)

    print(f"Found {len(phases)} phases:")
    for phase in phases:
        if phase["min_hours"] == phase["max_hours"]:
            print(f"  - {phase['name']}: {phase['min_hours']} hours")
        else:
            print(
                f"  - {phase['name']}: {phase['min_hours']}-{phase['max_hours']} hours"
            )
    print()

    # Generate the summary
    summary = generate_summary(
        phases,
        args.min_hourly_rate,
        args.max_hourly_rate,
        args.min_weekly_hours,
        args.max_weekly_hours,
        final_quote=args.final,
    )

    # Update the input file unless --no-edit is specified
    if not args.no_edit:
        if update_markdown_file(args.file, summary, args.no_edit):
            print(f"✅ Input file updated: {args.file}")
        else:
            print("⚠️  Failed to update input file")

    # Output to separate file if specified
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
        if args.final:
            print("GENERATED FINAL QUOTE:")
        else:
            print("GENERATED ESTIMATE:")
        print("=" * 50)
        print(summary)

    # Copy to clipboard (unless --no-clipboard is specified)
    if not args.no_clipboard:
        if copy_to_clipboard(summary):
            print("\n✅ Summary copied to clipboard!")
            print(
                "You can paste it into your markdown file with Ctrl+V (or Cmd+V on macOS)"
            )
        else:
            import platform

            system = platform.system()
            print("\n⚠️  Could not copy to clipboard.")
            if system == "Linux":
                print("Ensure xclip is installed: sudo apt install xclip")
            elif system == "Darwin":
                print("pbcopy should be available by default on macOS")
            else:
                print("Clipboard functionality not supported on this system")


if __name__ == "__main__":
    main()
