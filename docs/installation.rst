Requirements, installation & importing
======================================

**whyqd** can be integrated into an existing data importer, or you could use it as part of your
data analysis and exploration in Jupyter Notebooks. Tables can be printed as reStructuredText or
as Pandas dataframes.

Requirements
------------

**whyqd** has a relatively short list of requirements (excl. dependencies):

	* Python 3.7+
	* Pandas 1.0+
	* Tabulate 0.8+ (for pretty-printing tables)

It could run on lower versions, but this hasn't been tested. If you want to work with Jupyter, then
either install Jupyter only, or Anaconda.

Installing
----------

Install with `pip`::

	pip install whyqd

Then import::

	import whyqd

Your next steps are to build a target :doc:`schema` to describe the data structure, and then import
that into a :doc:`method`.