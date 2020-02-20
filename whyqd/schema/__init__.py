import sys
try:
	assert sys.version_info >= (3,7)
except AssertionError:
	from whyqd.schema.field import Field
	from whyqd.schema.schema import Schema
else:
	from .field import Field
	from .schema import Schema