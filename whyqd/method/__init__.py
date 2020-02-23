import sys
try:
	assert sys.version_info >= (3,7)
except AssertionError:
	from whyqd.method.method import Method
else:
	from .method import Method