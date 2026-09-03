"""Put the skill's scripts on sys.path so the tests can import them."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "softrade-batch", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
