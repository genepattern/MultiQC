# MultiQC (v1.0)

**Description**: Aggregate results from bioinformatics analyses across many samples into a single interactive HTML report.
**Authors**: Philip Ewels; SciLifeLab / Babraham Bioinformatics
**Contact**: https://groups.google.com/forum/#!forum/multiqc
**Algorithm Version**: Not applicable

## Summary

Modern high-throughput sequencing experiments generate large volumes of quality control (QC) data from many different bioinformatics tools — FastQC, STAR, Salmon, Picard, Samtools, and dozens more. Manually reviewing individual QC reports for every sample quickly becomes impractical. **MultiQC** solves this problem by automatically searching a directory of analysis output files, recognizing and parsing the results of over 100 supported bioinformatics tools, and collating all of those results into a single, interactive HTML report.

The resulting report provides:
- **A general statistics summary table** aggregating key metrics (e.g., total reads, % aligned, % duplicates) across all samples side by side.
- **Per-tool interactive plots** (bar charts, line graphs, heatmaps, etc.) that let you quickly spot trends, outliers, or failed samples at a glance.
- **Structured data export** (TSV, JSON, or YAML) containing all parsed metrics for downstream programmatic analysis or integration into LIMS systems.

MultiQC fits naturally into any sequencing workflow: run your individual QC and analysis tools as usual, then point MultiQC at the directory containing all their output files. It will find and parse them automatically — no manual configuration is required for standard use cases.

Within GenePattern, the MultiQC module wraps the command-line MultiQC tool inside a standardized, reproducible compute environment. Users simply supply the directory of analysis outputs, optionally customize the report through configuration parameters, and receive the finished HTML report and structured data files as outputs.

### Supported Tools (examples)
MultiQC supports results from tools including: FastQC, fastp, Cutadapt, Trim Galore!, STAR, HISAT2, Bowtie 2, TopHat, BWA, Bismark, Salmon, Kallisto, featureCounts, HTSeq, Samtools, Picard, GATK, QualiMap, RSeQC, deepTools, Kraken 2, and many more. For a full list, see the [MultiQC supported modules documentation](https://multiqc.info/modules/).

## References

- Ewels P, Magnusson M, Lundin S, Käller M. **MultiQC: summarize analysis results for multiple tools and samples in a single report.** *Bioinformatics*. 2016;32(19):3047–3048. doi:[10.1093/bioinformatics/btw354](https://doi.org/10.1093/bioinformatics/btw354)
- MultiQC Documentation: https://multiqc.info/docs/

## Source Links
* [MultiQC Source Code (GitHub)](https://github.com/ewels/MultiQC)
* [MultiQC Docker Image (quay.io)](https://quay.io/repository/biocontainers/multiqc)
* [MultiQC Official Website](https://multiqc.info/)

## Parameters

| Name | Description | Default Value |
| :--- | :--- | :--- |
| input.dir * | Directory containing output files from supported bioinformatics tools to be aggregated into the report | |
| output.prefix | Prefix string to use for the names of the output report and data directory | `multiqc` |
| config.file | Custom MultiQC YAML configuration file for advanced report customization | |
| module | Name(s) of specific MultiQC module(s) to run (comma-separated); if not specified, all detected modules are run | |
| exclude | Name(s) of MultiQC module(s) to exclude from the report (comma-separated) | |
| ignore | Glob-style pattern(s) for analysis files to ignore when scanning the input directory | |
| sample.names | Tab-separated file mapping original detected sample names to custom display names | |
| template | Report template to use for the HTML output | `default` |
| tag | Restrict the report to only MultiQC modules that are tagged with the specified keyword | |
| view.tags | If enabled, display the list of available module tags and exit without generating a report | |
| ignore.samples | Pattern(s) for sample names to ignore; matching samples will be excluded from the report | |
| flat | If enabled, generate only flat (static, non-interactive) plots instead of interactive JavaScript-based plots | |
| interactive | If enabled, generate only interactive plots (forces interactive mode, overriding flat mode) | |
| export | If enabled, export all report plots as static image files (PNG, SVG, PDF) in addition to the HTML report | |
| data.dir | If enabled, force creation of the parsed data directory (multiqc_data) even if it would not be created by default | |
| no.data.dir | If enabled, prevent creation of the parsed data directory | |
| data.format | Output format for structured data files in the multiqc_data directory | `tsv` |
| zip.data.dir | If enabled, compress the parsed data directory into a ZIP archive | |
| force | If enabled, overwrite an existing report and data directory if they already exist | |
| verbose | If enabled, increase logging output verbosity for debugging | |
| quiet | If enabled, suppress all console output except errors | |

\* required

## Input Files

1. **input.dir**
    The primary input: a directory containing output files from one or more supported bioinformatics tools. MultiQC recursively searches this directory for any files it recognizes (based on filename patterns and content). No specific file naming convention is required beyond what the originating tool produces — MultiQC's automatic detection handles the rest. Supported file types span a broad range of tools, including:
    - **Read QC**: FastQC (`.zip`, `fastqc_data.txt`), fastp (JSON reports), Cutadapt/Trim Galore logs
    - **Alignment**: STAR (`Log.final.out`), HISAT2, Bowtie 2, BWA, TopHat logs
    - **Quantification**: Salmon (`logs/`), Kallisto (`run_info.json`)
    - **Post-alignment QC**: Samtools (`flagstat`, `stats`, `idxstats`), Picard metrics files, RSeQC outputs, QualiMap outputs, deepTools outputs
    - **Variant calling**: GATK, bcftools stats
    - **Other**: featureCounts summaries, HTSeq logs, Kraken 2 reports, Bismark bisulfite reports

2. **sample.names** *(optional)*
    A plain-text, tab-separated file (`.txt` or `.tsv`) with two columns and a header row that maps internal or auto-detected sample names to custom display names. Column headers should be `Sample Name` (first column, the name as MultiQC detects it from the input files) and `New Name` (second column, the desired display name for the report). This is particularly useful for replacing cryptic SRR accession numbers or internal identifiers with meaningful project-specific labels.

    Example format:
    ```
    Sample Name	New Name
    SRR1234567	Patient_A_Tumor
    SRR1234568	Patient_A_Normal
    ```

3. **config.file** *(optional)*
    A YAML-formatted MultiQC configuration file (typically named `multiqc_config.yaml`). This file allows advanced customization of the report, including: custom report header metadata (project name, contact, instrument, date), module run order, ignored filename patterns, custom sample name cleaning rules, table column visibility and ordering, color scheme overrides, and more. See the [MultiQC documentation on configuration](https://multiqc.info/docs/#configuring-multiqc) for a full reference.

    Example minimal config:
    ```yaml
    report_header_info:
      - Project: "RNA-seq Pilot Study"
        Contact: "researcher@institution.edu"
        Application: "RNA-seq"
    ```

## Output Files

1. **`<output.prefix>_report.html`** (default: `multiqc_report.html`)
    The primary output: a self-contained, interactive HTML report summarizing the QC and analysis metrics from all detected tools and samples. Open this file in any modern web browser (Chrome, Firefox, Edge, Safari). The report contains:
    - A **General Statistics** table with key metrics for every sample
    - **Per-module sections** with interactive plots (bar charts, line graphs, box plots, heatmaps) for each detected tool
    - A **Search and filter** bar for finding samples within the report
    - Configurable column visibility and highlighting tools

2. **`<output.prefix>_data/`** (default: `multiqc_data/`)
    A directory of structured data files containing all parsed metrics in machine-readable format. Contents include:
    - `multiqc_general_stats.<format>` — General statistics table data
    - `multiqc_<tool>.<format>` — Per-tool parsed metrics (one file per detected tool)
    - `multiqc_sources.<format>` — List of all input files parsed
    - `multiqc.log` — Execution log with info on detected files and any warnings
    The format of these files is controlled by the `data.format` parameter (TSV, JSON, or YAML).

3. **`<output.prefix>_plots/`** *(only when `export` is enabled)*
    A directory containing all report plots exported as static image files (PNG, SVG, and PDF), organized into subdirectories by format. Useful for extracting publication-quality figures directly from the report.

## Example Data

**Input:**
Example input data (a collection of FastQC output files for multiple samples) is available from the MultiQC test data repository:
- [MultiQC Test Data (GitHub)](https://github.com/ewels/MultiQC_TestData)
- Direct download: `git clone https://github.com/ewels/MultiQC_TestData.git`

**Output:**
An example MultiQC report generated from test data is available on the MultiQC website:
- [Example MultiQC Report](https://multiqc.info/examples/rna-seq/multiqc_report.html)

## Requirements

- **Execution Environment**: This module runs inside a Docker container and does not require any local software installation.
- **Docker Image**: `quay.io/biocontainers/multiqc:1.14--pyhdfd78af_0` (or equivalent version tag)
- **Operating System**: Linux (within Docker container; compatible with GenePattern server on any OS)
- **Memory**: Typically 2–8 GB RAM depending on the number of samples and tools. Very large datasets (1000+ samples) may require increased memory allocation.
- **Disk Space**: Proportional to the size of the input directory. The output HTML report is usually 1–50 MB; the data directory is typically small.
- **Python**: Python 3.8+ (provided within the Docker image)
- **Browser**: A modern web browser (Chrome, Firefox, Edge, or Safari) is required to view the interactive HTML report output.

## License

MultiQC is released under the **GNU General Public License v3 (GPLv3)**.
- Full license text: [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html)
- MultiQC license on GitHub: [https://github.com/ewels/MultiQC/blob/master/LICENSE](https://github.com/ewels/MultiQC/blob/master/LICENSE)

The GenePattern module wrapper is made available for research use under the same license terms.

## Version Comments

| Version | Release Date | Description |
| :--- | :--- | :--- |
| 1.0 | 2024-01-01 | Initial release of the MultiQC GenePattern module, wrapping MultiQC v1.14. Supports all standard MultiQC parameters including report customization, module filtering, flat/interactive plot selection, and structured data export in TSV, JSON, and YAML formats. |
