"""Command-line execution module for fri_nfi_tool.

Allows executing the package directly via:
    python -m fri_nfi_tool <args>
"""

import sys

from .converter import main

if __name__ == "__main__":
    sys.exit(main())
