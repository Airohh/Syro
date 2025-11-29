"""
Configuration globale pour pytest.
"""

import pytest
import sys
from pathlib import Path

# Ajouter le répertoire racine au path Python
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Configuration pytest
pytest_plugins = []
