Tutorial: Cthulhu data
======================

For years I've taught an introductory `Data wrangling & validation <https://github.com/whythawk/data-wrangling-and-validation>`_ 
course using the same training data-series: the Human Development Index report of 2007 - 2008 
released by the UNDP as part of the Millennial Development Goals.

.. note:: In 1990 the first `Human Development Report <http://www.hdr.undp.org/>`_ introduced a new 
    approach for advancing human wellbeing. Human development – or the human development approach - is 
    about expanding the richness of human life, rather than simply the richness of the economy in which 
    human beings live. It is an approach that is focused on people and their opportunities and choices.

These days it's a slick affair with beautifully-prepared open data in a standardised format. Back then open data ways
in its infancy, and these data were a constantly-changing mess of non-standard Excel spreadsheets.

H.P. Lovecraft, that old scifi-writing bigot, described Cthulhu as:

    *"A monster of vaguely anthropoid outline, but with an octopus-like head whose face was a mass of feelers, a scaly, 
    rubbery-looking body, prodigious claws on hind and fore feet, and long, narrow wings behind."*

Seems like a good description for this:

.. figure:: images/undp-hdi-2007-8.jpg
    :alt: UNDP Human Development Index 2007-2008

    UNDP Human Development Index 2007-2008: a beautiful example of messy data.

The longer you spend with it, the worse it gets. Teaching open data managers in countries around the world the 
importance of open standards and well-structured machine-readable data is brought home when seeing this and experiencing
how difficult it is to work with.

I never really expected to fix this sort of thing programmatically. However, with a little creativity,
it turns out you can.

Creating a Schema
-----------------
The 2007-8 HDI report was listed as a series of about 50 spreadsheets, each dataset aligned with the 
objectives of the `Millennium Development Goals <https://www.un.org/millenniumgoals/>`_. These supporting
information were used to track countries meeting the MDG targets. Analysis required rebuilding these 
spreadsheets into a single database aligned to a common schema.

This tutorial assumes you are familiar with the concepts used in **whyqd**::

    >>> import whyqd
    >>> schema = whyqd.Schema()
    >>> details = {
            "name": "human-development-report",
            "title": "UN Human Development Report 2007 - 2008",
            "description": """
            In 1990 the first Human Development Report introduced a new approach for 
            advancing human wellbeing. Human development – or the human development approach - is about 
            expanding the richness of human life, rather than simply the richness of the economy in which 
            human beings live. It is an approach that is focused on people and their opportunities and choices."""
        }
    >>> schema.set(details)

Let's define the fields in our schema and then iterate over the list to add each field::

    >>> fields = [
            {
                "name": "year",
                "title": "Year",
                "type": "year",
                "description": "Year of release.",
            },
            {
                "name": "country_name",
                "title": "Country Name",
                "type": "string",
                "description": "Official country names.",
                "constraints": {"required": True},
            },
            {
                "name": "indicator_name",
                "title": "Indicator Name",
                "type": "string",
                "description": "Indicator described in the data series.",
            },
            {
                "name": "values",
                "title": "Values",
                "type": "number",
                "description": "Value for the Year and Indicator Name.",
                "constraints": {"required": True},
            },
            {
                "name": "reference",
                "title": "Reference",
                "type": "string",
                "description": "Reference to data source.",
            },
        ]
    >>> for field in fields:
    ...     schema.add_field(field)
    >>> schema.save(DIRECTORY)

So far, so straightforward. Now to the wrangling.

Morphing with Methods
---------------------
Any data series consists of numerical values (usually) described by standardised metadata terms 
(time, area, a specific description, etc). There are two main ways of presenting these machine-readable 
data, which can be summarised as wide or long. You need to make a deliberate choice as to which format 
you will choose, and each has its own particular strengths and weaknesses:

**Wide data** present numerical data in multiple columns. Either as categories (e.g. each country is 
presented in its own column) or by date (e.g. each annual update results in a new column). New data 
go across the screen from left to right.

Wide data are often used for data visualisation and processing since the data can easily be grouped 
into the necessary axes for chart libraries. However, it's a difficult archival format since updating 
such a dataseries requires the equivalent of creating a new field (the year in the fields above) and 
then updating every row with appropriate information. That can be an expensive operation in a large 
database, and also means that writing a programmatic method for querying your data is more challenging.

**Long data** present numerical data in multiple rows with only one column for values. New data go 
down the screen from top to bottom. These were the sort of data we used in the first tutorial.

Long data are best for archival and for representing the structure you will ordinarily find in a 
database. Each row in a long dataseries represents a row in a database. Adding new information is 
relatively straightforward since you only need update a single row at a time. In database terms, 
you'd be creating a single database entry.

.. warning:: The preference in open data publication is for the long format, and this will be the 
    method usually recommended for release. That said, conversion between them - as long as data 
    are machine-readable with well-defined metadata - is straightforward.

Our tutorial data are wide, and horrifically malformed:

* Merged headers, and a header row smeared across multiple rows which doesn't start at the top
* References scattered throughout the data
* Aggregations which can safely be left out
* Blank columns and rows, and redundant information

Let's make a stab at fixing it::

    >>> import numpy as np
    >>> import whyqd
    >>> SOURCE_DATA = [
            "HDR 2007-2008 Table 03.xlsx"
        ]
    >>> SCHEMA_SOURCE = DIRECTORY + "human-development-report.json"
    >>> SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
    >>> method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
    >>> method.set({"name": "human-development-report-method"})
    >>> input_data = {"path": SOURCE_DATA}
    >>> method.add_data(source=input_data)

You can collect any sample data from the `Data wrangling & validation <https://github.com/whythawk/data-wrangling-and-validation>`_
course. The `sample data folder <https://github.com/whythawk/data-wrangling-and-validation/tree/master/data/lesson-spreadsheet>`_
contains a selection of files you can use. This tutorial uses `HDR 2007-2008 Table 03.xlsx`.

If you open this file in `pandas` you'll see a problem::

    >>> df = pd.read_excel(source_data)

+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|    | Unnamed: 0                                      |   Unnamed: 1 |   Unnamed: 2 | Monitoring human development: enlarging people's choices …   |   Unnamed: 4 |   Unnamed: 5 |   Unnamed: 6 | Unnamed: 7                                         |   Unnamed: 8 | Unnamed: 9               |   Unnamed: 10 | Unnamed: 11                                    |   Unnamed: 12 | Unnamed: 13                    |   Unnamed: 14 | Unnamed: 15          |   Unnamed: 16 |   Unnamed: 17 |   Unnamed: 18 |   Unnamed: 19 |   Unnamed: 20 | Unnamed: 21                           |
+====+=================================================+==============+==============+==============================================================+==============+==============+==============+====================================================+==============+==========================+===============+================================================+===============+================================+===============+======================+===============+===============+===============+===============+===============+=======================================+
|  0 | 3 Human and income poverty Developing countries |          nan |          nan | nan                                                          |          nan |          nan |          nan | nan                                                |          nan | nan                      |           nan | nan                                            |           nan | nan                            |           nan | nan                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  1 | nan                                             |          nan |          nan | nan                                                          |          nan |          nan |          nan | nan                                                |          nan | nan                      |           nan | nan                                            |           nan | nan                            |           nan | nan                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  2 | nan                                             |          nan |          nan | nan                                                          |          nan |          nan |          nan | nan                                                |          nan | nan                      |           nan | nan                                            |           nan | nan                            |           nan | nan                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  3 | nan                                             |          nan |          nan | nan                                                          |          nan |          nan |          nan | nan                                                |          nan | nan                      |           nan | nan                                            |           nan | nan                            |           nan | nan                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  4 | nan                                             |          nan |          nan | nan                                                          |          nan |          nan |          nan | nan                                                |          nan | nan                      |           nan | nan                                            |           nan | nan                            |           nan | nan                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  5 | nan                                             |          nan |          nan | nan                                                          |          nan |          nan |          nan | nan                                                |          nan | nan                      |           nan | nan                                            |           nan | nan                            |           nan | nan                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  6 | nan                                             |          nan |          nan | nan                                                          |          nan |          nan |          nan | nan                                                |          nan | nan                      |           nan | nan                                            |           nan | nan                            |           nan | nan                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  7 | nan                                             |          nan |          nan | nan                                                          |          nan |          nan |          nan | Probability at birth of not surviving to age 40a,† |          nan | nan                      |           nan | nan                                            |           nan | MDG                            |           nan | MDG                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
|    |                                                 |              |              |                                                              |              |              |              | (% of cohort)                                      |              |                          |               |                                                |               |                                |               |                      |               |               |               |               |               |                                       |
|    |                                                 |              |              |                                                              |              |              |              | 2000-05                                            |              |                          |               |                                                |               |                                |               |                      |               |               |               |               |               |                                       |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  8 | nan                                             |          nan |          nan | nan                                                          |          nan |          nan |          nan | nan                                                |          nan | Adult illiteracy rateb,† |           nan | Population not using an improved water source† |           nan | Children under weight for age† |           nan | Population below     |           nan |           nan |           nan |           nan |           nan | HPI-1 rank minus income poverty rankc |
|    |                                                 |              |              |                                                              |              |              |              |                                                    |              | (% aged 15 and older)    |               | (%)                                            |               | (% under age 5)                |               | income poverty line  |               |               |               |               |               |                                       |
|    |                                                 |              |              |                                                              |              |              |              |                                                    |              | 1995-2005                |               | 2004                                           |               | 1996-2005d                     |               | (%)                  |               |               |               |               |               |                                       |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+
|  9 | nan                                             |          nan |          nan | Human poverty index                         (HPI-1)          |          nan |          nan |          nan | nan                                                |          nan | nan                      |           nan | nan                                            |           nan | nan                            |           nan | nan                  |           nan |           nan |           nan |           nan |           nan | nan                                   |
+----+-------------------------------------------------+--------------+--------------+--------------------------------------------------------------+--------------+--------------+--------------+----------------------------------------------------+--------------+--------------------------+---------------+------------------------------------------------+---------------+--------------------------------+---------------+----------------------+---------------+---------------+---------------+---------------+---------------+---------------------------------------+

There doesn't seem to be any data. At this stage you may be tempted to start hacking at the file 
directly and see what you can fix, but our objective is not only clean data, but also an auditable 
record of how you went from source to final that can demonstrate the decisions you made, and 
whether you were able to maintain all the source data.

**Whyqd** offers a comprehensive set of :doc:`action_api` that permit you to restructure your data. Here are the ones we're going
to use:

* DEBLANK - Remove all blank columns and rows from a DataFrame.
* DEDUPE - Remove all duplicated rows from a DataFrame.
* DELETE_ROWS - Delete rows provided in a list. They don't have to be contiguous.
* JOIN - Join values in different fields to create a new concatenated value. Each value will be converted to a string 
  (e.g. A: 'Word 1' B: 'Word 2' => 'Word 1 Word 2').
* PIVOT_CATEGORIES - Convert row-level categories into column categorisations.
* PIVOT_LONGER - Transform a DataFrame from wide to long format.
* REBASE - Rebase the header row at an indexed row and drop rows above that point.
* RENAME - Rename an existing field to conform to a schema name. Only valid where a single field is provided.
* RENAME_ALL - Rename header columns listed in a dict.
* RENAME_NEW - Rename a column outside of the schema or existing column definitions. To be used with caution.
* SPLIT - Split the string values in a single column into any number of new columns on a specified key.

If you review the data in `pandas` you'll see that the main part of the header row starts at row index 11. Let's rebase
the table and see if that improves things::

    >>> schema_scripts = [
            "DEBLANK",
            "DEDUPE",
            "REBASE < [11]",
        ]
    >>> source_data = method.get.input_data[0]
    >>> method.add_actions(schema_scripts, source_data.uuid.hex, sheet_name=source_data.sheet_name)
    >>> df = method.transform(source_data)

+----+------------------------+------------------------+--------+--------+----------+--------+--------+--------+--------+--------+--------+--------+---------+---------+---------+---------+---------+---------+---------+---------+
|    | nan0                   | nan1                   | Rank   |   nan2 | Value    |   nan3 | nan4   | nan5   |   nan6 | nan7   |   nan8 | nan9   |   nan10 | nan11   |   nan12 | nan13   |   nan14 | nan15   |   nan16 | nan17   |
|    |                        |                        |        |        |  (%)     |        |        |        |        |        |        |        |         |         |         |         |         |         |         |         |
+====+========================+========================+========+========+==========+========+========+========+========+========+========+========+=========+=========+=========+=========+=========+=========+=========+=========+
| 14 | HIGH HUMAN DEVELOPMENT | nan                    | nan    |    nan | nan      |  nan   | nan    | nan    |    nan | nan    |    nan | nan    |     nan | nan     |     nan | nan     |     nan | nan     |     nan | nan     |
+----+------------------------+------------------------+--------+--------+----------+--------+--------+--------+--------+--------+--------+--------+---------+---------+---------+---------+---------+---------+---------+---------+
| 15 | 21                     | Hong Kong, China (SAR) | ..     |    nan | ..       |    1.5 | e      | ..     |    nan | ..     |    nan | ..     |     nan | ..      |     nan | ..      |     nan | ..      |     nan | ..      |
+----+------------------------+------------------------+--------+--------+----------+--------+--------+--------+--------+--------+--------+--------+---------+---------+---------+---------+---------+---------+---------+---------+
| 16 | 25                     | Singapore              | 7      |    nan | 5.2      |    1.8 | nan    | 7.5    |    nan | 0      |    nan | 3      |     nan | ..      |     nan | ..      |     nan | ..      |     nan | ..      |
+----+------------------------+------------------------+--------+--------+----------+--------+--------+--------+--------+--------+--------+--------+---------+---------+---------+---------+---------+---------+---------+---------+
| 17 | 26                     | Korea (Republic of)    | ..     |    nan | ..       |    2.5 | nan    | 1.0    |    nan | 8      |    nan | ..     |     nan | <2      |     nan | <2      |     nan | ..      |     nan | ..      |
+----+------------------------+------------------------+--------+--------+----------+--------+--------+--------+--------+--------+--------+--------+---------+---------+---------+---------+---------+---------+---------+---------+
| 18 | 28                     | Cyprus                 | ..     |    nan | ..       |    2.4 | nan    | 3.2    |    nan | 0      |    nan | ..     |     nan | ..      |     nan | ..      |     nan | ..      |     nan | ..      |
+----+------------------------+------------------------+--------+--------+----------+--------+--------+--------+--------+--------+--------+--------+---------+---------+---------+---------+---------+---------+---------+---------+

Well. No.

But we do notice a few things. Firstly, in row 14 there's a categorical term masquerading as heading, and we need to do
something about the headers.

When you look at the header row in the original source file, you see things like this:

.. figure:: images/undp-hdi-composite-header.jpg
    :alt: UNDP Human Development Index 2007-2008, composite header

    UNDP Human Development Index 2007-2008: composite header over multiple lines and columns

There's no way (currently) to efficiently write code to parse this. That particular composite is really several columns,
some of which are 'hidden':

 * 'Population below income poverty line (%) - $1 a day;;1990-2005',
 * 'Reference 6',
 * 'Population below income poverty line (%) - $2 a day;;1990-2005',
 * 'Reference 7',
 * 'Population below income poverty line (%) - National poverty line;;1990-2004'

Not only are the full descriptions split across multiple rows, but there's also a merged split header. Plus, years are
included with the text. We need to separate all of these components out into two new columns in the schema: 'year' and
'indicator_name'.

Pay attention to the `;;` term in the header. It is not there by accident but to help us split the text later.

Here's a list of the various things we need to fix:

* Replace the `nan` headers with a proper text header row,
* Convert the row-level categories (at rows 14, 44 and 120) into actual categories,
* Remove unnecessary rows towards the bottom of the table (from 144 onwards),
* Rename any newly-added columns to descriptive terms,
* Pivot the header row to create a new 'indicator_name' column,
* Split the 'indicator_name' column to separate the 'year' into its own column,
* Join all the separate 'Reference' columns into a single column.

That's quite a lot, and you won't figure it out without studying your data and having insight into what it means. The
information we're deleting from the bottom is also not irrelevent. They're the references that the abbreviated terms in
'reference' refer to ('e' is a reference to the footnotes). However, we can extract these footnotes in a separate 
process.

Neither will this restructuring yield 'clean' data. Too many of the terms in the 'values' column are anything but.
However, that is for your analytical software to process. **Whyqd's** job is to ensure that your data conforms to 
a schema so your analytical systems can access it.

Let's convert these steps to action scripts::

    >>> source_data = method.get.input_data[0]
    >>> df = method.transform(source_data)
    >>> schema_scripts = [
            f"DELETE_ROWS < {[int(i) for i in np.arange(144, df.index[-1]+1)]}",
            "RENAME_ALL > ['HDI rank;;2008', 'Country', 'Human poverty index (HPI-1) - Rank;;2008', 'Reference 1', 'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05', 'Reference 2', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Reference 3', 'Population not using an improved water source (%);;2004', 'Reference 4', 'Children under weight for age (% under age 5);;1996-2005', 'Reference 5', 'Population below income poverty line (%) - $1 a day;;1990-2005', 'Reference 6', 'Population below income poverty line (%) - $2 a day;;1990-2005', 'Reference 7', 'Population below income poverty line (%) - National poverty line;;1990-2004', 'Reference 8', 'HPI-1 rank minus income poverty rank;;2008']",
            "PIVOT_CATEGORIES > ['HDI rank;;2008'] < [14,44,120]",
            "RENAME_NEW > 'HDI Category;;2008'::['PIVOT_CATEGORIES_idx_20_0']",
            "PIVOT_LONGER > = ['HDI rank;;2008', 'HDI Category;;2008', 'Human poverty index (HPI-1) - Rank;;2008', 'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Population not using an improved water source (%);;2004', 'Children under weight for age (% under age 5);;1996-2005', 'Population below income poverty line (%) - $1 a day;;1990-2005', 'Population below income poverty line (%) - $2 a day;;1990-2005', 'Population below income poverty line (%) - National poverty line;;1990-2004', 'HPI-1 rank minus income poverty rank;;2008']",
            "SPLIT > ';;'::['PIVOT_LONGER_names_idx_9']",
            "DEBLANK",
            "DEDUPE",
        ]
    >>> method.add_actions(schema_scripts, source_data.uuid.hex, sheet_name=source_data.sheet_name)

We used `numpy` to create an array of the rows we wish to delete. To do that, we need to know how many there are::

    df.index[-1]+1

*For those unfamiliar with Python or Numpy.* A `numpy` range (like everything in Python) is zero-indexed, meaning that
the list starts from 0. If you want an array of `[1,2,3,4,5]`, `arange(5)` would give you `[0,1,2,3,4]`. If you want
`[144,145,...]` and you want to include the last row as well, you need to do two steps, get the last row index
`df.index[-1]`, and increment it by `1`.

.. note:: *Whyqd*  deliberately differentiates between `RENAME` into the schema, and `RENAME_NEW` to unambiguously 
    introduce new headers that are not part of the schema. A list of action scripts must be readable to ensure clarity
    during any review. It should be clear when you're introducing new information, and when you're moving data into 
    the schema.

Finally, we need to join the disparate reference columns. First, though, we need to ensure we know which ones are still
with us. Those `DEDUPE` and `DEBLANK` actions may have removed any that weren't necessary::

    >>> reference_columns = [c.name for c in method.get.input_data[0].columns if c.name.startswith("Reference")]
    >>> schema_scripts = [
            f"JOIN > 'reference' < {reference_columns}",
            "RENAME > 'indicator_name' < ['SPLIT_idx_11_0']",
            "RENAME > 'country_name' < ['Country']",
            "RENAME > 'year' < ['SPLIT_idx_12_1']",
            "RENAME > 'values' < ['PIVOT_LONGER_values_idx_10']",
        ]
    >>> method.add_actions(schema_scripts, source_data.uuid.hex, sheet_name=source_data.sheet_name)

The final set of `RENAME` move our data into the schema. The `build` process will check the schema to ensure that all
requirements are met, and only then allow you to complete transformation::

    >>> method.build()

+----+------------------------+------------------+-------------+--------+----------+
|    | country_name           | indicator_name   | reference   |   year |   values |
+====+========================+==================+=============+========+==========+
|  0 | Hong Kong, China (SAR) | HDI rank         | e           |   2008 |       21 |
+----+------------------------+------------------+-------------+--------+----------+
|  1 | Singapore              | HDI rank         | nan         |   2008 |       25 |
+----+------------------------+------------------+-------------+--------+----------+
|  2 | Korea (Republic of)    | HDI rank         | nan         |   2008 |       26 |
+----+------------------------+------------------+-------------+--------+----------+
|  3 | Cyprus                 | HDI rank         | nan         |   2008 |       28 |
+----+------------------------+------------------+-------------+--------+----------+
|  4 | Brunei Darussalam      | HDI rank         | nan         |   2008 |       30 |
+----+------------------------+------------------+-------------+--------+----------+

I encourage you to explore this dataset and see if you agree with the decisions made. And, hopefully, as far as Cthulhu
datasets are concerned, the deep holds a smidgeon fewer fears.

