import sys
try:
	assert sys.version_info >= (3,7)
except AssertionError:
	from whyqd.core.action import BaseAction
else:
	from .action import BaseAction