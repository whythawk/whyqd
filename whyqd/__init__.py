import sys
try:
	assert sys.version_info >= (3,7)
except AssertionError:
	from whyqd.schema import Field, Schema
	from whyqd.method import Action, Method
else:
	from .schema import Field, Schema
	from .method import Action, Method