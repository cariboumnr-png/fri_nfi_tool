"""Demonstration script for the FRI <-> NFI converter tool.

Walks through:
1. Interactive string conversion examples (FRI -> NFI -> reconstructed FRI).
2. Processing a real-world sample raster and attribute table (VAT).
3. Inspecting the converted tabular results.

Usage:
    python demo.py
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
import pprint
import sys
from typing import Sequence

try:
    from fri_nfi_tool.converter import (
        fri_to_nfi,
        nfi_to_fri,
        process_raster_and_attribute_table,
    )
except ImportError:
    from converter import (  # type: ignore[no-redef]
        fri_to_nfi,
        nfi_to_fri,
        process_raster_and_attribute_table,
    )

logger = logging.getLogger("demo")


def run_demo() -> int:
    """Run all demonstration steps."""
    base_dir = Path(__file__).resolve().parent
    sample_dir = base_dir / "sample_data"

    input_raster = sample_dir / "sample_raster.tif"
    input_csv = sample_dir / "sample_attr_table.csv"
    output_raster = sample_dir / "output_nfi_raster.tif"
    output_csv = sample_dir / "output_nfi_attr.csv"

    print("=" * 72)
    print(" DEMO 1: String Conversion (FRI -> NFI -> Reconstructed FRI)")
    print("=" * 72)

    sample_strings: Sequence[str] = [
        "Cw  50Sb  40La  10",  # 50% Cedar, 40% Black Spruce, 10% Tamarack
        "Pt  70Bw  20Sb  10",  # 70% Trembling Aspen, 20% Birch, 10% Spruce
        "Sb 100",              # Pure Black Spruce
    ]

    for fri_str in sample_strings:
        print(f"\n[Input FRI String]: '{fri_str}'")
        nfi_list = fri_to_nfi(fri_str)
        print("[Converted NFI Records]:")
        pprint.pprint(nfi_list, indent=2)

        recon_fri = nfi_to_fri(nfi_list)
        print(f"[Reconstructed FRI String]: '{recon_fri}'")

    print("\n" + "=" * 72)
    print(" DEMO 2: Processing Raster Attribute Table")
    print("=" * 72)

    if not input_raster.is_file() or not input_csv.is_file():
        print(f"Error: Sample data files missing in {sample_dir}", file=sys.stderr)
        return 1

    print(f"Reading input raster: {input_raster}")
    print(f"Reading input VAT:    {input_csv}")

    process_raster_and_attribute_table(
        input_raster_path=input_raster,
        input_attr_table_path=input_csv,
        output_raster_path=output_raster,
        output_attr_table_path=output_csv,
        spp_column_name="OSPCOMP",
    )

    print("\n[Preview of Converted Attribute Table Output (First 5 Rows)]:\n")
    with output_csv.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx >= 5:
                break
            val = row.get("Value")
            fri_spp = row.get("OSPCOMP")
            summary = row.get("nfi_summary")
            lead = row.get("leading_spp")
            spp1 = f"{row.get('spp1_genus')} {row.get('spp1_species')} ({row.get('spp1_percent')}%)"
            spp2 = f"{row.get('spp2_genus')} {row.get('spp2_species')} ({row.get('spp2_percent')}%)"

            print(f"  Pixel Value: {val}")
            print(f"    Raw FRI (OSPCOMP): {fri_spp}")
            print(f"    NFI Summary:      {summary}")
            print(f"    Leading Species:  {lead}")
            print(f"    GIS Join Columns: spp1={spp1} | spp2={spp2}")
            print()

    print(f"Output raster saved to: {output_raster}")
    print(f"Output attribute table saved to: {output_csv}")
    print("\n" + "=" * 72)
    print(" Demo completed successfully.")
    print("=" * 72)
    return 0


def main() -> int:
    """Entry point for the demo script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    return run_demo()


if __name__ == "__main__":
    sys.exit(main())
