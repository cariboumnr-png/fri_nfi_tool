"""
FRI <-> NFI species composition conversion package.

Provides standalone functions to translate between Ontario Forest Resource
Inventory (FRI) species composition strings and Canada National Forest
Inventory (NFI) taxonomic records, with raster Value Attribute Table (VAT)
processing tools.
"""

from .converter import (
    FRI_TO_NFI_CODES,
    NFI_TO_FRI_CODES,
    InvalidCompositionFormatError,
    NfiSpeciesEntry,
    NfiSpeciesTuple,
    SpeciesConversionError,
    UnknownSpeciesCodeError,
    convert_fri_attribute_table,
    fri_to_nfi,
    nfi_to_fri,
    parse_fri_spp_string,
    process_raster_and_attribute_table,
)

__version__ = "1.0.0"

__all__ = [
    "FRI_TO_NFI_CODES",
    "NFI_TO_FRI_CODES",
    "InvalidCompositionFormatError",
    "NfiSpeciesEntry",
    "NfiSpeciesTuple",
    "SpeciesConversionError",
    "UnknownSpeciesCodeError",
    "convert_fri_attribute_table",
    "fri_to_nfi",
    "nfi_to_fri",
    "parse_fri_spp_string",
    "process_raster_and_attribute_table",
]
