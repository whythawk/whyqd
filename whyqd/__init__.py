from pathlib import Path

from .schema import Schema
from .method import Method
from .validate import Validate

__version__ = (Path(__file__).resolve().parent / "VERSION").read_text()
