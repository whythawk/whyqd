import sys
try:
	assert sys.version_info >= (3,7)
except AssertionError:
	from whyqd.method.method import Method
	from whyqd.method.morph import Morph
else:
	from .method import Method
	from .morph import Morph