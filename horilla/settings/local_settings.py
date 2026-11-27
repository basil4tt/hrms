"""
Client-specific overrides.

Imported last from horilla.settings.__init__ (after base + addons).
Override settings here; do NOT use ``from .base import *`` — that re-exports
base MEDIA_* values and wipes AWS S3 paths set by addons.py.
"""

from datetime import timedelta

import environ

env = environ.Env()

WHITE_LABELLING = True
AXES_COOLOFF_TIME = timedelta(minutes=env.int("AXES_COOLOFF_MINUTES", default=5))

