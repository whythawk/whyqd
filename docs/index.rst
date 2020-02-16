.. whyqd documentation master file, created by
   sphinx-quickstart on Sat Feb 15 21:19:46 2020.

whyqd: simplicity, transparency, speed
======================================

What is it?
-----------

**whyqd** provides an intuitive and quick method for restructuring messy data to conform to a
standardised metadata schema. It supports data managers and researchers looking to rapidly, and
continuously, normalise any messy spreadsheets using a simple series of steps. Once complete, you
can import wrangled data into more complex analytical systems or full-feature wrangling tools.

It aims to get you to the point where you can perform automated data munging prior to
committing your data into a database, and no further. It is built on Pandas, and plays well with
existing Python-based data-analytical tools. Each raw source file will produce a json schema and
method file which defines the set of actions to be performed to produce refined data, and a
destination file validated against that schema.

**whyqd** ensures complete audit transparency by saving all actions performed to restructure
your input data to a separate json-defined methods file. This permits others to scrutinise your
approach, validate your methodology, or even use your methods to import data in production.

Once complete, a method file can be shared, along with your input data, and anyone can
import **whyqd** and validate your method to verify that your output data is the product of these
inputs.

How does it work?
-----------------

There is a full worked :doc:`tutorial` to help you on your way, but the core process is as follows:

  - Create, update or import a data schema which defines the destination data structure
  - Create a new method and associate it with your schema and input data source/s
  - Assign a foreign key column and (if required) merge input data sources
  - Structure input data fields to conform to the requriements for each schema field
  - Assign categorical data identified during structuring
  - Transform and filter input data to produce a final destination data file

.. toctree::
   :caption: Getting started

   installation
   tutorial

.. toctree::
   :maxdepth: 2
   :caption: Creating and managing Schemas

   schema

.. toctree::
   :maxdepth: 2
   :caption: Wrangling with Methods

   method

.. toctree::
   :caption: What next?

   roadmap
   contributing

.. toctree::
   :caption: Reference API

   field_api
   schema_api
   action_api
   method_api
