# FRI <-> NFI Species Composition Converter & Raster Utility

A lightweight, standalone Python package to translate between **Ontario Forest Resource Inventory (FRI / OFRI)** species composition strings and **Canada National Forest Inventory (NFI)** taxonomic representations.

The utility processes single-band categorical rasters and their accompanying Value Attribute Tables (VAT/CSV), translating stand-level species composition attributes while maintaining spatial coordinates, projections, and pixel values.

---

## 1. Background

| System | Format | Example |
| :--- | :--- | :--- |
| **Ontario FRI** | Compressed alphanumeric string of 2-3 letter codes + integer percentages | `Cw  50Sb  40La  10` (50% Eastern White Cedar, 40% Black Spruce, 10% Tamarack) |
| **Canada NFI** | Relational records: 4-letter genus, 3-letter species, optional variety, float percentage | `[['THUJ', 'OCC', None, 50.0], ['PICE', 'MAR', None, 40.0], ['LARI', 'LAR', None, 10.0]]` |

The tool embeds the full dictionary of **107 Ontario tree species** with bidirectional lookup support.

---

## 2. Directory Structure

```text
fri_nfi_tool/
├── __init__.py               # Package exports and versioning
├── __main__.py               # Module execution entry point (python -m fri_nfi_tool)
├── converter.py              # Standalone conversion engine & CLI
├── demo.py                   # Self-contained runnable demonstration script
├── notebook_walkthrough.ipynb # Interactive Jupyter Notebook for data science workflows
├── pyproject.toml            # PEP 517/621 packaging specification
├── requirements.txt          # Dependencies (standard library + optional rasterio)
├── README.md                 # This documentation
└── sample_data/
    ├── sample_raster.tif     # Real-world forest stand raster (GeoTIFF)
    └── sample_attr_table.csv # Input attribute table with Value & OSPCOMP columns
```

---

## 3. Quick Start

### Prerequisites
- Python 3.8 or higher.
- Standard library modules only (`csv`, `json`, `re`, `pathlib`, `typing`, `logging`, `argparse`).
- *(Optional)* `rasterio` for GeoTIFF manipulation. If not installed, rasters are safely duplicated using binary file copying.
- *(Optional)* `pandas` and `jupyter` if running the interactive notebook.

### Run the Interactive Jupyter Notebook
Open and run [notebook_walkthrough.ipynb](notebook_walkthrough.ipynb):
```bash
jupyter notebook notebook_walkthrough.ipynb
```

### Run the Console Demo Script
Run the included demonstration script to verify the installation and see the conversion on sample data:

```bash
python demo.py
```

This will:
1. Demonstrate string parsing and round-trip conversion (`FRI -> NFI -> Reconstructed FRI`).
2. Read `sample_data/sample_raster.tif` and `sample_data/sample_attr_table.csv`.
3. Output the converted raster and enriched attribute table (`output_nfi_raster.tif` and `output_nfi_attr.csv`).
4. Display a preview of the converted table directly in the console.

---

## 4. Usage Guide

### A. Command-Line Interface (CLI)

The tool can be run either directly via `converter.py` or as a module via `-m`:

```bash
# Direct script execution
python converter.py <input_raster.tif> <input_attr.csv> -o <output_raster.tif> -a <output_attr.csv> [options]

# Or as a module from parent directory
python -m fri_nfi_tool <input_raster.tif> <input_attr.csv> -o <output_raster.tif> -a <output_attr.csv> [options]
```

#### Arguments
- `raster_in` *(positional)*: Path to input raster (`.tif`).
- `attr_in` *(positional)*: Path to input attribute table (`.csv`).
- `-o`, `--raster_out` *(required)*: Path where the output raster will be written.
- `-a`, `--attr_out` *(required)*: Path where the converted attribute table will be written.
- `--spp_col`: Name of the column containing FRI species strings (e.g. `OSPCOMP` or `spp_code`). Auto-detected if omitted.
- `--strict`: Enable to raise an error if species percentages in a string do not sum to 100%.
- `-v`, `--verbose`: Enable detailed debug logging.

#### Example Command
```bash
python converter.py sample_data/sample_raster.tif sample_data/sample_attr_table.csv -o output_raster.tif -a output_attr.csv --spp_col OSPCOMP
```

---

### B. Python API

You can import and use the utility functions directly in your own scripts:

```python
from fri_nfi_tool import (
    fri_to_nfi,
    nfi_to_fri,
    convert_fri_attribute_table,
    process_raster_and_attribute_table,
    SpeciesConversionError,
)

# 1. Parse and convert a single FRI string
nfi_records = fri_to_nfi("Cw  50Sb  40La  10")
# Returns:
# [
#   {'genus': 'THUJ', 'species': 'OCC', 'variety': None, 'percent': 50.0, 'fri_code': 'Cw'},
#   {'genus': 'PICE', 'species': 'MAR', 'variety': None, 'percent': 40.0, 'fri_code': 'Sb'},
#   {'genus': 'LARI', 'species': 'LAR', 'variety': None, 'percent': 10.0, 'fri_code': 'La'}
# ]

# 2. Reconstruct FRI string from NFI entries
fri_str = nfi_to_fri(nfi_records)
# Returns: 'Cw50Sb40La10'

# 3. Process an entire CSV attribute table
convert_fri_attribute_table(
    input_csv_path="sample_data/sample_attr_table.csv",
    output_csv_path="output_table.csv",
    spp_column_name="OSPCOMP"
)

# 4. End-to-end raster + attribute table processing
process_raster_and_attribute_table(
    input_raster_path="sample_data/sample_raster.tif",
    input_attr_table_path="sample_data/sample_attr_table.csv",
    output_raster_path="output_raster.tif",
    output_attr_table_path="output_table.csv",
    spp_column_name="OSPCOMP"
)
```

---

## 5. Output Table Schema

The output CSV preserves all original columns (e.g. `Value`, `Count`, `OID_`, `OSPCOMP`) and adds:

| Column Name | Description | Example |
| :--- | :--- | :--- |
| `nfi_summary` | Clean human-readable summary | `THUJ OCC 50% \| PICE MAR 40% \| LARI LAR 10%` |
| `leading_spp` | Dominant species call and % | `THUJ OCC (50%)` |
| `nfi_json` | Complete serialized JSON list | `[{"genus": "THUJ", "species": "OCC", ...}]` |
| `spp1_genus`, `spp1_species`, `spp1_percent` | Primary species columns for GIS joins | `THUJ`, `OCC`, `50.0` |
| `spp2_genus`, `spp2_species`, `spp2_percent` | Secondary species columns | `PICE`, `MAR`, `40.0` |
| `spp3_genus`, `spp3_species`, `spp3_percent` | Tertiary species columns | `LARI`, `LAR`, `10.0` |

---

## 6. Common FRI Species Code Reference

| FRI Code | NFI Genus | NFI Species | Scientific Name | Common English Name |
| :---: | :---: | :---: | :--- | :--- |
| **Sb** | `PICE` | `MAR` | *Picea mariana* | Black Spruce |
| **Sw** | `PICE` | `GLA` | *Picea glauca* | White Spruce |
| **Pj** | `PINU` | `BAN` | *Pinus banksiana* | Jack Pine |
| **Pr** | `PINU` | `RES` | *Pinus resinosa* | Red Pine |
| **Pw** | `PINU` | `STR` | *Pinus strobus* | Eastern White Pine |
| **Bf** | `ABIE` | `BAL` | *Abies balsamea* | Balsam Fir |
| **Cw** | `THUJ` | `OCC` | *Thuja occidentalis* | Eastern White Cedar |
| **La** | `LARI` | `LAR` | *Larix laricina* | Tamarack / Eastern Larch |
| **Pt** | `POPU` | `TRE` | *Populus tremuloides* | Trembling Aspen |
| **Pb** | `POPU` | `BAL` | *Populus balsamifera* | Balsam Poplar |
| **Bw** | `BETU` | `PAP` | *Betula papyrifera* | White Birch / Paper Birch |
| **By** | `BETU` | `ALL` | *Betula alleghaniensis* | Yellow Birch |
| **Mh** | `ACER` | `SAH` | *Acer saccharum* | Sugar / Hard Maple |
| **Mr** | `ACER` | `RUB` | *Acer rubrum* | Red Maple |
| **He** | `TSUG` | `CAN` | *Tsuga canadensis* | Eastern Hemlock |
| **OC** | `GENC` | `SPP` | Coniferous | Other Conifer |
| **OH** | `GENH` | `SPP` | Deciduous | Other Hardwood |
