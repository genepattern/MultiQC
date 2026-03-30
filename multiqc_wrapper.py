#!/usr/bin/env python3
"""
Wrapper script for MultiQC GenePattern module.

MultiQC aggregates results from multiple bioinformatics tools across many samples
into a single comprehensive HTML report with interactive plots.

Usage (GenePattern command line):
    python run_multiqc.py --input.data <file> [options]

GenePattern Module: MultiQC
Tool Version: 1.14+
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool = False) -> None:
    """Configure logging format and level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Argument Parsing
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description="GenePattern wrapper for MultiQC — aggregate bioinformatics QC reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ---- Required ----
    parser.add_argument(
        "--input.data",
        dest="input_data",
        required=True,
        metavar="FILE",
        help=(
            "A ZIP archive (or directory) containing output files from one or more "
            "supported bioinformatics tools (e.g. FastQC, STAR, Salmon, Picard, Samtools). "
            "MultiQC will automatically detect and parse all recognised file types."
        ),
    )

    # ---- Optional: report cosmetics ----
    parser.add_argument(
        "--report.title",
        dest="report_title",
        default=None,
        metavar="TEXT",
        help=(
            "Title to display at the top of the HTML report "
            "(e.g. 'RNA-seq QC – Project ABC')."
        ),
    )
    parser.add_argument(
        "--report.comment",
        dest="report_comment",
        default=None,
        metavar="TEXT",
        help="Custom comment or note to include at the top of the report.",
    )
    parser.add_argument(
        "--output.filename",
        dest="output_filename",
        default=None,
        metavar="TEXT",
        help=(
            "Filename for the output HTML report (default: multiqc_report.html). "
            "Provide only the filename — the .html extension is optional."
        ),
    )

    # ---- Optional: module selection ----
    parser.add_argument(
        "--modules",
        dest="modules",
        default=None,
        metavar="TEXT",
        help=(
            "Comma-separated list of MultiQC module names to include "
            "(e.g. 'fastqc,star,salmon'). All detected modules are run if omitted."
        ),
    )
    parser.add_argument(
        "--exclude.modules",
        dest="exclude_modules",
        default=None,
        metavar="TEXT",
        help=(
            "Comma-separated list of MultiQC module names to exclude "
            "(e.g. 'fastqc,star')."
        ),
    )

    # ---- Optional: output format ----
    parser.add_argument(
        "--data.format",
        dest="data_format",
        default=None,
        choices=["tsv", "csv", "json", "yaml"],
        metavar="CHOICE",
        help=(
            "Output format for the structured data files in multiqc_data/. "
            "Accepted values: tsv (default), csv, json, yaml."
        ),
    )

    # ---- Optional: boolean-style choices ----
    parser.add_argument(
        "--flat.plots",
        dest="flat_plots",
        default=None,
        metavar="CHOICE",
        help=(
            "Generate flat (static) plots instead of interactive JS plots. "
            "Accepted values: yes / no."
        ),
    )
    parser.add_argument(
        "--export.plots",
        dest="export_plots",
        default=None,
        metavar="CHOICE",
        help=(
            "Export all report plots as PNG/SVG/PDF files alongside the HTML report. "
            "Accepted values: yes / no."
        ),
    )
    parser.add_argument(
        "--prepend.dirs",
        dest="prepend_dirs",
        default=None,
        metavar="CHOICE",
        help=(
            "Prepend the parent directory name to sample names. "
            "Accepted values: yes / no."
        ),
    )

    # ---- Optional: files ----
    parser.add_argument(
        "--sample.names.file",
        dest="sample_names_file",
        default=None,
        metavar="FILE",
        help=(
            "Tab-separated file mapping original sample names to custom display names. "
            "Required columns: 'Sample Name', 'Display Name'."
        ),
    )
    parser.add_argument(
        "--config.file",
        dest="config_file",
        default=None,
        metavar="FILE",
        help="Custom MultiQC YAML configuration file (multiqc_config.yaml).",
    )

    # ---- Optional: inline config ----
    parser.add_argument(
        "--extra.config",
        dest="extra_config",
        default=None,
        metavar="TEXT",
        help=(
            "Inline YAML configuration string passed to MultiQC via --cl-config. "
            "Example: 'report_header_info: [{Contact: name@example.com}]'."
        ),
    )

    # ---- Internal / debug ----
    parser.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Enable verbose/debug logging.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------

_TRUE_VALUES = {"yes", "true", "1"}
_FALSE_VALUES = {"no", "false", "0"}


def _is_truthy(value: str) -> bool:
    """Return True if *value* represents an affirmative choice."""
    return value.strip().lower() in _TRUE_VALUES


def validate_inputs(args: argparse.Namespace) -> None:
    """Validate all input parameters; exit with an informative message on failure."""

    # Required: input.data must exist
    if not os.path.exists(args.input_data):
        logging.error("Input data not found: %s", args.input_data)
        sys.exit(1)

    # Optional file parameters must exist when supplied
    for param_name, file_path in [
        ("sample.names.file", args.sample_names_file),
        ("config.file", args.config_file),
    ]:
        if file_path and not os.path.exists(file_path):
            logging.error("File for --%s not found: %s", param_name, file_path)
            sys.exit(1)

    # Boolean-style choices validation
    for param_name, value in [
        ("flat.plots", args.flat_plots),
        ("export.plots", args.export_plots),
        ("prepend.dirs", args.prepend_dirs),
    ]:
        if value is not None:
            normalised = value.strip().lower()
            if normalised not in _TRUE_VALUES | _FALSE_VALUES:
                logging.error(
                    "Invalid value '%s' for --%s. Accepted values: yes, no.",
                    value,
                    param_name,
                )
                sys.exit(1)

    logging.debug("Input validation passed.")


# ---------------------------------------------------------------------------
# ZIP Extraction Helper
# ---------------------------------------------------------------------------

def prepare_input_directory(input_path: str, work_dir: str) -> str:
    """
    If *input_path* is a ZIP archive, extract it into *work_dir* and return
    *work_dir* as the analysis directory.  Otherwise return *input_path* as-is.
    """
    p = Path(input_path)

    # Check ZIP magic bytes rather than extension alone
    if p.is_file() and zipfile.is_zipfile(p):
        logging.info("Detected ZIP archive — extracting to temporary directory …")
        with zipfile.ZipFile(p, "r") as zf:
            zf.extractall(work_dir)
        logging.info("Extracted %d entries from ZIP.", len(zipfile.ZipFile(p).namelist()))
        return work_dir

    # Treat as a directory or a single flat file
    if p.is_dir():
        logging.info("Input is a directory: %s", input_path)
        return str(p)

    # Single file — use its parent directory so MultiQC can scan it
    logging.info("Input is a single file; using parent directory: %s", p.parent)
    return str(p.parent)


# ---------------------------------------------------------------------------
# Command Construction
# ---------------------------------------------------------------------------

def build_multiqc_command(args: argparse.Namespace, input_dir: str, output_dir: str) -> list:
    """Construct and return the multiqc command as a list of strings."""

    # Determine report filename (strip .html if present)
    if args.output_filename:
        report_name = args.output_filename
        if report_name.lower().endswith(".html"):
            report_name = report_name[:-5]
    else:
        report_name = "multiqc_report"

    cmd = [
        "multiqc",
        input_dir,
        "--outdir", output_dir,
        "--filename", report_name,
        "--force",          # overwrite existing report
    ]

    # Report cosmetics
    if args.report_title:
        cmd.extend(["--title", args.report_title])
    if args.report_comment:
        cmd.extend(["--comment", args.report_comment])

    # Module inclusion (repeated flag for each module)
    if args.modules:
        for mod in args.modules.split(","):
            mod = mod.strip()
            if mod:
                cmd.extend(["--module", mod])

    # Module exclusion (repeated flag for each module)
    if args.exclude_modules:
        for mod in args.exclude_modules.split(","):
            mod = mod.strip()
            if mod:
                cmd.extend(["--exclude", mod])

    # Structured data output format
    if args.data_format:
        cmd.extend(["--data-format", args.data_format])

    # Boolean flags
    if args.flat_plots and _is_truthy(args.flat_plots):
        cmd.append("--flat")

    if args.export_plots and _is_truthy(args.export_plots):
        cmd.append("--export")

    if args.prepend_dirs and _is_truthy(args.prepend_dirs):
        cmd.append("--dirs")

    # Optional files
    if args.sample_names_file:
        cmd.extend(["--sample-names", args.sample_names_file])

    if args.config_file:
        cmd.extend(["--config", args.config_file])

    # Inline YAML config
    if args.extra_config:
        cmd.extend(["--cl-config", args.extra_config])

    return cmd


# ---------------------------------------------------------------------------
# Tool Execution
# ---------------------------------------------------------------------------

def run_multiqc(cmd: list) -> int:
    """
    Execute the multiqc command, stream stdout/stderr to the console, and
    return the process exit code.
    """
    logging.info("Executing: %s", " ".join(cmd))

    try:
        # Stream output line-by-line so GenePattern can capture progress
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            for line in proc.stdout:
                line = line.rstrip("\n")
                if line:
                    print(line, flush=True)
            proc.wait()
            return proc.returncode

    except FileNotFoundError:
        logging.error(
            "MultiQC executable not found. "
            "Ensure 'multiqc' is installed and available on PATH."
        )
        return 2
    except OSError as exc:
        logging.error("OS error while launching MultiQC: %s", exc)
        return 2
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Unexpected error during MultiQC execution: %s", exc)
        return 2


# ---------------------------------------------------------------------------
# Output Validation
# ---------------------------------------------------------------------------

def validate_outputs(output_dir: str, report_name: str) -> bool:
    """
    Check that at least the HTML report was created.  Log a warning (not an
    error) if supplementary data directories are absent.
    """
    # Normalise name
    if not report_name.lower().endswith(".html"):
        report_name = report_name + ".html"

    report_path = Path(output_dir) / report_name
    if not report_path.exists():
        logging.error("Expected report not found: %s", report_path)
        return False

    logging.info("Report created successfully: %s", report_path)
    report_size = report_path.stat().st_size
    logging.info("Report size: %d bytes (%.1f KB)", report_size, report_size / 1024)

    # Check for data directory (non-fatal)
    data_dir = Path(output_dir) / "multiqc_data"
    if data_dir.exists():
        data_files = list(data_dir.iterdir())
        logging.info("Data directory contains %d file(s): %s", len(data_files), data_dir)
    else:
        logging.warning("multiqc_data directory was not created.")

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for the MultiQC GenePattern wrapper."""
    args = parse_arguments()
    setup_logging(verbose=args.verbose)

    logging.info("=== MultiQC GenePattern Wrapper ===")
    logging.info("Input data  : %s", args.input_data)
    logging.info("Output dir  : %s", os.getcwd())

    # Validate all inputs before touching the filesystem
    validate_inputs(args)

    # Determine report filename for later output validation
    if args.output_filename:
        report_name = args.output_filename
        if report_name.lower().endswith(".html"):
            report_name = report_name[:-5]
    else:
        report_name = "multiqc_report"

    output_dir = os.getcwd()

    # Use a temporary directory for ZIP extraction (cleaned up unconditionally)
    work_dir = tempfile.mkdtemp(prefix="multiqc_input_")
    logging.debug("Temporary work directory: %s", work_dir)

    exit_code = 1  # pessimistic default
    try:
        input_dir = prepare_input_directory(args.input_data, work_dir)
        cmd = build_multiqc_command(args, input_dir, output_dir)
        exit_code = run_multiqc(cmd)

        if exit_code == 0:
            # Confirm outputs exist
            if not validate_outputs(output_dir, report_name):
                logging.error("Output validation failed — report file missing.")
                exit_code = 1
            else:
                logging.info("MultiQC completed successfully.")
        else:
            logging.error("MultiQC exited with code %d.", exit_code)

    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Wrapper encountered an unexpected error: %s", exc)
        exit_code = 2
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        logging.debug("Cleaned up temporary directory: %s", work_dir)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
