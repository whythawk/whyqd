Actions
=======

The `Action` class defines the restructuring actions performed in a :doc:`method`. `BaseAction` classes are the main
definitions for an action and are inherited by child classes in the `/action` folder.

The current list of actions are:

* **ASSIGN_CATEGORY_BOOLEANS** - Assign values in a source data column as categorical boolean terms based on whether
  values are present, or are null.
* **ASSIGN_CATEGORY_UNIQUES** - Assign unique values in a source data column as categorical unique terms defined in the
  Schema.
* **CALCULATE** - Derive a calculation from a list of fields. Each field must have a modifier, including the first
  (e.g. +A -B +C).
* **CATEGORISE** - Apply categories to a list of columns. Each field must have a modifier, including the first
  (e.g. +A -B +C). '-' modifier indicates presence/absence of values as true/false for a specific term. '+' modifier
  indicates that the unique terms in the field must be matched to the unique terms defined in the schema. This is a
  two-step process, first requiring listing the columns effected, then applying the terms.
* **DEBLANK** - Remove all blank columns and rows from a DataFrame.
* **DEDUPE** - Remove all duplicated rows from a DataFrame.
* **DELETE_COLUMNS** - Delete columns provided in a list.
* **DELETE_ROWS** - Delete rows provided in a list. They don't have to be contiguous.
* **FILTER_AFTER** - Filter a table by a date column after a specified date.
* **FILTER_BEFORE** - Filter a table by a date column prior to a specified date.
* **FILTER_LATEST** - Filter a table for the latest row in a specified filter column, and within an optional set of
  groups.
* **JOIN** - Join values in different fields to create a new concatenated value. Each value will be converted to a
  string (e.g. A: 'Word 1' B: 'Word 2' => 'Word 1 Word 2').
* **MERGE** - Merge a list of Pandas DataFrames into a single, new DataFrame, on a key column.
* **NEW** - Create a new field and assign a set value.
* **ORDER** - Use sparse data from a list of fields to populate a new field. Order is important, each successive field
  in the list have priority over the ones before it (e.g. for columns A, B & C, values in C will have precedence over
  values in B and A).
* **ORDER_NEW** - Use sparse data from a list of fields to populate a new field order by most recent value. Field-pairs
  required, with the first containing the values, and the second the dates for comparison, linked by a '+' modifier
  (e.g. A+dA, B+dB, C+dC, values with the most recent associated date will have precedence over other values).
* **ORDER_OLD** - Use sparse data from a list of fields to populate a new field order by the oldest value. Field-pairs
  required, with the first containing the values, and the second the dates for comparison, linked by a '+' modifier
  (e.g. A+dA, B+dB, C+dC, values with the oldest associated date will have precedence over other values).
* **PIVOT_CATEGORIES** - Convert row-level categories into column categorisations.
* **PIVOT_LONGER** - Transform a DataFrame from wide to long format.
* **REBASE** - Rebase the header row at an indexed row and drop rows above that point.
* **RENAME** - Rename an existing field to conform to a schema name. Only valid where a single field is provided.
* **RENAME_ALL** - Rename header columns listed in a dict.
* **RENAME_NEW** - Rename a column outside of the schema or existing column definitions. To be used with caution.
* **SPLIT** - Split the string values in a single column into any number of new columns on a specified key.

.. autoclass:: whyqd.base.action_base.BaseSchemaAction
	:member-order: bysource
	:members:

.. autoclass:: whyqd.base.morph_base.BaseMorphAction
	:member-order: bysource
	:members:

.. autoclass:: whyqd.base.category_base.BaseCategoryAction
	:member-order: bysource
	:members:

.. autoclass:: whyqd.base.filter_base.BaseFilterAction
	:member-order: bysource
	:members: