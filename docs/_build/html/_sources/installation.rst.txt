Dependencies, installation & importing
======================================

**whyqd** can be integrated into an existing data importer, or you could use it as part of your
data analysis and exploration in Jupyter Notebooks. Tables can be printed as reStructuredText or
as Pandas dataframes.

Requirements
------------

**whyqd** has a relatively short list of requirements (excl. dependencies):

	* Python 3.8+
	* Pandas 1.0+
	* Numpy 1.2+
	* OpenPyxl 3.0+
	* XLRD 1.2+

Installing
----------

Install with `pip`::

	pip install whyqd

Then import::

	import whyqd

Your next steps are to build a target :doc:`schema` to describe the data structure, and then import
that into a :doc:`method`.