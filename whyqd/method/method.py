"""
.. module:: method
   :synopsis: Create and manage a wrangling method based on a predefined schema.

.. moduleauthor:: Gavin Chait <github.com/turukawa>

Method
======

`Whyqd <https://whyqd.com>`_ supports trust in research by ensuring complete and unambiquous probity in the curation of
all source data.

**Data probity** refers to the following criteria:

* Identifiable input source data,
* Transparent methods for restructuring of that source data into the data used to support research analysis,
* Accessible restructured data used to support research conclusions,
* A repeatable, auditable curation process which produces the same data.

Researchers may disagree on conclusions derived from analytical results. What they should not have cause for
disagreement on is the probity of the underlying data used to produce those analytical results.

Once you have created your :doc:`schema` it can be imported and used to develop a wrangling `method`, a
complete, structured JSON file which describes all aspects of the wrangling process. There is no
'magic'. Only what is defined in the method will be executed during transformation.

A method file can be shared, along with your input data, and anyone can then import `whyqd` and
:doc:`validate` your method to verify that your output data is the product of these inputs.

There are two worked tutorials to demonstrate how you can use `whyqd` to support source data curation transparency.

* :doc:`Local-government data <tutorial_local_government_data>`
* :doc:`Data produced by Cthulhu <tutorial_cthulhu_data>`

The first step in the process is simply to declare a method, and assign a `schema` which it must conform to::

    >>> import whyqd
    >>> SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
    >>> method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
    >>> method_details = {
        "name": "urban_population_method",
        "title": "Urban population method",
        "description": "Methods converting World Bank Urban Population source data into our analytical input data.",
    }
    >>> method.set(method_details)

Where:

 * `DIRECTORY` is your working directory to create your method and manage data files,
 * `SCHEMA_SOURCE` is the path to the `schema.json` file,

Greater detail can be found in the complete API reference. What follows are the high-level steps required to develop
your `method`.

Import source data
------------------

Assuming you have a list of input source data you wish to restructure::

    >>> INPUT_DATA = [
        SOURCE_DIRECTORY + "raw_E06000044_014_0.XLSX",
        SOURCE_DIRECTORY + "raw_E06000044_014_1.XLSX",
        SOURCE_DIRECTORY + "raw_E06000044_014_2.XLSX",
    ]

Data must conform to the `DataSourceModel`, which requires a minimum of a `path` field declaration::

    >>> input_data = [{"path": d} for d in INPUT_DATA]
    >>> method.add_data(source=input_data)

These data will be imported to your working `DIRECTORY` and a unique `checksum` assigned to each data. The checksum is
a hash based on `BLAKE2b <https://en.wikipedia.org/wiki/BLAKE_(hash_function)>`_. These input data are never changed
during the restructuring process, and the hash is based on the entire file. If anyone opens these files and resaves
them - even if they make no further changes - metadata and file structure will change, and a later hash generated on
the changed file will be different from the original.

You now have two options:

* **Merge**: since you have multiple data sources, you can merge these into one so that you only need to develop one**
  set of restructuring actions,
* **Add actions**: or you can add individual actions, and then merge.

.. warning:: **Whyqd** ensures **unambiguous** data curation. There are no "stranded" assets in a `method`. If you
    import an Excel spreadsheet which happens to have multiple sheets, each of these sheets as added as a separate
    `input_data` reference. It is up to you to delete input data you have no intention of using.

Merge
-----
`merge` will join, in order from right to left, your input data on a `key` column. Merging will generate a `working_data`
reference.

.. note:: If you only have one input source file, you don't need to merge. However, if you have multiple sources, then
    a merge is **mandatory** or your build will fail.

During import, each data source was assigned a unique reference
`UUID <https://en.wikipedia.org/wiki/Universally_unique_identifier>`>_. If a single Excel source file had multiple
sheets, then uniquely-identifying each is a combination of the `UUID` and its `sheet_name`.

To merge, you create a special MERGE `action`::

    "MERGE < ['key_column'::'source_hex'::'sheet_name', etc.]"

Where, for each input data source:

 * `key_column` is the data column used to uniquely link each row of each data source,
 * `source_hex` is unique reference UUID for each data source,
 * `sheet_name` is sheet name within a multi-sheet Excel source file, if such exist (otherwise `None`).

You should know your own source data, and you can get the references as follows::

    >>> merge_reference = [
            {"source_hex": method.get.input_data[2].uuid.hex, "key_column": "Property ref no"},
            {"source_hex": method.get.input_data[1].uuid.hex, "key_column": "Property Reference Number"},
            {"source_hex": method.get.input_data[0].uuid.hex, "key_column": "Property Reference Number"},
        ]

In this example, there is no `sheet_name`. Generate and add your merge script as follows::

    >>> merge_terms = ", ".join([f"'{m['key_column']}'::'{m['source_hex']}'" for m in merge_reference])
    >>> merge_script = f"MERGE < [{merge_terms}]"
    >>> method.merge(merge_script)

`whyqd` will automatically process the merge, validate the merge works, and assign a UUID to the `working_data`.

Whether you needed to `merge` or not, you're now ready to assign restructuring actions.

Restructure with Actions
------------------------
:doc:`action_api` are the core of the wrangling process and is the step where you define individual steps which must be
performed to restructure your data.

There are two main types of restructuring actions:

* **Schema-based** where the result of the action is to restructure source data columns into schema columns,
* **Morph-based** where you physically, and destructively, manipulate your source data to make it useable.

Morphs include actions like deletion, or rebasing the header row. These will lose information from your source. These
two actions have a slightly different structure, but the process by which you add them to your method is the same.

Schema-based actions
^^^^^^^^^^^^^^^^^^^^
A template schema-based script::

    "ACTION > 'destination_column' < [modifier 'source_column', {action_script}]"

Where, for each input data source:

 * `destination_column` is the schema field, or existing column, you wish to direct the results of your action,
 * `source_column` is the existing column you wish to restructure,
 * `modifier` are special characters, defined by the ACTION, which modify the way the values in the `source_colum`
   are interpreted.
 * `{action_script}` is a nested action.

Schema-based actions can be nested. You can embed other schema-based actions inside them. In the case of `CALCULATE`,
this may be necessary if you need to change the sign of a column of negative values::

    "CALCULATE > 'destination_field' < [modifier 'source_column', modifier CALCULATE < [- 'source_column']"

Morph-based actions
^^^^^^^^^^^^^^^^^^^
A template morph-based script::

    "ACTION > [columns] < [rows]"

Where:

 * `rows` are the specific rows effected by the morph, a `list` of `int`,
 * `columns` are the specific columns effected by the morph, a `list` of `source_column`.

Morph-based actions are not permitted to be nested, i.e. they are stand-alone actions.

.. note:: It is assumed that you're not working 'blind', that you're actually looking at your data while assigning
    actions - *especially* row-level actions - otherwise you are going to get extremely erratic results. **Whyqd** is
    built on `Pandas <https://pandas.pydata.org/>`_ and these examples lean heavily on that package.

Reviw :doc:`action_api` for each action's documentation in the API to know how to work with them.

Assigning actions
^^^^^^^^^^^^^^^^^
Once you have reviewed your data, and worked through the script you need to produce, they can be assigned::

    >>> schema_scripts = [
            "DEBLANK",
            "DEDUPE",
            "REBASE < [2]",
        ]
    >>> source_data = method.get.input_data[0]
    >>> method.add_actions(schema_scripts, source_data.uuid.hex, sheet_name = "Data")

Note, though, that `"REBASE < [2]"` changed the header-row column labels. Any further actions need to reference these
names or the action will fail. You can review your progress at any point by running the transform and getting a
`Pandas DataFrame <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html>`_::

    >>> df = method.transform(source_data)

+----+----------------+----------------+------------------+------------------+----------+----------+----------+----------+----------+----------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+----------+
|    | Country Name   | Country Code   | Indicator Name   | Indicator Code   |   1960.0 |   1961.0 |   1962.0 |   1963.0 |   1964.0 |   1965.0 |           1966.0 |           1967.0 |           1968.0 |           1969.0 |           1970.0 |           1971.0 |           1972.0 |           1973.0 |           1974.0 |           1975.0 |           1976.0 |           1977.0 |           1978.0 |           1979.0 |           1980.0 |           1981.0 |           1982.0 |           1983.0 |          1984.0 |          1985.0 |          1986.0 |          1987.0 |          1988.0 |          1989.0 |          1990.0 |          1991.0 |          1992.0 |          1993.0 |          1994.0 |          1995.0 |          1996.0 |          1997.0 |          1998.0 |          1999.0 |          2000.0 |          2001.0 |          2002.0 |          2003.0 |          2004.0 |          2005.0 |          2006.0 |          2007.0 |          2008.0 |          2009.0 |          2010.0 |          2011.0 |          2012.0 |          2013.0 |          2014.0 |          2015.0 |          2016.0 |          2017.0 |          2018.0 |   2019.0 |
+====+================+================+==================+==================+==========+==========+==========+==========+==========+==========+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+==================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+=================+==========+
|  3 | Aruba          | ABW            | Urban population | SP.URB.TOTL      |    27526 |    28141 |    28532 |    28761 |    28924 |    29082 |  29253           |  29416           |  29575           |  29738           |  29900           |  30082           |  30275           |  30470           |  30605           |  30661           |  30615           |  30495           |  30353           |  30282           |  30332           |  30560           |  30943           |  31365           | 31676           | 31762           | 31560           | 31142           | 30753           | 30720           | 31273           | 32507           | 34116           | 35953           | 37719           | 39172           | 40232           | 40970           | 41488           | 41945           | 42444           | 43048           | 43670           | 44246           | 44669           | 44889           | 44882           | 44686           | 44378           | 44053           | 43778           | 43819           | 44057           | 44348           | 44665           | 44979           | 45296           | 45616           | 45948           |      nan |
+----+----------------+----------------+------------------+------------------+----------+----------+----------+----------+----------+----------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+----------+
|  4 | Afghanistan    | AFG            | Urban population | SP.URB.TOTL      |   755836 |   796272 |   839385 |   885228 |   934135 |   986074 |      1.04119e+06 |      1.09927e+06 |      1.16136e+06 |      1.22827e+06 |      1.30095e+06 |      1.37946e+06 |      1.46329e+06 |      1.55104e+06 |      1.64087e+06 |      1.73093e+06 |      1.82161e+06 |      1.91208e+06 |      1.99758e+06 |      2.07094e+06 |      2.13637e+06 |      2.18149e+06 |      2.20897e+06 |      2.22507e+06 |     2.24132e+06 |     2.2679e+06  |     2.30581e+06 |     2.35734e+06 |     2.43955e+06 |     2.50291e+06 |     2.62855e+06 |     2.82817e+06 |     3.09339e+06 |     3.39171e+06 |     3.67709e+06 |     3.91625e+06 |     4.09384e+06 |     4.22082e+06 |     4.32158e+06 |     4.43476e+06 |     4.5878e+06  |     4.79005e+06 |     5.03116e+06 |     5.29338e+06 |     5.5635e+06  |     5.82429e+06 |     6.05502e+06 |     6.26375e+06 |     6.46484e+06 |     6.68073e+06 |     6.92776e+06 |     7.21252e+06 |     7.52859e+06 |     7.86507e+06 |     8.20488e+06 |     8.53561e+06 |     8.85286e+06 |     9.16484e+06 |     9.4771e+06  |      nan |
+----+----------------+----------------+------------------+------------------+----------+----------+----------+----------+----------+----------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+----------+
|  5 | Angola         | AGO            | Urban population | SP.URB.TOTL      |   569222 |   597288 |   628381 |   660180 |   691532 |   721552 | 749534           | 776116           | 804107           | 837758           | 881022           | 944294           |      1.0282e+06  |      1.12462e+06 |      1.23071e+06 |      1.34355e+06 |      1.4626e+06  |      1.58871e+06 |      1.72346e+06 |      1.86883e+06 |      2.02677e+06 |      2.19787e+06 |      2.38256e+06 |      2.58126e+06 |     2.79453e+06 |     3.02227e+06 |     3.26559e+06 |     3.5251e+06  |     3.8011e+06  |     4.09291e+06 |     4.40096e+06 |     4.72563e+06 |     5.06788e+06 |     5.42758e+06 |     5.80661e+06 |     6.15946e+06 |     6.53015e+06 |     6.919e+06   |     7.32807e+06 |     7.75842e+06 |     8.212e+06   |     8.68876e+06 |     9.19086e+06 |     9.72127e+06 |     1.02845e+07 |     1.08828e+07 |     1.14379e+07 |     1.20256e+07 |     1.26446e+07 |     1.32911e+07 |     1.39631e+07 |     1.46603e+07 |     1.53831e+07 |     1.61303e+07 |     1.69008e+07 |     1.76915e+07 |     1.85022e+07 |     1.93329e+07 |     2.01847e+07 |      nan |
+----+----------------+----------------+------------------+------------------+----------+----------+----------+----------+----------+----------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+----------+
|  6 | Albania        | ALB            | Urban population | SP.URB.TOTL      |   493982 |   513592 |   530766 |   547928 |   565248 |   582374 | 599300           | 616687           | 635924           | 656733           | 677801           | 698647           | 720649           | 742333           | 764166           | 786668           | 809052           | 832109           | 854618           | 876974           | 902120           | 927513           | 954645           | 982645           |     1.01124e+06 |     1.04013e+06 |     1.0685e+06  |     1.09835e+06 |     1.12772e+06 |     1.16716e+06 |     1.19722e+06 |     1.19891e+06 |     1.20949e+06 |     1.21988e+06 |     1.23022e+06 |     1.2404e+06  |     1.25052e+06 |     1.26041e+06 |     1.27021e+06 |     1.27985e+06 |     1.28939e+06 |     1.29858e+06 |     1.32722e+06 |     1.35485e+06 |     1.38183e+06 |     1.4073e+06  |     1.43089e+06 |     1.4524e+06  |     1.47339e+06 |     1.49526e+06 |     1.51952e+06 |     1.54693e+06 |     1.57579e+06 |     1.6035e+06  |     1.63012e+06 |     1.6545e+06  |     1.68025e+06 |     1.70634e+06 |     1.72897e+06 |      nan |
+----+----------------+----------------+------------------+------------------+----------+----------+----------+----------+----------+----------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+-----------------+----------+

Wide format is not exactly helpful, so we'll modify this::

    >>> source_data = method.get.input_data[0]
    >>> source_columns = [c.name for c in source_data.columns]
    >>> schema_script = f"PIVOT_LONGER > {source_columns[4:]}"
    >>> method.add_actions(schema_script, source_data.uuid.hex, sheet_name = "Data")
    >>> df = method.transform(source_data)

+----+----------------+------------------+------------------+----------------+----------------------------+-----------------------------+
|    | Country Code   | Indicator Name   | Indicator Code   | Country Name   |   PIVOT_LONGER_names_idx_4 |   PIVOT_LONGER_values_idx_5 |
+====+================+==================+==================+================+============================+=============================+
|  0 | ABW            | Urban population | SP.URB.TOTL      | Aruba          |                       1960 |                       27526 |
+----+----------------+------------------+------------------+----------------+----------------------------+-----------------------------+
|  1 | AFG            | Urban population | SP.URB.TOTL      | Afghanistan    |                       1960 |                      755836 |
+----+----------------+------------------+------------------+----------------+----------------------------+-----------------------------+
|  2 | AGO            | Urban population | SP.URB.TOTL      | Angola         |                       1960 |                      569222 |
+----+----------------+------------------+------------------+----------------+----------------------------+-----------------------------+
|  3 | ALB            | Urban population | SP.URB.TOTL      | Albania        |                       1960 |                      493982 |
+----+----------------+------------------+------------------+----------------+----------------------------+-----------------------------+

It may seem daunting at first, but the actions are designed to give you all the power of `pandas` while allowing you
to focus on the complexities of restructuring your data.

Assigning categories
^^^^^^^^^^^^^^^^^^^^
One of the problems with having a schema is that not everyone will agree to use it. Your source data can have a variety
of terms - with a variety of different spellings - to refer to the same things. This can make an already-intimidating
restructuring process a hair-tearing experience.

It takes two separate sets of actions to categorise and restructure categories.

* First, identify the columns which contain values you wish to categories, and specify how to treat those values,
* Second, assign the values in each column to the schema-defined categories.

The template script to extract unique terms in columns is::

    "CATEGORISE > 'destination_field' < [modifier 'source_column', modifier 'source_column', etc.]"

Where there are two `modifier` terms:

 * `-` indicates that the presence or absence of values in the column are coerced to `boolean`, and
 * `+` indicates that specific values in the column are to be assigned to a defined `schema` `category`.

Once complete, you can get a list of the unique terms and assign them using one of the two assignment actions::

    "ASSIGN_CATEGORY_BOOLEANS > 'destination_field'::bool < 'source_column'"

or::

    "ASSIGN_CATEGORY_UNIQUES > 'destination_field'::'destination_category' < 'source_column'::['unique_source_term', 'unique_source_term', etc.]"

Where assignment terms include:

 * `destination_field` is a `FieldModel` and is the destination column. The `::` linked `CategoryModel` defines what
   term the source values are to be assigned.
 * `list` of `CategoryModel` - unique values from `ColumnModel` - will be assigned `::CategoryModel`.
 * Values from the `source_column` `ColumnModel` are treated as boolean `True` or `False`, defined by `::bool`.

The way to think about assigning a `boolean` column is that these are columns with values and nulls. The presence or
absence of values can be all you need to know, not the values themselves. For example, if you want to know who - in a
list of employees - has taken leave but all you have is a date column of *when* they took leave, an absence of a date
in that column indicates they haven't yet taken any.

Getting a list of the unique terms in a column so you can assign them goes like this::

    >>> df = method.transform(method.get.working_data)
    >>> list(df["Current Relief Type"].unique())
    [<NA>,
    'Retail Discount',
    'Small Business Relief England',
    'Supporting Small Business Relief',
    'Sbre Extension For 12 Months',
    'Empty Property Rate Industrial',
    'Empty Property Rate Non-Industrial',
    'Mandatory',
    'Sports Club (Registered CASC)',
    'Empty Property Rate Charitable']

.. note:: You can assign unique values to a `boolean` category term (e.g. 'Empty Property Rate Industrial' and
    'Empty Property Rate Non-Industrial' could be assigned to a `occupation_status` schema field, where `True` is
    occupied, and `False` is vacant). You can also assign booleans to a schema requiring unique fields. Use your
    intuiation and it'll probably work the way you expect.

Here's an example script to assign column values to a boolean schema field::

    "CATEGORISE > 'occupation_state' < [+ 'Current Property Exemption Code', + 'Current Relief Type']"
    "ASSIGN_CATEGORY_UNIQUES > 'occupation_state'::False < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']"

Adding these scripts works as above::

    >>> source_data = method.get.working_data
    >>> method.add_actions(schema_scripts, source_data.uuid.hex)

Assigning filters
^^^^^^^^^^^^^^^^^
Filtering is inherently destructive, reducing the number of rows in your source data. This can make your data more
manageable, or help ensure only the latest data since a previous release, are included in an ongoing data series.

A standard script is::

    "ACTION > 'filter_column'::'date' < 'source_column'"

Where:

 * `filter_column`: the specific column for filtering,
 * `source_column`: a group-by column for filtering the latest data only of a data series,
 * `date`: a specific date reference, in ISO `YYYY-MM-DD` format. Times are not filtered, so treat with caution if your
   filter requirements are time-based.

There are three filters: before a specified date, after a specified date, or latest for a specified group.

As example::

    >>> filter_script = "FILTER_AFTER > 'occupation_state_date'::'2010-01-01'"
    >>> method.add_actions(filter_script, source_data.uuid.hex)

Or you could do latest:

    >>> filter_script = "FILTER_LATEST > 'occupation_state_date' < 'ba_ref'"
    >>> method.add_actions(filter_script, source_data.uuid.hex)


Build
-----
Performing the build is straightforward::

    >>> method.build()
    >>> method.save(created_by="Gavin Chait")

`Build` will automatically save your restructured output data as an Excel file (to preserve source field types). You
can save your method as a `json` file by calling `save`. A `version` data update will automatically be added to the
method, and you can add an optional `created_by` reference as well.

Validation
----------
At each step of the transformation process - whether it be adding input data, merging or adding actions - `whyqd`
performs validation, both for individual steps, and for the entire build process. This validation step exists only
for the truly paranoid (as you rightly should be with input data you do not control).

    >>> method.validate()
    True

Citation
--------

**whyqd** is designed to support a research process and ensure citation of the incredible work done by research-based
data scientists.

A citation is a special set of fields, with options for:

* **author**: The name(s) of the author(s) (in the case of more than one author, separated by `and`),
* **title**: The title of the work,
* **url**: The URL field is used to store the URL of a web page or FTP download. It is a non-standard BibTeX field,
* **publisher**: The publisher's name,
* **institution**: The institution that was involved in the publishing, but not necessarily the publisher,
* **doi**: The doi field is used to store the digital object identifier (DOI) of a journal article, conference paper,
  book chapter or book. It is a non-standard BibTeX field. It's recommended to simply use the DOI, and not a DOI link,
* **month**: The month of publication (or, if unpublished, the month of creation). Use three-letter abbreviation,
* **year**: The year of publication (or, if unpublished, the year of creation),
* **note**: Miscellaneous extra information.

Those of you familiar with Dataverse's `universal numerical fingerprint <http://guides.dataverse.org/en/latest/developers/unf/index.html>`_
may be wondering where it is? **whyqd**, similarly, produces a unique hash for each datasource,
including inputs, working data, and outputs. Ours is based on `BLAKE2b <https://en.wikipedia.org/wiki/BLAKE_(hash_function)>`_
and is included in the citation output.

As an example::

    >>> citation = {
            "author": "Gavin Chait",
            "month": "feb",
            "year": 2020,
            "title": "Portsmouth City Council normalised database of commercial ratepayers",
            "url": "https://github.com/whythawk/whyqd/tree/master/tests/data"
        }
    >>> method.set_citation(citation)

You can then get your citation report::

    >>> method.get_citation()
        {'author': 'Gavin Chait',
        'title': 'Portsmouth City Council normalised database of commercial ratepayers',
        'url': AnyUrl('https://github.com/whythawk/whyqd/tree/master/tests/data', scheme='https', host='github.com', tld='com', host_type='domain', path='/whythawk/whyqd/tree/master/tests/data'),
        'month': 'feb',
        'year': 2020,
        'input_sources': [{'path': 'https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-properties-january-2020.xls',
        'checksum': 'b180bd9fe8c3b1025f433e0b3377fb9a738523b9c33eac5d62ed83c51883e1f64a3895edf0fc9e96a85a4130df3392177dff262963338971114aa4f5d1b0a70e'},
        {'path': 'https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-reliefs-january-2020.xls',
        'checksum': '98e23e4eac6782873492181d6e4f3fcf308f1bb0fc47dc582c3fdf031c020a651d9f06f6510b21405c3f63b8d576a93a27bd2f3cc5b053d8d9022c884b57d3a3'},
        {'path': 'https://www.portsmouth.gov.uk/ext/documents-external/biz-empty-commercial-properties-january-2020.xls',
        'checksum': '9fd3d0df6cc1e0e58ab481ca9d46b68150b3b8d0c97148a00417af16025ba066e29a35994d0e4526edb1deda4c10b703df8f0dbcc23421dd6c0c0fd1a4c6b01c'}],
        'restructured_data': {'path': 'https://github.com/whythawk/whyqd/tree/master/tests/data',
        'checksum': '25591827b9b5ad69780dc1eea6121b4ec79f10b62f21268368c7faa5ca473ef3f613c72fea723875669d0fe8aa57c9e7890f1df5b13f922fc525c82c1239eb42'}}
"""
from __future__ import annotations
from shutil import copyfile, SameFileError
import urllib.request
import string
from typing import Optional, Union, List, Dict, Tuple, Type
from pydantic import Json
from uuid import UUID
import pandas as pd

from ..models import (
    DataSourceModel,
    ActionScriptModel,
    MethodModel,
    CategoryActionModel,
    VersionModel,
    MorphActionModel,
    CitationModel,
)
from ..parsers import CoreScript, WranglingScript, MethodScript, ParserScript
from ..schema import Schema


class Method:
    """Create and manage a method to perform a wrangling process.

    Parameters
    ----------
    directory: str
        Working path for creating methods, interim data files and final output
    source: str
        Path to a json file containing a saved schema, default is None
    """

    def __init__(
        self,
        directory: str,
        schema: Type[Schema],
        method: Optional[MethodModel] = None,
    ) -> None:
        # Default number of rows in a DataFrame to return from summaries
        self._nrows = 50
        if not isinstance(schema, Schema):
            raise AssertionError("Schema must be a valid Schema type.")
        self._schema = schema
        if not self._schema.get.fields:
            raise ValueError(f"Schema ({self._schema}) has no defined fields.")
        self._method = None
        if method:
            self._method = MethodModel(**method)
            self._method.schema_fields = self._schema.get.fields.copy()
        # Initialise Parsers
        self.core = CoreScript()
        self.mthdprsr = MethodScript(self._schema)
        self.wrangle = WranglingScript()
        self.parser = ParserScript()
        # Set working directory
        self.directory = self.core.check_path(directory)

    def __repr__(self) -> str:
        """Returns the string representation of the model."""
        if self._method:
            return f"Method: `{self._method.name}`"
        return "Method"

    @property
    def describe(self) -> Union[Dict[str, None], None]:
        """Get the method name, title and description.

         - name: Term used for filename and referencing. Will be lower-cased and spaces replaced with `_`
         - title: Human-readable term used as name.
         - description: Detailed description for the method. Reference its objective and use-case.

        Returns
        -------
        dict or None
        """
        if self._method:
            response = {
                "name": self._method.name,
                "title": self._method.title,
                "description": self._method.description,
            }
            return response
        return None

    @property
    def get(self) -> Union[MethodModel, None]:
        """Get the method model.

        Returns
        -------
        MethodModel or None
        """
        return self._method

    def set(self, method: MethodModel) -> None:
        """Update or create the method.

        Parameters
        ----------
        method: MethodModel
            A dictionary conforming to the MethodModel.
        """
        # Create a temporary MethodModel
        updated_method = MethodModel(**method)
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        if self._method:
            self._method = self._method.copy(update=updated_method.dict(exclude_unset=True))
        else:
            self._method = updated_method
        self._method.schema_fields = self._schema.get.fields.copy()

    #########################################################################################
    # MANAGE INPUT DATA
    #########################################################################################

    def add_data(self, source: Union[str, List[str], DataSourceModel, List[DataSourceModel]], get_row_count: bool = False) -> None:
        """Provide either a path string, list of path strings, or a dictionary conforming to the DataSourceModel data
        for wrangling.

        If conforming to the DataSourceModel, each source dictionary requires the minimum of::

            {
                "path": "path/to/source/file"
            }

        An optional `citation` conforming to `CitationModel` can also be provided.

        Parameters
        ----------
        source: str, list of str, DataSourceModel, or list of DataSourceModel
            A dictionary conforming to the DataSourceModel. Each path can be to a filename, or a url.
        get_row_count: bool, default False
            Toggle whether to include row-count for tabular data in model.
        """
        if not isinstance(source, list):
            source = [source]
        for data in source:
            if isinstance(data, str):
                data = {"path": data}
            if not isinstance(data, DataSourceModel):
                data = DataSourceModel(**data)
            # Check if the filename is remote
            file_root = "/".join(data.path.split("/")[:-1])
            valid_file_source = "".join(
                c for c in data.path.split("/")[-1] if c in f"-_. {string.ascii_letters}{string.digits}"
            )
            local_source = self.directory / valid_file_source
            if self.core.check_uri(data.path):
                # File at remote URI
                urllib.request.urlretrieve(data.path, local_source)
            elif file_root:
                try:
                    # File in another directory
                    copyfile(data.path, local_source)
                except SameFileError:
                    pass
            self.core.rename_file(local_source, data.source)
            if not get_row_count:
                df_sample = self.wrangle.get_dataframe(
                    self.directory / data.source,
                    filetype=data.mime,
                    names=[d.name for d in data.names],
                    preserve=[d.name for d in data.preserve],
                    nrows=self._nrows,
                )
            else:
                df_sample = self.wrangle.get_dataframe(
                    self.directory / data.source,
                    filetype=data.mime,
                    names=[d.name for d in data.names],
                    preserve=[d.name for d in data.preserve]
                )
            if not isinstance(df_sample, dict):
                # There weren't multiple sheets in MimeType.XLS/X
                df_sample = {"key": df_sample}
            for k in df_sample.keys():
                df_columns = self.wrangle.get_dataframe_columns(df_sample[k])
                data_k = data.copy()
                if len(df_sample.keys()) > 1:
                    data_k = data.copy(deep=True, update={"sheet_name": k})
                data_k.columns = df_columns
                if get_row_count: data_k.row_count = len(df_sample[k])
                self._method.input_data.append(data_k)

    def remove_data(self, uid: UUID, sheet_name: Optional[str] = None) -> None:
        """Remove an input data source defined by its source uuid4.

        .. note:: You can remove references to individual sheets of a data source if you provide `sheet_name`. If not,
            the entire data source will be removed.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for an input data source. View all input data from method `input_data`.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to remove, or - by default - the entire
            data source will be removed.
        """
        if self._method.input_data:
            if sheet_name:
                self._method.input_data = [
                    ds
                    for ds in self._method.input_data
                    if ds.uuid != UUID(uid) or (ds.uuid == UUID(uid) and ds.sheet_name != sheet_name)
                ]
            else:
                self._method.input_data = [ds for ds in self._method.input_data if ds.uuid != UUID(uid)]

    def update_data(self, source: DataSourceModel, uid: UUID, sheet_name: Optional[str] = None) -> None:
        """Update an existing data source.

        Can be used to modify which columns are to be preserved, or other specific changes.

        .. warning:: You can only modify the following definitions: `names`, `preserve`, `citation`. Attempting to
            change any other definitions will raise an exception. Remove the source data instead.

        Parameters
        ----------
        source: DataSourceModel
            A dictionary conforming to the DataSourceModel. Each path can be to a filename, or a url.
        uid: UUID
            Unique uuid4 for an input data source. View all input data from method `input_data`.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.

        Raises
        ------
        ValueError if a sheet_name exists without a sheet_name being provided.
        """
        # Create a temporary DataSourceModel to ensure validation
        updated_source = DataSourceModel(**source)
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        if self._method.input_data:
            ds = self.mthdprsr.get_input_data(self._method.input_data, uid, sheet_name)
            # And update the modified definitions ... exclude unset to ensure only updates included
            keys = list(updated_source.dict(exclude_unset=True).keys())
            if "names" in keys:
                ds.names = updated_source.names
            if "preserve" in keys:
                ds.preserve = updated_source.preserve
            if "key" in keys:
                ds.key = updated_source.key
            if "citation" in keys and ds.citation:
                ds.citation = ds.citation.copy(update=updated_source.citation.dict(exclude_unset=True))
            elif "citation" in keys and not ds.citation:
                ds.citation = updated_source.citation

    def reorder_data(self, order: List[Union[UUID, Tuple[UUID, str]]]) -> None:
        """Reorder a list of source data prior to merging them.

        Parameters
        ----------
        order: list of UUID or tuples of UUID, str
            Either a list of UUIDs, or tuples of hexed UUIDs and sheet_names, e.g. ('uuid.hex', 'sheet_name')

        Raises
        ------
        ValueError if the list of uuid4s doesn't conform to that in the list of source data.
        """
        if self._method.input_data:
            self._method.input_data = self.mthdprsr.reorder_models(self._method.input_data, order)

    #########################################################################################
    # APPLY ACTIONS TO INPUT AND INTERIM SOURCE DATA
    #########################################################################################

    def add_actions(self, actions: Union[str, List[str]], uid: UUID, sheet_name: Optional[str] = None) -> None:
        """Add an action script to a data source specified by its uid and optional sheet name.

        .. warning:: Morph-type ACTIONS (such as 'REBASE', 'PIVOT_LONGER', and 'PIVOT_WIDER') change the header-row
            column names, and - with that - any of your subsequent referencing that relies on these names. It is
            best to run your morphs first, then your schema ACTIONS, that way you won't get any weird referencing
            errors. If column errors do arise, check your ACTION ordering.

        Parameters
        ----------
        actions: str or list of str
            An action script.
        uid: UUID
            Unique uuid4 for a either an input or interim data source.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.
        """
        if not isinstance(actions, list):
            actions = [actions]
        pre_df = pd.DataFrame()
        for a in actions:
            a = ActionScriptModel(**{"script": a})
            source_data = self.mthdprsr.get_source_data(self._method, uid=uid, sheet_name=sheet_name)
            params = self.mthdprsr.parse_action_script(source_data, a)
            source_data.actions.append(a)
            if isinstance(params["action"], MorphActionModel):
                # Ensure source_data.columns reflects the last action table state
                if pre_df.empty:
                    # Need to run the entire transform to check what the state of the table will be at this point
                    pre_df = self.transform(source_data)
                else:
                    pre_df = self.mthdprsr.transform_df_from_source(pre_df, source_data, **params)
                    # And update the columns
                    source_data.columns = self.wrangle.get_dataframe_columns(pre_df)

    def remove_action(self, uid: UUID, action_uid: UUID, sheet_name: Optional[str] = None) -> None:
        """Remove an action from a data source defined by its source uuid4. Raises an exception of sheet_name
        applies to that data source.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for a either an input or interim data source.
        action_uid: UUID
            Unique uuid4 for an action.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.

        Raises
        ------
        ValueError if a sheet_name exists without a sheet_name being provided.
        """
        source_data = self.mthdprsr.get_source_data(self._method, uid=uid, sheet_name=sheet_name)
        source_data = self.mthdprsr.remove_action(source_data.actions, action_uid)
        self._rebuild_actions(source_data)

    def update_action(self, uid: UUID, action_uid: UUID, action: str, sheet_name: Optional[str] = None) -> None:
        """Update an action from a list of actions.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for a either an input or interim data source.
        action_uid: UUID
            Unique uuid4 for an action.
        action: str
            An updated action script.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.
        """
        new_action = ActionScriptModel(**{"script": action})
        source_data = self.mthdprsr.get_source_data(self._method, uid=uid, sheet_name=sheet_name)
        # Check that it parses
        self.mthdprsr.parse_action_script(source_data, new_action)
        source_data = self.mthdprsr.update_actions(source_data.actions, action_uid, new_action)
        self._rebuild_actions(source_data)

    def reorder_actions(self, uid: UUID, order: List[UUID], sheet_name: Optional[str] = None) -> None:
        """Reorder a list of actions.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for a either an input or interim data source.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.
        order: list of UUID
            List of uuid4 action strings.

        Raises
        ------
        ValueError if the list of uuid4s doesn't conform to that in the list of actions.
        """
        source_data = self.mthdprsr.get_source_data(self._method, uid=uid, sheet_name=sheet_name)
        source_data = self.mthdprsr.reorder_models(source_data.actions, order)
        self._rebuild_actions(source_data)

    #########################################################################################
    # MERGE INPUT AND GENERATE INTERIM DATA
    #########################################################################################

    def merge(self, script: str) -> None:
        """Merge input data to generate any required interim data. Will perform all actions on each interim data source.

        .. note:: Merging, or an interim data source, are not required to produce a schema-defined destination data
            output.

        .. warning:: There is only so much hand-holding possible:
            * If an interim data source already exists, and has existing actions, this function will reset the
            action list, placing this `script` first.
            * If further actions are added to input data, this function must be run again.
            * The first two points are, obviously, detrimental to each other.
            * And then there are 'filters' which are intrinsically destructive.

        Merge script is of the form::

            "MERGE < ['key_column'::'source_hex'::'sheet_name', etc.]"

        Where the source terms are in order for merging.

        Parameters
        ----------
        script: str
            Merge script, as defined.
        """
        # Get or create the working_file path
        if self._method.working_data:
            working_path = self._method.working_data.path
        else:
            working_file = (
                f"working_{'_'.join([m.lower() for m in self._method.name.split()])}_{self._method.uuid.hex}.xlsx"
            )
            working_path = self.directory / working_file
        actions = [ActionScriptModel(**{"script": script})]
        merge_list = self.mthdprsr.parse_merge(actions[0], self._method.input_data)
        # Perform the merge
        df = self._merge_dataframes(merge_list)
        # Establish the WORKING DATA term in method
        df.to_excel(working_path, index=False)
        working_data = DataSourceModel(**{"path": str(working_path)})
        working_data.columns = self.wrangle.get_dataframe_columns(df)
        working_data.preserve = [c for c in working_data.columns if c.type_field == "string"]
        working_data.actions = actions
        working_data.row_count = len(df)
        # Load file again to calculate checksum
        df = self.wrangle.get_dataframe_from_datasource(working_data)
        working_data.checksum = self.core.get_data_checksum(df)
        self._method.working_data = working_data
        # Update the method with this change-event
        update = VersionModel(**{"description": "Build merged data."})
        self._method.version.append(update)

    #########################################################################################
    # IMPLEMENT TRANSFORMATIONS
    #########################################################################################

    def transform(self, data: DataSourceModel) -> pd.DataFrame:
        """Returns a transformed DataFrame after performing assigned action scripts, in order, to transform
        a data source.

        Parameters
        ----------
        data: DataSourceModel

        Returns
        -------
        Pandas DataFrame
        """
        # 1. Check that there are transformations to perform
        if not data.actions:
            raise ValueError("There are no transformation actions to perform.")
        data_actions = data.actions.copy()
        # Check if the first action is a MERGE
        if self.parser.get_anchor_action(data_actions[0].script).name == "MERGE":
            if not len(data.actions) > 1:
                raise ValueError("Merge is complete, but there are no further transformation actions to perform.")
            data_actions = data.actions[1:].copy()
        # 2. Morph ACTIONS change reference columns ... this causes the chaos you would expect ...
        # Reset column references BEFORE starting transform so that scripts run properly
        df = self.wrangle.get_dataframe_from_datasource(data)
        data.columns = self.wrangle.get_dataframe_columns(df)
        # 1. Parse all category assignment scripts
        category_assignments = []
        for script in data.actions:
            first_action = self.parser.get_anchor_action(script.script)
            if isinstance(first_action, CategoryActionModel) and first_action.name in [
                "ASSIGN_CATEGORY_UNIQUES",
                "ASSIGN_CATEGORY_BOOLEANS",
            ]:
                category_assignments.append(self.mthdprsr.parse_action_script(data, script))
        parsed = []
        # 3. Associate category ASSIGNMENTS to CATEGORISE & process MORPHS without trashing things
        for script in data_actions:
            first_action = self.parser.get_anchor_action(script.script)
            if isinstance(first_action, CategoryActionModel):
                continue
            p = self.mthdprsr.parse_action_script(data, script)
            if isinstance(p["action"], MorphActionModel):
                # Do a pre-transform up to this point to get the current column state ... only way without
                # massive refactoring ... will try come up with a more efficient way...
                # Currently, this is an abomination unto ... everything.
                pre_df = df.copy()
                pre_parsed = parsed.copy()
                pre_parsed.append(p)
                data.columns = self.wrangle.get_dataframe_columns(pre_df)
                for params in pre_parsed:
                    pre_df = self.mthdprsr.transform_df_from_source(pre_df, data, **params)
                    data.columns = self.wrangle.get_dataframe_columns(pre_df)
            elif p["action"].name == "CATEGORISE":
                p["assigned"] = []
                for a in category_assignments:
                    if a["destination"].name == p["destination"].name:
                        p["assigned"].append(a)
            parsed.append(p)
        # 4. Perform the transformations on the DataFrame
        #    These can be a mix of Schema and Morph Actions
        data.columns = self.wrangle.get_dataframe_columns(df)
        for params in parsed:
            df = self.mthdprsr.transform_df_from_source(df, data, **params)
            # And update the columns
            data.columns = self.wrangle.get_dataframe_columns(df)
        return df

    #########################################################################################
    # BUILD THE OUTPUT DATA ACCORDING TO THE SCHEMA
    #########################################################################################

    def build(self) -> None:
        """Merge input data to generate any required interim data. Will perform all actions on each interim data source.

        .. note:: Merging, or an interim data source, are not required to produce a schema-defined destination data
            output.

        .. warning:: There is only so much hand-holding possible:
            * If an interim data source already exists, and has existing actions, this function will reset the
            action list, placing this `script` first.
            * If further actions are added to input data, this function must be run again.
            * The first two points are, obviously, detrimental to each other.
            * And then there are 'filters' which are intrinsically destructive.
        """
        # Validate and restructure source data
        df_restructured = self._restructure_dataframes()
        # Establish the RESTRUCTURED DATA term in method
        # Get or create the restructured_file path
        if self._method.restructured_data:
            restructured_path = self._method.restructured_data.path
        else:
            restructured_file = (
                f"restructured_{'_'.join([m.lower() for m in self._method.name.split()])}_{self._method.uuid.hex}.xlsx"
            )
            restructured_path = self.directory / restructured_file
        # Try for a Schema order
        header_order = [c.name for c in self._schema.get.fields if c.name in df_restructured.columns]
        try:
            df_restructured[header_order].to_excel(restructured_path, index=False)
        except ValueError:
            # Excel is limited to a particular row length, if exceeded, it has to be CSV, unfortunately
            restructured_path = f"{str(restructured_path)[:-5]}.csv"
            df_restructured[header_order].to_csv(restructured_path, index=False)
        restructured_data = DataSourceModel(**{"path": str(restructured_path)})
        restructured_data.columns = self.wrangle.get_dataframe_columns(df_restructured[header_order])
        restructured_data.preserve = [c for c in restructured_data.columns if c.type_field == "string"]
        # Load file again to calculate checksum
        df_restructured = self.wrangle.get_dataframe_from_datasource(restructured_data)
        restructured_data.checksum = self.core.get_data_checksum(df_restructured[header_order])
        self._method.restructured_data = restructured_data
        # Update the method with this change-event
        update = VersionModel(**{"description": "Build restructured data."})
        self._method.version.append(update)

    #########################################################################################
    # VALIDATE BUILD
    #########################################################################################

    def validate(self) -> bool:
        """Validate the build process and all data checksums. Will perform all actions on each interim data source.

        Raises
        ------
        ValueError if any steps fail to validate.

        Returns
        -------
        bool
        """
        if not isinstance(self._method.restructured_data, DataSourceModel):
            raise ValueError("Method build restructuring is not complete.")
        # Validate and restructure source data
        df_restructured = self._restructure_dataframes()
        # Create and save a temporary working file
        temporary_file = f"temporary_{self._method.uuid.hex}.xlsx"
        temporary_path = self.directory / temporary_file
        # Force the same header order
        header_order = [c.name for c in self._schema.get.fields if c.name in df_restructured.columns]
        df_restructured[header_order].to_excel(temporary_path, index=False)
        temporary_data = DataSourceModel(**{"path": str(temporary_path)})
        temporary_data.columns = self.wrangle.get_dataframe_columns(df_restructured)
        temporary_data.preserve = [c for c in temporary_data.columns if c.type_field == "string"]
        # Load file again to calculate checksum
        df_restructured = self.wrangle.get_dataframe_from_datasource(temporary_data)
        # Validate RESTRUCTURED DATA checksums
        df_checksum = self.core.get_data_checksum(df_restructured)
        # Delete the temporary file. Before crashing.
        self.core.delete_file(temporary_path)
        if self._method.restructured_data.checksum != df_checksum:
            raise ValueError(
                f"Method build of restructured source data does not validate. (provided:{df_checksum} != method:{self._method.restructured_data.checksum})"
            )
        return True

    #########################################################################################
    # MANAGE CITATION
    #########################################################################################

    def get_citation(self) -> Dict[str, Union[str, Dict[str, str]]]:
        """Get the citation as a dictionary.

        Raises
        ------
        ValueError if no citation has been declared or the build is incomplete.

        Returns
        -------
        dict
        """
        if not self._method.citation:
            raise ValueError("No citation has been declared yet.")
        if not isinstance(self._method.restructured_data, DataSourceModel):
            raise ValueError("Method build restructuring is not complete.")
        citation = self._method.citation.dict(by_alias=True, exclude_defaults=True, exclude_none=True)
        input_sources = []
        for input_data in self._method.input_data:
            input_sources.append({"path": input_data.path, "checksum": input_data.checksum})
        citation["input_sources"] = input_sources
        citation["restructured_data"] = {
            "path": self._method.restructured_data.path,
            "checksum": self._method.restructured_data.checksum,
        }
        return citation

    def set_citation(self, citation: CitationModel) -> None:
        """Update or create the citation.

        Parameters
        ----------
        citation: CitationModel
            A dictionary conforming to the CitationModel.
        """
        # Create a temporary CitationModel
        updated_citation = CitationModel(**citation)
        if self._method.citation:
            self._method.citation = self._method.citation.copy(update=updated_citation.dict(exclude_unset=True))
        else:
            self._method.citation = updated_citation

    #########################################################################################
    # SAVE UTILITIES
    #########################################################################################

    def get_json(self, hide_uuid: Optional[bool] = False) -> Union[Json, None]:
        """Get the json method model.

        Parameters
        ----------
        hide_uuid: str, default False
            Hide all UUIDs in the nested JSON output.

        Returns
        -------
        Json or None
        """
        if self._method and not hide_uuid:
            return self._method.json(by_alias=True, exclude_defaults=True, exclude_none=True)
        elif self._method and hide_uuid:
            exclude_schema_fields, exclude_input_data, exclude_working_data, exclude_restructured_data = (
                None,
                None,
                None,
                None,
            )
            if self._method.schema_fields:
                exclude_schema_fields = {
                    f_idx: (
                        {
                            "uuid": ...,
                            "constraints": {
                                "category": {c_idx: {"uuid"} for c_idx in range(len(f.constraints.category))}
                            },
                        }
                        if f.constraints and f.constraints.category
                        else {"uuid"}
                    )
                    for f_idx, f in enumerate(self._method.schema_fields)
                }
            # DataSourceModel: columns, preserve, key, actions all have UUID
            if self._method.input_data:
                exclude_input_data = {
                    i_idx: (
                        {
                            "uuid": ...,
                            "columns": ({c_idx: {"uuid"} for c_idx in range(len(i.columns))} if i.columns else None),
                            "preserve": (
                                {c_idx: {"uuid"} for c_idx in range(len(i.preserve))} if i.preserve else None
                            ),
                            "key": ({"uuid"} if i.key else None),
                            "actions": ({c_idx: {"uuid"} for c_idx in range(len(i.actions))} if i.actions else None),
                        }
                    )
                    for i_idx, i in enumerate(self._method.input_data)
                }
            if self._method.working_data:
                exclude_working_data = {
                    "uuid": ...,
                    "columns": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.working_data.columns))}
                        if self._method.working_data.columns
                        else None
                    ),
                    "preserve": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.working_data.preserve))}
                        if self._method.working_data.preserve
                        else None
                    ),
                    "key": ({"uuid"} if self._method.working_data.key else None),
                    "actions": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.working_data.actions))}
                        if self._method.working_data.actions
                        else None
                    ),
                }
            if self._method.restructured_data:
                exclude_restructured_data = {
                    "uuid": ...,
                    "columns": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.restructured_data.columns))}
                        if self._method.restructured_data.columns
                        else None
                    ),
                    "preserve": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.restructured_data.preserve))}
                        if self._method.restructured_data.preserve
                        else None
                    ),
                    "key": ({"uuid"} if self._method.restructured_data.key else None),
                    "actions": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.restructured_data.actions))}
                        if self._method.restructured_data.actions
                        else None
                    ),
                }
            exclude = {
                "uuid": ...,
                "schema_fields": exclude_schema_fields,
                "input_data": exclude_input_data,
                "working_data": exclude_working_data,
                "restructured_data": exclude_restructured_data,
            }
            return self._method.json(by_alias=True, exclude_defaults=True, exclude_none=True, exclude=exclude)
        return None

    def save(
        self,
        directory: Optional[str] = None,
        filename: Optional[str] = None,
        created_by: Optional[str] = None,
        hide_uuid: Optional[bool] = False,
    ) -> bool:
        """Save schema as a json file.

        Parameters
        ----------
        directory: str
            Defaults to working directory
        filename: str
            Defaults to schema name
        created_by: string, default is None
            Declare the schema creator/updater
        hide_uuid: str, default False
            Hide all UUIDs in the nested JSON output.

        Returns
        -------
        bool True if saved
        """
        if not self._method:
            raise ValueError("Method does not exist.")
        if not directory:
            directory = self.directory
        else:
            directory = self.core.check_path(directory)
        if not filename:
            filename = self._method.name
        if filename.split(".")[-1] != "json":
            filename += ".json"
        path = directory / filename
        update = VersionModel(**{"description": "Save method."})
        if created_by:
            update.name = created_by
        self._method.version.append(update)
        # Reset all the source data columns
        for data in self._method.input_data:
            df = self.wrangle.get_dataframe_from_datasource(data)
            data.columns = self.wrangle.get_dataframe_columns(df)
        if self._method.working_data:
            df = self.wrangle.get_dataframe_from_datasource(self._method.working_data)
            self._method.working_data.columns = self.wrangle.get_dataframe_columns(df)
        if self._method.restructured_data:
            df = self.wrangle.get_dataframe_from_datasource(self._method.restructured_data)
            self._method.restructured_data.columns = self.wrangle.get_dataframe_columns(df)
        return self.core.save_file(self.get_json(hide_uuid=hide_uuid), path)

    #########################################################################################
    # OTHER UTILITIES
    #########################################################################################

    # def _get_dataframe(self, data: DataSourceModel) -> pd.DataFrame:
    #     """Return the dataframe for a data source. Used in transforms.

    #     Parameters
    #     ----------
    #     data: DataSourceModel

    #     Returns
    #     -------
    #     pd.DataFrame
    #     """
    #     path = data.path
    #     try:
    #         self.core.check_source(path)
    #     except FileNotFoundError:
    #         path = str(self.directory / data.source)
    #         self.core.check_source(path)
    #     df_columns = [d.name for d in data.columns]
    #     names = [d.name for d in data.names] if data.names else None
    #     df = self.wrangle.get_dataframe(
    #         path,
    #         filetype=data.mime,
    #         names=names,
    #         preserve=[d.name for d in data.preserve if d.name in df_columns],
    #     )
    #     if isinstance(df, dict):
    #         if df:
    #             df = df[data.sheet_name]
    #         else:
    #             # It's an empty df for some reason. Maybe excessive filtering.
    #             df = pd.DataFrame()
    #     if df.empty:
    #         raise ValueError(
    #             f"Data source contains no data ({data.path}). Review actions to see if any were more destructive than expected."
    #         )
    #     return df

    def _rebuild_actions(self, data: DataSourceModel) -> None:
        """Rebuild all actions for any changes to the list of actions since they can have unexpected interactions."""
        actions = [d.script for d in data.actions]
        df = self.wrangle.get_dataframe_from_datasource(data)
        data.columns = self.wrangle.get_dataframe_columns(df)
        data.actions = []
        data.actions = self.add_actions(actions, data.uuid.hex, data.sheet_name)

    def _merge_dataframes(self, merge_list: List[DataSourceModel]) -> pd.DataFrame:
        """Return a merged dataframe by transforming and merging a list of source data.

        Parameters
        ----------
        merge_list: list of DataSourceModel

        Returns
        -------
        pd.DataFrame
        """
        df_base = pd.DataFrame()
        for input_data in merge_list:
            # Perform all input data transforms and return the dataframe
            if input_data.actions:
                df = self.transform(input_data)
            else:
                df = self.wrangle.get_dataframe_from_datasource(input_data)
            if df_base.empty:
                df_base = df.copy()
                data_base = input_data.copy()
            else:
                # Rename and merge on the common key... {'from': 'too'}
                # This avoids any hassles with missing keys after the merge.
                df.rename(index=str, columns={input_data.key.name: data_base.key.name}, inplace=True)
                df_base = pd.merge(df_base, df, how="outer", on=data_base.key.name, indicator=False)
        # Deduplicate any columns after merge
        df_base.columns = self.wrangle.deduplicate_columns(df_base, self._schema)
        return df_base

    def _restructure_dataframes(self) -> pd.DataFrame:
        """Return a restructured dataframe by transforming source data.

        Raises
        ------
        ValueError if any steps fail to validate.

        Returns
        -------
        pd.DataFrame
        """
        # Check this is a valid build ...
        if not self._method.input_data:
            raise ValueError("Method build error. No input data available in this method.")
        if len(self._method.input_data) > 1 and not isinstance(self._method.working_data, DataSourceModel):
            raise ValueError(
                f"Method build is unclear where there are multiple input source data ({len(self._method.input_data)}) but they have not been merged."
            )
        if len(self._method.input_data) == 1 and not isinstance(self._method.working_data, DataSourceModel):
            df_restructured = self.transform(self._method.input_data[0])
        else:
            # Recreate the merge from the input data ...
            merge_script = self._method.working_data.actions[0]
            merge_list = self.mthdprsr.parse_merge(merge_script, self._method.input_data)
            # Perform the merge and validate the merged DataFrame's checksum
            df_working = self._merge_dataframes(merge_list)
            # Create and save a temporary working file
            temporary_file = f"temporary_{self._method.uuid.hex}.xlsx"
            temporary_path = self.directory / temporary_file
            df_working.to_excel(temporary_path, index=False)
            temporary_data = DataSourceModel(**{"path": str(temporary_path)})
            temporary_data.columns = self.wrangle.get_dataframe_columns(df_working)
            temporary_data.preserve = [c for c in temporary_data.columns if c.type_field == "string"]
            # Load file again to calculate checksum
            df_working = self.wrangle.get_dataframe_from_datasource(temporary_data)
            df_checksum = self.core.get_data_checksum(df_working)
            if self._method.working_data.checksum != df_checksum:
                raise ValueError(
                    "Method build of merged source data does not validate. Check whether you added additional source data action scripts after your last merge."
                )
            # Delete the temporary file
            self.core.delete_file(temporary_path)
            # Create the restructured dataframe.
            df_restructured = self.transform(self._method.working_data)
        # Validate against the SCHEMA
        restructured_columns = set(df_restructured.columns)
        schema_required = set([f.name for f in self._schema.get.fields if f.constraints and f.constraints.required])
        if schema_required.difference(restructured_columns):
            raise ValueError(
                f"Method build restructured table is missing required schema fields ({schema_required.difference(restructured_columns)})"
            )
        # Keep only the columns from the schema, in that order
        restructured_keep_columns = set([f.name for f in self._schema.get.fields if f.name in restructured_columns])
        return df_restructured[restructured_keep_columns]
