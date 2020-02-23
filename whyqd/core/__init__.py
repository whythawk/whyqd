import sys
try:
	assert sys.version_info >= (3,7)
except AssertionError:
	from whyqd.core.action import BaseAction
	from whyqd.core import common
else:
	from .action import BaseAction
	from . import common