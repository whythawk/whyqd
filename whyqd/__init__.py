from pathlib import Path

from whyqd.metamodel.schema import Schema
from whyqd.metamodel.method import Method
from whyqd.transform.validate import Validate

__version__ = (Path(__file__).resolve().parent / "VERSION").read_text()
