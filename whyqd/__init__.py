from pathlib import Path

from whyqd.core.schema import SchemaDefinition
from whyqd.core.datasource import DataSourceDefinition
from whyqd.core.crosswalk import CrosswalkDefinition
from whyqd.core.transform import TransformDefinition

__version__ = (Path(__file__).resolve().parent / "VERSION").read_text()
