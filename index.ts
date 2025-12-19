#!/usr/bin/env bun

/**
 * Script to automatically generate an estimates summary from a markdown quote file.
 * Usage: npm start -- <markdown_file> [options]
 */

import fs from "node:fs";
import chalk from "chalk";
import clipboardy from "clipboardy";
import { Command } from "commander";

// --- Configuration ---

const HOURLY_RATE_DEFAULT = 35;
const WEEKLY_HOURS_DEFAULT = 15;
const DOWN_PAYMENT_PERCENTAGE_DEFAULT = 50;

// --- Type Definitions ---

interface Phase {
  name: string;
  minHours: number;
  maxHours: number;
}

interface EstimateCalculations {
  totalHoursMin: number;
  totalHoursMax: number;
  priceMin: number;
  priceMax: number;
  weeksMin: number;
  weeksMax: number;
}

// --- Core Functions ---

/**
 * Parses the markdown file and extracts phases with their hourly estimates.
 */
function parseMarkdownFile(filePath: string): Phase[] {
  let content: string;
  try {
    content = fs.readFileSync(filePath, "utf-8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      console.error(`Error: File '${filePath}' not found.`);
    } else {
      console.error(`Error reading file: ${(error as Error).message}`);
    }
    process.exit(1);
  }

  const phases: Phase[] = [];
  const lines = content.split("\n");
  let currentPhase: string | null = null;
  const excludedHeaders = [
    "### Riepilogo stime",
    "### Stima economica",
    "### Timeline stimata",
    "### Preventivo finale",
    "### Costo del progetto",
    "### Timeline"
  ];

  console.log(`Parsing ${lines.length} lines from file...`);

  for (const line of lines) {
    const trimmedLine = line.trim();
    // Find sections starting with ###, excluding summary sections
    if (trimmedLine.startsWith("### ") && !excludedHeaders.some(h => trimmedLine.startsWith(h))) {
      currentPhase = trimmedLine.substring(4); // Remove "### "
      console.log(`Found phase: "${chalk.green(`${currentPhase}`)}"`);
      continue;
    }

    // Look for the line with "Stima ore"
    if (currentPhase && trimmedLine.startsWith("**Stima ore**:")) {
      console.log(
        `${chalk.gray(
          '  ├─ Found "Stima ore" line for phase'
        )}: "${currentPhase}" → "${trimmedLine}"`
      );
      // Try to match range format (e.g., "10-15 ore")
      const rangeMatch = trimmedLine.match(/(\d+)[-–](\d+)\s+ore/);
      if (rangeMatch) {
        const minHours = parseInt(rangeMatch[1]!, 10);
        const maxHours = parseInt(rangeMatch[2]!, 10);
        console.log(`${chalk.gray("  ├─ ✓ Parsed hours range:")} ${minHours}-${maxHours} ore`);
        phases.push({
          name: currentPhase,
          minHours,
          maxHours
        });
        currentPhase = null;
      } else {
        // Try to match single value format (e.g., "5 ore")
        const singleMatch = trimmedLine.match(/(\d+)\s+ore/);
        if (singleMatch) {
          const hours = parseInt(singleMatch[1]!, 10);
          console.log(`${chalk.gray("  ├─ ✓ Parsed single hours value:")} ${hours} ore`);
          phases.push({ name: currentPhase, minHours: hours, maxHours: hours });
          currentPhase = null;
        } else {
          console.log(
            `${chalk.gray("  ├─ ✗ Warning: Could not parse hours from line:")} "${chalk.yellow(
              trimmedLine
            )}"`
          );
        }
      }
    } else if (currentPhase && trimmedLine.includes("ore") && trimmedLine.includes("Stima")) {
      console.log(
        `${chalk.gray(
          '  ├─ Note: Found line with "Stima" and "ore" but doesn\'t match expected format:'
        )} "${chalk.yellow(trimmedLine)}"`
      );
    }
  }

  console.log(`Successfully parsed ${phases.length} phases\n`);
  return phases;
}

/**
 * Copies the text to the clipboard.
 */
function copyToClipboard(text: string): boolean {
  try {
    clipboardy.writeSync(text);
    return true;
  } catch (error) {
    console.warn(`Warning: Could not copy to clipboard: ${(error as Error).message}`);
    return false;
  }
}

/**
 * Rounds a number to the nearest multiple.
 */
function roundToMultiple(num: number, multiple = 5): number {
  return multiple * Math.round(num / multiple);
}

/**
 * Rounds a number to a specified number of decimal digits.
 */
function roundToDigits(num: number, digits: number): number {
  const factor = 10 ** digits;
  return Math.round(num * factor) / factor;
}

/**
 * Calculates total hours, price range, and estimated timeline from phases data.
 */
// CHANGED: The function now accepts a single hourlyRate and weeklyHours.
function calculateEstimates(
  phases: Phase[],
  hourlyRate: number,
  weeklyHours: number
): EstimateCalculations {
  const totalHoursMin = phases.reduce((sum, phase) => sum + phase.minHours, 0);
  const totalHoursMax = phases.reduce((sum, phase) => sum + phase.maxHours, 0);

  // CHANGED: Price is calculated based on the single hourly rate.
  const priceMin = roundToMultiple(totalHoursMin * hourlyRate);
  const priceMax = roundToMultiple(totalHoursMax * hourlyRate);

  // CHANGED: Weeks are calculated based on the single weekly hours value.
  const weeksMin = Math.round(totalHoursMin / weeklyHours);
  const weeksMax = Math.round(totalHoursMax / weeklyHours);

  return {
    totalHoursMin,
    totalHoursMax,
    priceMin,
    priceMax,
    weeksMin,
    weeksMax
  };
}

/**
 * Generates the estimates summary in markdown format.
 */
// CHANGED: Updated the function signature and destructuring to use the new options.
function generateSummary(
  phases: Phase[],
  {
    hourlyRate,
    weeklyHours,
    finalQuote,
    downPaymentPercentage,
    milestones,
    feedbackWindowWeeks
  }: {
    hourlyRate: number;
    weeklyHours: number;
    finalQuote: boolean;
    downPaymentPercentage: number;
    milestones: number;
    feedbackWindowWeeks: number;
  }
): string {
  // CHANGED: The call to calculateEstimates now passes the single rate and hours.
  const { totalHoursMin, totalHoursMax, priceMin, priceMax, weeksMin, weeksMax } =
    calculateEstimates(phases, hourlyRate, weeklyHours);

  const formatPrice = (price: number, digits?: number) => {
    const roundedPrice = Number.isInteger(digits) ? roundToDigits(price, digits!) : price;
    return new Intl.NumberFormat("it-IT", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    }).format(roundedPrice);
  };
  const summaryLines: string[] = [];
  summaryLines.push("---", "");

  if (finalQuote) {
    const finalHours = Math.round((totalHoursMin + totalHoursMax) / 2);
    // Calcola il prezzo basandosi sulle ore GIÀ ARROTONDATE
    const finalPrice = finalHours * hourlyRate;
    const finalWeeks = Math.round((weeksMin + weeksMax) / 2);

    summaryLines.push("### Preventivo finale", "");
    summaryLines.push("| Fase | Ore (media) |");
    summaryLines.push("| :--- | :---: |");
    phases.forEach(phase => {
      const phaseHours = Math.round((phase.minHours + phase.maxHours) / 2);
      summaryLines.push(`| ${phase.name} | ${phaseHours} |`);
    });
    summaryLines.push(`| **TOTALE** | **${finalHours}** |`, "");
    summaryLines.push("### Costo del progetto", "");
    const calculatedRate = formatPrice(finalPrice / finalHours, 0);
    summaryLines.push(`Stima effort (ore): ${finalHours}`, "");
    summaryLines.push(`Tariffa oraria: €${calculatedRate}`, "");
    summaryLines.push(`**Prezzo finale: €${formatPrice(finalPrice, 2)}**`, "");
    summaryLines.push("### Timeline", "");
    summaryLines.push(`**${finalWeeks} settimane** per il completamento.`);
  } else {
    summaryLines.push("### Riepilogo stime", "");
    summaryLines.push("| Fase | Ore Min | Ore Max |");
    summaryLines.push("| :--- | :---: | :---: |");
    phases.forEach(phase => {
      summaryLines.push(`| ${phase.name} | ${phase.minHours} | ${phase.maxHours} |`);
    });
    summaryLines.push(`| **TOTALE** | **${totalHoursMin}** | **${totalHoursMax}** |`, "");
    summaryLines.push("### Stima economica", "");
    summaryLines.push(
      `**Range di prezzo: €${formatPrice(priceMin)} - €${formatPrice(priceMax)}**`,
      ""
    );
    summaryLines.push(
      "_Nota: i costi indicati si riferiscono esclusivamente alle attività di sviluppo. Eventuali costi per servizi esterni (hosting, domini, licenze software, servizi cloud) non sono inclusi nella stima e saranno quantificati separatamente in base alle specifiche esigenze del progetto._",
      ""
    );
    summaryLines.push("### Timeline stimata", "");
    summaryLines.push(`**${weeksMin}-${weeksMax} settimane** per il completamento.`, "");
    summaryLines.push(
      "_Nota: la timeline è indicativa e dipende dalla complessità delle implementazioni, eventuali revisioni richieste e disponibilità del team di sviluppo._"
    );
  }

  summaryLines.push("", "### Modalità di pagamento");
  if (milestones > 0) {
    summaryLines.push(`Acconto in base ai ${milestones} milestone stabiliti.`, "");
  } else {
    summaryLines.push(
      `Acconto del ${downPaymentPercentage}% all'inizio del progetto, seguito dal saldo alla consegna.`,
      ""
    );
  }
  summaryLines.push("", "### Finestra di feedback");
  summaryLines.push(
    `Le modifiche e le correzioni dovranno essere comunicate **entro ${feedbackWindowWeeks} settimane** dal completamento della relativa fase. Dopo questo periodo, i cambiamenti richiesti saranno soggetti a una nuova stima dei costi e dei tempi.  \nFanno eccezione esclusivamente eventuali malfunzionamenti gravi o evidenti, che saranno comunque risolti entro tempi congrui.`,
    ""
  );
  summaryLines.push("### Considerazioni finali");
  summaryLines.push(
    "_Le stime si basano sulle specifiche tecniche fornite. Eventuali modifiche sostanziali potrebbero comportare variazioni di costo e timeline._"
  );

  return summaryLines.join("\n");
}

/**
 * Updates the markdown file by replacing or appending the summary.
 */
function updateMarkdownFile(filePath: string, summary: string): boolean {
  try {
    const content = fs.readFileSync(filePath, "utf-8");

    const summaryMarkers = ["---\n\n### Riepilogo stime", "---\n\n### Preventivo finale"];
    let summaryIndex = -1;

    for (const marker of summaryMarkers) {
      const index = content.indexOf(marker);
      if (index !== -1) {
        console.log(
          `Found existing summary marker at index ${chalk.yellow(index)}:\n"${chalk.bgGrey(
            marker
          )}"\n`
        );
        summaryIndex = index;
        break;
      }
    }

    console.log("Updating markdown file with new summary...");

    let newContent: string;
    if (summaryIndex !== -1) {
      newContent = content.substring(0, summaryIndex) + summary;
      console.log(
        `Replacing existing summary starting at index ${chalk.yellow(
          summaryIndex
        )} with new summary:\n"${chalk.gray(summary).substring(0, 50)}"\n${chalk.reset(
          "[truncated]"
        )}`
      );
    } else {
      newContent = `${content.trimEnd()}\n\n${summary}`;
    }

    console.log(`Writing updated content to file: ${chalk.blue(filePath)}`);

    fs.writeFileSync(filePath, newContent, "utf-8");
    return true;
  } catch (error) {
    console.error(`Error updating file: ${(error as Error).message}`);
    return false;
  }
}

/**
 * Main script execution function.
 */
async function main() {
  const program = new Command();

  program
    .name("stima-ts")
    .description("Automatically generates an estimates summary from a markdown quote file.")
    .version("1.0.0")
    .argument("<file>", "Markdown quote file to analyze")
    // CHANGED: Replaced the four min/max options with two single-value options.
    .option("-r, --hourly-rate <number>", "The hourly rate in euros", String(HOURLY_RATE_DEFAULT))
    .option(
      "-w, --weekly-hours <number>",
      "The number of hours worked per week",
      String(WEEKLY_HOURS_DEFAULT)
    )
    .option(
      "-d, --down-payment <number>",
      "Down payment percentage",
      String(DOWN_PAYMENT_PERCENTAGE_DEFAULT)
    )
    .option("-m, --milestones <number>", "Number of payment milestones", "0")
    .option("--feedback-window <number>", "Feedback review window in weeks", "2")
    .option(
      "-f, --final",
      "Generate final quote with average values instead of estimate ranges",
      false
    )
    .option("-o, --output <file>", "Output file (default: print to stdout)")
    .option("-c, --no-clipboard", "Do not automatically copy to clipboard", false)
    .option("-e, --no-edit", "Do not modify the input file", false)
    .action(async (file, options) => {
      // CHANGED: The options object now reflects the new CLI arguments.
      const opts = {
        hourlyRate: parseFloat(options.hourlyRate),
        weeklyHours: parseFloat(options.weeklyHours),
        downPaymentPercentage: parseFloat(options.downPayment),
        milestones: parseInt(options.milestones),
        feedbackWindowWeeks: parseInt(options.feedbackWindow),
        finalQuote: options.final
      };

      if (!fs.existsSync(file)) {
        console.error(`Error: The file '${file}' does not exist.`);
        process.exit(1);
      }

      console.log("Analyzing with options:");
      for (const [key, value] of Object.entries({ file, ...opts })) {
        console.log(`${chalk.gray(`  ├─ ${key}:`)} ${chalk.green(`${value}`)}`);
      }
      console.log();

      const phases = parseMarkdownFile(file);

      if (phases.length === 0) {
        console.error("No phases found in the file. Ensure the format is correct.");
        process.exit(1);
      }

      console.log(`Found ${phases.length} phases:`);
      phases.forEach(phase => {
        const hourRange =
          phase.minHours === phase.maxHours
            ? `${phase.minHours} hours`
            : `${phase.minHours}-${phase.maxHours} hours`;
        console.log(`  - ${phase.name}: ${chalk.blue(hourRange)}`);
      });
      console.log();

      const summary = generateSummary(phases, opts);

      if (!options.noEdit && updateMarkdownFile(file, summary)) {
        console.log(`Input file updated: ${chalk.blue(file)}`);
      } else if (!options.noEdit) {
        console.log("⚠️  Failed to update input file");
      }

      if (options.output) {
        try {
          fs.writeFileSync(options.output, summary, "utf-8");
          console.log(`Summary saved to: ${options.output}`);
        } catch (error) {
          console.error(`Error saving file: ${(error as Error).message}`);
          process.exit(1);
        }
      } else {
        console.log(
          "\n" +
            chalk.bgBlue.whiteBright.bold(
              opts.finalQuote ? "Generated final quote:" : "Generated estimate:"
            )
        );
        console.log(chalk.gray(summary));
      }

      if (!options.noClipboard && copyToClipboard(summary)) {
        console.log("\n✅ Summary copied to clipboard!");
      } else if (!options.noClipboard) {
        console.log("\n⚠️  Could not copy to clipboard. Ensure a clipboard utility is available.");
      }
    });

  await program.parseAsync(process.argv);
}

main().catch(error => {
  console.error("An unexpected error occurred:", error);
  process.exit(1);
});
