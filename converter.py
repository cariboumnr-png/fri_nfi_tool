"""
FRI <-> NFI species composition converter and raster VAT processor.

Provides bidirectional conversion between Ontario Forest Resource Inventory
(FRI / OFRI) species composition strings and Canada National Forest
Inventory (NFI) taxonomic records, along with tools to process raster Value
Attribute Tables (VAT).
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import csv
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union

# Optional dependency for GeoTIFF raster I/O
try:
    import rasterio  # type: ignore[import-not-found]
    HAS_RASTERIO = True
except ImportError:
    rasterio = None  # type: ignore[assignment]
    HAS_RASTERIO = False

logger = logging.getLogger(__name__)


# =====================================================================
# Custom Exceptions
# =====================================================================


class SpeciesConversionError(ValueError):
    """Base exception for species composition conversion errors."""


class UnknownSpeciesCodeError(SpeciesConversionError, KeyError):
    """Raised when an unknown species code is encountered."""


class InvalidCompositionFormatError(SpeciesConversionError):
    """Raised when a species composition string or sum is invalid."""


# =====================================================================
# Type Definitions
# =====================================================================

NfiSpeciesTuple = Tuple[str, str, Optional[str]]
PathLike = Union[str, os.PathLike[str], Path]


class NfiSpeciesEntry(TypedDict):
    """Structured dictionary representation of an NFI species entry."""

    genus: str
    species: str
    variety: Optional[str]
    percent: float
    fri_code: str


# =====================================================================
# Reference Mappings (107 Ontario Tree Species)
# =====================================================================

FRI_TO_NFI_CODES: Dict[str, NfiSpeciesTuple] = {
    "OC": ("GENC", "SPP", None),
    "OH": ("GENH", "SPP", None),
    "Bf": ("ABIE", "BAL", None),
    "Mf": ("ACER", "SPP", None),
    "Mm": ("ACER", "NEG", None),
    "Mb": ("ACER", "NIG", None),
    "Mp": ("ACER", "PEN", None),
    "Mn": ("ACER", "PLA", None),
    "Mr": ("ACER", "RUB", None),
    "Ms": ("ACER", "SAC", None),
    "Mh": ("ACER", "SAH", None),
    "Mt": ("ACER", "SPI", None),
    "MX": ("ACER", "SPP", None),
    "Hc": ("AESC", "HIP", None),
    "AL": ("ALNU", "SPP", None),
    "Pa": ("ASIM", "TRI", None),
    "By": ("BETU", "ALL", None),
    "Bc": ("BETU", "LEN", None),
    "Bw": ("BETU", "PAP", None),
    "Bp": ("BETU", "PEN", None),
    "Bg": ("BETU", "POP", None),
    "Bb": ("CARP", "CAR", None),
    "Hb": ("CARY", "COR", None),
    "Hp": ("CARY", "SPP", None),
    "Hl": ("CARY", "SPP", None),
    "Hs": ("CARY", "OVA", None),
    "Hi": ("CARY", "SPP", None),
    "Hm": ("CARY", "TOM", None),
    "Cd": ("CAST", "DEN", None),
    "Cat": ("CATA", "SPE", None),
    "Hk": ("CELT", "OCC", None),
    "Red": ("CERC", "CAN", None),
    "Ht": ("CRAT", "SPP", None),
    "Be": ("FAGU", "GRA", None),
    "Aw": ("FRAX", "AME", None),
    "Ab": ("FRAX", "NIG", None),
    "Ag": ("FRAX", "PEN", None),
    "Ap": ("FRAX", "SPP", None),
    "Aq": ("FRAX", "QUA", None),
    "AX": ("FRAX", "SPP", None),
    "Gt": ("GLED", "TRI", None),
    "Kk": ("GYMN", "DIO", None),
    "Haz": ("HAMA", "VIR", None),
    "PO": ("POPU", "SPP", None),
    "Bn": ("JUGL", "CIN", None),
    "Wb": ("JUGL", "NIG", None),
    "Cr": ("JUNI", "VIR", None),
    "Le": ("LARI", "DEC", None),
    "La": ("LARI", "LAR", None),
    "Lj": ("LARI", "SPP", None),
    "Tp": ("LIRI", "TUL", None),
    "Ct": ("MAGN", "ACU", None),
    "Mo": ("MORU", "RUB", None),
    "Gb": ("NYSS", "SYL", None),
    "Iw": ("OSTR", "VIR", None),
    "Sn": ("PICE", "ABI", None),
    "Sw": ("PICE", "GLA", None),
    "Sk": ("PICE", "SPP", None),
    "Sb": ("PICE", "MAR", None),
    "Sc": ("PICE", "PUN", None),
    "Sr": ("PICE", "RUB", None),
    "SX": ("PICE", "SPP", None),
    "Pj": ("PINU", "BAN", None),
    "Pn": ("PINU", "NIG", None),
    "Pr": ("PINU", "RES", None),
    "Pp": ("PINU", "RIG", None),
    "PX": ("PINU", "SPP", None),
    "Pw": ("PINU", "STR", None),
    "Ps": ("PINU", "SYL", None),
    "Sy": ("PLAT", "OCC", None),
    "Pe": ("POPU", "ALB", None),
    "Pb": ("POPU", "BAL", None),
    "Pc": ("POPU", "SPP", None),
    "Pd": ("POPU", "DEL", None),
    "Pl": ("POPU", "GRA", None),
    "Pt": ("POPU", "TRE", None),
    "Cm": ("PRUN", "AVI", None),
    "Cs": ("PRUN", "SPP", None),
    "Cp": ("PRUN", "PEN", None),
    "Cb": ("PRUN", "SER", None),
    "CH": ("PRUN", "SPP", None),
    "Cc": ("PRUN", "VIR", None),
    "Ow": ("QUER", "ALB", None),
    "Osw": ("QUER", "BIC", None),
    "Ob": ("QUER", "MAC", None),
    "Och": ("QUER", "MUE", None),
    "Obl": ("QUER", "SPP", None),
    "Op": ("QUER", "PAL", None),
    "Or": ("QUER", "RUB", None),
    "Os": ("QUER", "SHU", None),
    "OX": ("QUER", "SPP", None),
    "Lb": ("ROBI", "PSE", None),
    "LO": ("ROBI", "SPP", None),
    "Wi": ("SALI", "SPP", None),
    "Ss": ("SASS", "ALB", None),
    "Ema": ("SORB", "AUC", None),
    "AM": ("SORB", "SPP", None),
    "Cw": ("THUJ", "OCC", None),
    "CE": ("THUJ", "SPP", None),
    "Bd": ("TILI", "AME", None),
    "Ll": ("TILI", "SPP", None),
    "Bl": ("TILI", "SPP", None),
    "He": ("TSUG", "CAN", None),
    "Ew": ("ULMU", "AME", None),
    "Er": ("ULMU", "RUB", None),
    "EX": ("ULMU", "SPP", None),
    "Eu": ("ULMU", "THO", None),
}

# Invert dictionary: (GENUS, SPECIES, VARIETY) -> FRI code
NFI_TO_FRI_CODES: Dict[NfiSpeciesTuple, str] = {}
for _fri, _nfi in FRI_TO_NFI_CODES.items():
    if _nfi not in NFI_TO_FRI_CODES:
        NFI_TO_FRI_CODES[_nfi] = _fri


# =====================================================================
# Core Conversion Functions
# =====================================================================


def parse_fri_spp_string(
    spp_str: Optional[str],
    strict_sum: bool = False,
) -> List[Tuple[str, float]]:
    """Parse an Ontario FRI species string into code and percentage tuples.

    Args:
        spp_str: The raw FRI species composition string (e.g.
            'Cw  50Sb  40La  10' or 'Sb 100').
        strict_sum: If True, raises InvalidCompositionFormatError when the
            percentages do not sum to exactly 100.0%.

    Returns:
        A list of (species_code, percentage) tuples. Returns an empty list
        if the input is None, whitespace, or empty.

    Raises:
        InvalidCompositionFormatError: If strict_sum is True and percentages
            do not sum to 100%.

    Examples:
        >>> parse_fri_spp_string('Cw  50Sb  40La  10')
        [('Cw', 50.0), ('Sb', 40.0), ('La', 10.0)]
        >>> parse_fri_spp_string('Sb 100')
        [('Sb', 100.0)]
        >>> parse_fri_spp_string(' ')
        []
    """
    if spp_str is None:
        return []

    cleaned = str(spp_str).replace(" ", "").strip()
    if not cleaned or cleaned.lower() in ("none", "null", "nan"):
        return []

    pattern = r"([a-zA-Z]{2,3})(\d{1,3})"
    matches = re.findall(pattern, cleaned)
    if not matches:
        return []

    result: List[Tuple[str, float]] = []
    total_pct = 0.0

    for spp, digits in matches:
        pct = float(digits)
        result.append((spp, pct))
        total_pct += pct

    if strict_sum and round(total_pct, 1) != 100.0:
        raise InvalidCompositionFormatError(
            f"Species percentages in '{spp_str}' do not sum to 100% "
            f"(sum={total_pct:.1f})"
        )

    return result


def fri_to_nfi(
    fri_str: Optional[str],
    strict_sum: bool = False,
    ignore_unknown: bool = False,
) -> List[NfiSpeciesEntry]:
    """Convert an Ontario FRI species string to a list of NFI species entries.

    Args:
        fri_str: Input FRI species composition string.
        strict_sum: Enforce that species percentages must sum to 100%.
        ignore_unknown: If True, skips unrecognized species codes instead of
            raising an UnknownSpeciesCodeError.

    Returns:
        List of NfiSpeciesEntry dictionaries with NFI taxonomic details and
        percentages.

    Raises:
        UnknownSpeciesCodeError: If a species code is not in FRI_TO_NFI_CODES
            and ignore_unknown is False.
        InvalidCompositionFormatError: If strict_sum is True and percentages
            do not sum to 100%.

    Examples:
        >>> fri_to_nfi('Sb 70La 30')
        [{'genus': 'PICE', 'species': 'MAR', 'variety': None, 'percent': 70.0, 'fri_code': 'Sb'},
         {'genus': 'LARI', 'species': 'LAR', 'variety': None, 'percent': 30.0, 'fri_code': 'La'}]
    """
    parsed = parse_fri_spp_string(fri_str, strict_sum=strict_sum)
    nfi_entries: List[NfiSpeciesEntry] = []

    for spp_code, pct in parsed:
        if spp_code not in FRI_TO_NFI_CODES:
            if ignore_unknown:
                logger.warning(
                    "Skipping unrecognized FRI species code: %s", spp_code
                )
                continue
            raise UnknownSpeciesCodeError(
                f"FRI species code '{spp_code}' not recognized in mapping."
            )

        nfi_tuple = FRI_TO_NFI_CODES[spp_code]
        nfi_entries.append(
            {
                "genus": nfi_tuple[0],
                "species": nfi_tuple[1],
                "variety": nfi_tuple[2],
                "percent": pct,
                "fri_code": spp_code,
            }
        )

    return nfi_entries


def nfi_to_fri(
    nfi_entries: Union[
        Sequence[Sequence[Any]],
        Sequence[Mapping[str, Any]],
    ],
) -> str:
    """Convert NFI species entries back into an Ontario FRI species string.

    Supports entries supplied either as:
      - A sequence of 4-element sequences: [('PICE', 'MAR', None, 70.0), ...]
      - A sequence of mappings: [{'genus': 'PICE', 'species': 'MAR', ...}]

    Args:
        nfi_entries: A sequence of NFI species records.

    Returns:
        Reconstructed FRI string (e.g. 'Sb70La30').

    Raises:
        ValueError: If entry format or fields are malformed.
        UnknownSpeciesCodeError: If an NFI taxonomic tuple has no known FRI code.
        TypeError: If an entry is neither a sequence nor a mapping.

    Examples:
        >>> nfi_to_fri([['PICE', 'MAR', None, 70.0], ['LARI', 'LAR', None, 30.0]])
        'Sb70La30'
    """
    fri_parts: List[str] = []

    for entry in nfi_entries:
        if isinstance(entry, (list, tuple)):
            if len(entry) < 4:
                raise ValueError(
                    "NFI sequence entry must contain [GENUS, SPECIES, VARIETY, PERCENT]"
                )
            genus = str(entry[0])
            species = str(entry[1])
            variety = str(entry[2]) if entry[2] is not None else None
            pct = float(entry[3])
        elif isinstance(entry, Mapping):
            genus_val = entry.get("genus")
            species_val = entry.get("species")
            variety_val = entry.get("variety")
            pct = float(entry.get("percent", 0.0))

            if not isinstance(genus_val, str) or not isinstance(species_val, str):
                raise ValueError(
                    f"Entry must contain string 'genus' and 'species': {entry}"
                )
            genus = genus_val
            species = species_val
            variety = str(variety_val) if variety_val is not None else None
        else:
            raise TypeError(
                f"Expected sequence or mapping for NFI entry, got {type(entry).__name__}"
            )

        key: NfiSpeciesTuple = (genus, species, variety)
        if key not in NFI_TO_FRI_CODES:
            raise UnknownSpeciesCodeError(
                f"NFI species tuple {key} not found in reverse FRI lookup."
            )

        fri_code = NFI_TO_FRI_CODES[key]
        fri_parts.append(f"{fri_code}{int(round(pct))}")

    return "".join(fri_parts)


# =====================================================================
# Attribute Table Processing
# =====================================================================


def convert_fri_attribute_table(
    input_csv_path: PathLike,
    output_csv_path: PathLike,
    spp_column_name: Optional[str] = None,
    value_column_name: str = "Value",
    max_species_columns: int = 5,
    strict_sum: bool = False,
    ignore_unknown: bool = True,
) -> List[Dict[str, Any]]:
    """Convert FRI species strings in a CSV attribute table to NFI records.

    Reads an input raster attribute table (CSV), parses the species
    composition column, and writes an augmented CSV table containing:
      - All original attributes (e.g. Value, Count).
      - `nfi_json`: Complete serialized JSON list of NFI records.
      - `nfi_summary`: Clean human-readable summary string.
      - `leading_spp`: Dominant species and percentage.
      - Flattened columns for GIS joins (`spp1_genus`, `spp1_species`, etc.).

    Args:
        input_csv_path: Path to the input FRI attribute table CSV.
        output_csv_path: Path where the converted NFI table will be saved.
        spp_column_name: Column containing FRI species strings. If None,
            automatically identifies candidates like 'OSPCOMP' or 'spp_code'.
        value_column_name: Name of the raster pixel value column.
        max_species_columns: Number of individual species slots to expand.
        strict_sum: Enforce that species percentages must sum to 100%.
        ignore_unknown: Skip unrecognized species codes without crashing.

    Returns:
        List of converted row dictionaries.

    Raises:
        FileNotFoundError: If input_csv_path does not exist.
        ValueError: If input CSV is empty or species column cannot be found.
    """
    input_path = Path(input_csv_path).resolve()
    output_path = Path(output_csv_path).resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Attribute table not found: {input_path}")

    with input_path.open(mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, Any]] = [dict(r) for r in reader]
        fieldnames: List[str] = list(reader.fieldnames) if reader.fieldnames else []

    if not rows:
        raise ValueError(f"Input CSV is empty: {input_path}")

    if value_column_name and value_column_name not in fieldnames:
        logger.warning(
            "Value column '%s' not present in table fields: %s",
            value_column_name,
            fieldnames,
        )

    if spp_column_name is None:
        candidates = [
            "OSPCOMP",
            "spp_code",
            "SPP_CODE",
            "SPECIES",
            "spp",
            "species_comp",
        ]
        for candidate in candidates:
            if candidate in fieldnames:
                spp_column_name = candidate
                break
        if spp_column_name is None:
            raise ValueError(
                f"Could not automatically detect species column among: {fieldnames}. "
                f"Please specify 'spp_column_name'."
            )

    logger.info("Using species composition column: '%s'", spp_column_name)

    output_rows: List[Dict[str, Any]] = []
    for row in rows:
        new_row: Dict[str, Any] = dict(row)
        raw_spp = row.get(spp_column_name, "")

        nfi_list = fri_to_nfi(
            str(raw_spp) if raw_spp is not None else "",
            strict_sum=strict_sum,
            ignore_unknown=ignore_unknown,
        )

        new_row["nfi_json"] = json.dumps(nfi_list)

        if nfi_list:
            summary_parts = [
                f"{item['genus']} {item['species']}"
                + (f" {item['variety']}" if item["variety"] else "")
                + f" {int(round(item['percent']))}%"
                for item in nfi_list
            ]
            new_row["nfi_summary"] = " | ".join(summary_parts)
            leading = max(nfi_list, key=lambda x: x["percent"])
            new_row["leading_spp"] = (
                f"{leading['genus']} {leading['species']} "
                f"({int(round(leading['percent']))}%)"
            )
        else:
            new_row["nfi_summary"] = ""
            new_row["leading_spp"] = ""

        for idx in range(1, max_species_columns + 1):
            if idx <= len(nfi_list):
                spp_item = nfi_list[idx - 1]
                new_row[f"spp{idx}_genus"] = spp_item["genus"]
                new_row[f"spp{idx}_species"] = spp_item["species"]
                new_row[f"spp{idx}_variety"] = spp_item["variety"] or ""
                new_row[f"spp{idx}_percent"] = spp_item["percent"]
            else:
                new_row[f"spp{idx}_genus"] = ""
                new_row[f"spp{idx}_species"] = ""
                new_row[f"spp{idx}_variety"] = ""
                new_row[f"spp{idx}_percent"] = ""

        output_rows.append(new_row)

    out_fields = list(fieldnames)
    added_fields = ["nfi_summary", "leading_spp", "nfi_json"]
    for idx in range(1, max_species_columns + 1):
        added_fields.extend(
            [
                f"spp{idx}_genus",
                f"spp{idx}_species",
                f"spp{idx}_variety",
                f"spp{idx}_percent",
            ]
        )
    for field in added_fields:
        if field not in out_fields:
            out_fields.append(field)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open(mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(output_rows)

    logger.info("Successfully wrote %d rows to %s", len(output_rows), output_path)
    return output_rows


# =====================================================================
# End-to-End Pipeline
# =====================================================================


def process_raster_and_attribute_table(
    input_raster_path: PathLike,
    input_attr_table_path: PathLike,
    output_raster_path: PathLike,
    output_attr_table_path: PathLike,
    spp_column_name: Optional[str] = None,
    value_column_name: str = "Value",
    strict_sum: bool = False,
) -> None:
    """Execute end-to-end raster and attribute table conversion.

    Args:
        input_raster_path: Path to the input raster file (.tif).
        input_attr_table_path: Path to the input attribute table (.csv).
        output_raster_path: Path where the output raster will be created.
        output_attr_table_path: Path where the output attribute table will be saved.
        spp_column_name: Column containing species strings (auto-detected if None).
        value_column_name: Raster pixel value column name (default 'Value').
        strict_sum: Enforce that species percentages must sum to 100%.

    Raises:
        FileNotFoundError: If input raster or attribute table is missing.
    """
    in_raster = Path(input_raster_path).resolve()
    in_attr = Path(input_attr_table_path).resolve()
    out_raster = Path(output_raster_path).resolve()
    out_attr = Path(output_attr_table_path).resolve()

    if not in_raster.is_file():
        raise FileNotFoundError(f"Input raster not found: {in_raster}")
    if not in_attr.is_file():
        raise FileNotFoundError(f"Input attribute table not found: {in_attr}")

    logger.info("Converting attribute table: %s", in_attr)
    convert_fri_attribute_table(
        input_csv_path=in_attr,
        output_csv_path=out_attr,
        spp_column_name=spp_column_name,
        value_column_name=value_column_name,
        strict_sum=strict_sum,
    )

    logger.info("Writing output raster: %s", out_raster)
    out_raster.parent.mkdir(parents=True, exist_ok=True)

    if HAS_RASTERIO and rasterio is not None:
        with rasterio.open(in_raster) as src:
            meta = src.meta.copy()
            meta.update(compress="lzw")
            with rasterio.open(out_raster, "w", **meta) as dst:
                for band_idx in range(1, src.count + 1):
                    dst.write(src.read(band_idx), band_idx)
    else:
        shutil.copy2(in_raster, out_raster)

    logger.info("Pipeline complete. Output raster: %s", out_raster)


# =====================================================================
# CLI Entry Point
# =====================================================================


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="fri_nfi_converter",
        description="Convert raster FRI species composition attribute tables to NFI standard.",
    )
    parser.add_argument("raster_in", type=Path, help="Input FRI raster (.tif)")
    parser.add_argument("attr_in", type=Path, help="Input FRI attribute table (.csv)")
    parser.add_argument(
        "-o",
        "--raster_out",
        type=Path,
        required=True,
        help="Output raster file path (.tif)",
    )
    parser.add_argument(
        "-a",
        "--attr_out",
        type=Path,
        required=True,
        help="Output converted attribute table path (.csv)",
    )
    parser.add_argument(
        "--spp_col",
        default=None,
        help="Column containing FRI species strings (e.g. 'OSPCOMP')",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if species percentages do not sum to 100%%",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI main function."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        process_raster_and_attribute_table(
            input_raster_path=args.raster_in,
            input_attr_table_path=args.attr_in,
            output_raster_path=args.raster_out,
            output_attr_table_path=args.attr_out,
            spp_column_name=args.spp_col,
            strict_sum=args.strict,
        )
        return 0
    except (SpeciesConversionError, OSError, ValueError) as exc:
        logger.error("Execution failed: %s", exc, exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
