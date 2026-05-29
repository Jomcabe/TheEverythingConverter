"""GUI entry point used by PyInstaller to build the standalone app.

Kept tiny on purpose — all real logic lives in the ``everythingconverter``
package. This is just the thing the double-clickable app runs.
"""

import sys

from everythingconverter.gui import launch

if __name__ == "__main__":
    sys.exit(launch())
