import io
import os

VERSION = io.open(os.path.join(os.path.dirname(__file__), "VERSION")).read().strip()
DEFAULT_FIELD_TYPE = "string"
DEFAULT_FIELD_FORMAT = "default"
DEFAULT_MISSING_VALUES = [""]