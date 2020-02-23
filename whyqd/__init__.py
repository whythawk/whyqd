import sys
from pathlib import Path
try:
	assert sys.version_info >= (3,7)
except AssertionError:
	from whyqd.core import BaseAction
	from whyqd.schema import Field, Schema
	from whyqd.method import Method
	from whyqd.action import actions, default_actions
else:
	from .core import BaseAction
	from .schema import Field, Schema
	from .method import Method
	from .action import actions, default_actions
__version__ = (Path(__file__).resolve().parent / "VERSION").read_text()