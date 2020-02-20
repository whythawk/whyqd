import sys
try:
	assert sys.version_info >= (3,7)
except AssertionError:
	from whyqd.method.action import Action
	from whyqd.method.method import Method
else:
	from .action import Action
	from .method import Method