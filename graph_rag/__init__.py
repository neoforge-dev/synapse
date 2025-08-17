"""
Synapse - A Graph-based Retrieval Augmented Generation implementation.
"""

import sys
from pathlib import Path

# Add pymgclient to Python path if it exists locally
pymgclient_path = Path(__file__).parent.parent / "pymgclient"
if pymgclient_path.exists() and str(pymgclient_path) not in sys.path:
    sys.path.insert(0, str(pymgclient_path))

__version__ = "0.1.0"
