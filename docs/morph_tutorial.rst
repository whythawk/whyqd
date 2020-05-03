Table morph tutorial
====================

For years I've taught an introductory `Data wrangling & validation <https://github.com/whythawk/data-wrangling-and-validation>`_ 
course using the same training data-series: the Human Development Index report of 2007 - 2008 
released by the UNDP as part of the Millennial Development Goals.

.. note:: In 1990 the first `Human Development Report <http://www.hdr.undp.org/>`_ introduced a new 
    approach for advancing human wellbeing. Human development – or the human development approach - is 
    about expanding the richness of human life, rather than simply the richness of the economy in which 
    human beings live. It is an approach that is focused on people and their opportunities and choices.

These days it's a slick affair with beautifully-prepared open data in a standardised format. Back then 
it was a constantly-changing mess of non-standard Excel spreadsheets.

.. figure:: images/undp-hdi-2007-8.jpg
    :alt: UNDP Human Development Index 2007-2008

    UNDP Human Development Index 2007-2008: a beautiful example of messy data.

Teaching open data managers in countries around the world the importance of open standards and well-structured
machine-readable data is brought home when seeing this and experiencing how difficult it is to work with.

I never really expected to fix this sort of thing programmatically. However, with a little creativity,
it turns out you can.

Creating a Schema
-----------------

The 2007-8 HDI report was listed as a series of about 50 spreadsheets, each dataset aligned with the 
objectives of the `Millennium Development Goals <https://www.un.org/millenniumgoals/>`_. These supporting
information were used to track countries meeting the MDG targets. Analysis required rebuilding these 
spreadsheets into a single database aligned to a common schema.

This tutorial assumes you have already completed :doc:`tutorial` or are familiar with the concepts used
in **whyqd**::

    import whyqd as _w
    schema = _w.Schema()
    details = {
            "name": "human-development-report",
            "title": "UN Human Development Report 2007 - 2008",
            "description": """
            In 1990 the first Human Development Report introduced a new approach for 
            advancing human wellbeing. Human development – or the human development approach - is about 
            expanding the richness of human life, rather than simply the richness of the economy in which 
            human beings live. It is an approach that is focused on people and their opportunities and choices."""
    }
    schema = _w.Schema()
    schema.set_details(**details)

Let's define the fields in our schema and then iterate over the list to add each field::

    fields = [
        {
            "name": "Country Name",
            "title": "Country Name",
            "type": "string",
            "description": "Official country names.",
            "constraints": {
                "required": True
            }
        },
        {
            "name": "Indicator Name",
            "title": "Indicator Name",
            "type": "string",
            "description": "Indicator described in the data series.",
        },
        {
            "name": "Reference",
            "title": "Reference",
            "type": "string",
            "description": "Reference to data source.",
        },
        {
            "name": "Year",
            "title": "Year",
            "type": "year",
            "description": "Year of release.",
        },
        {
            "name": "Values",
            "title": "Values",
            "type": "number",
            "description": "Value for the Year and Indicator Name.",
            "constraints": {
                "required": True
            }
        },
    ]
    for field in fields:
        schema.set_field(**field)

We can save our schema to a specified `directory`::

    directory = "/path/to/directory"
    filename = "human-development-report-schema"
    schema.save(directory, filename=filename, overwrite=True)

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
* References scattered throughout data
* Aggregations which can safely be left out
* Blank columns and rows, and redundant information

The :doc:`morph_api` class offers a set of tools for manipulating and restructuring these data, while 
also adding a record of these transactions into the :doc:`method`. In this tutorial, we're focused
on the morph component::

    from IPython.core.display import HTML
    display(HTML("<style>pre { white-space: pre !important; }</style>"))

    import numpy as np
    import whyqd as _w

    SCHEMA_SOURCE = "/full/path_to/human-development-report-schema.json"
    DIRECTORY = "/path_to/working/directory/"
    INPUT_DATA = [
        "HDR 2007-2008 Table 03.xlsx"
    ]
    method = _w.Method(SCHEMA_SOURCE, directory=DIRECTORY, input_data=INPUT_DATA)

You can collect any sample data from the `Data wrangling & validation <https://github.com/whythawk/data-wrangling-and-validation>`_ 
course. The `sample data folder <https://github.com/whythawk/data-wrangling-and-validation/tree/master/data/lesson-spreadsheet>`_
contains a selection of files you can use. This tutorial uses `HDR 2007-2008 Table 03.xlsx`.

When you get help on the next step, you'll see a problem::

    print(method.print_input_data())

    Data id: 1aff74e7-8115-42d0-bf00-4660966e0a52
    Original source: HDR 2007-2008 Table 03.xlsx

    ====  ===============================================  ============  ============  ============================================================  ============  ============  ============  ============  ============  ============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============
    ..  Unnamed: 0                                         Unnamed: 1    Unnamed: 2    Monitoring human development: enlarging people's choices …    Unnamed: 4    Unnamed: 5    Unnamed: 6    Unnamed: 7    Unnamed: 8    Unnamed: 9    Unnamed: 10    Unnamed: 11    Unnamed: 12    Unnamed: 13    Unnamed: 14    Unnamed: 15    Unnamed: 16    Unnamed: 17    Unnamed: 18    Unnamed: 19    Unnamed: 20    Unnamed: 21    Unnamed: 22    Unnamed: 23    Unnamed: 24    Unnamed: 25    Unnamed: 26    Unnamed: 27    Unnamed: 28    Unnamed: 29    Unnamed: 30
    ====  ===============================================  ============  ============  ============================================================  ============  ============  ============  ============  ============  ============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============
    0  3 Human and income poverty Developing countries           nan           nan                                                           nan           nan           nan           nan           nan           nan           nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan
    1  nan                                                       nan           nan                                                           nan           nan           nan           nan           nan           nan           nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan
    2  nan                                                       nan           nan                                                           nan           nan           nan           nan           nan           nan           nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan            nan
    ====  ===============================================  ============  ============  ============================================================  ============  ============  ============  ============  ============  ============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============  =============

There doesn't seem to be any data. At this stage you may be tempted to start hacking at the file 
directly and see what you can fix, but our objective is not only clean data, but also an auditable 
record of how you went from source to final that can demonstrate the decisions you made, and 
whether you were able to maintain all the source data.

**Whyqd** offers a set of morphs that permit you to restructure individual tables prior to merging.
As with :doc:`action_api`, you can list the available morphs::

    method.default_morph_types

    ['CATEGORISE', 'DEBLANK', 'DEDUPE', 'DELETE', 'MELT', 'REBASE', 'RENAME']

    # As an example:
    method.default_morph_settings("CATEGORISE")

    {'name': 'CATEGORISE', 
    'title': 'Categorise', 
    'type': 'morph', 
    'description': 'Convert row-level categories into column categorisations.', 
    'structure': ['rows', 'column_names']}

Similarly to an Action, the standard way of writing a morph is::

    ["MORPH_NAME", [rows], [columns], [column_names]]

The presence of the parameters - `rows`, `columns`, `column_names` - is specified in the `structure`
of the morph type.

* `rows`: address the row number of the table. These will remain immutable, so the row number is the row number.
* `columns`: these are the actual column names at that point of the morph. There **are** mutable and change as you morph.
* `column_names`: these are optional, but you can provide root names that will be used in creating new columns.

When you add your first morph, **whyqd** will automatically add in `DEBLANK` and `DEDUPE`. Figuring 
out the exact order of the morphs is trial-and-error, but nothing is committed and you can undo and redo 
as you require.

A few tools to help you ... `input_dataframe(id)` returns the complete `pandas` dataframe for your 
source data. It will also run all of the morphas up to that point, allowing you to see the impact of
your morph order. You can then explore our data and figure out what we need to do next::

    # We only have one input_data source file
    _id = method.input_data[0]["id"]
    df = method.input_dataframe(_id)

If you get to a point where you're tangled entirely, `reset_input_data_morph(id)` will remove all the
morphs and let you start again::

    method.reset_input_data_morph(_id)

I encourage you to explore this dataset and see exactly the decisions made, but here's my approach:

* Let's rebase the table to the top of the actual data::

    method.add_input_data_morph(_id, ["REBASE", 11])

* We can get rid of rows below `144` to the end of the table. These contain metadata that you may want
  to keep and publish separately::

    rows = [int(i) for i in np.arange(144, df.index[-1]+1)]
    method.add_input_data_morph(_id, ["DELETE", rows])

* Now lets name the columns that remain based on what their original names. Also note that the 
  reference columns were previously unlabeled::

    columns = [
        "HDI rank",
        "Country",
        "Human poverty index (HPI-1) - Rank",
        "Reference 1",
        "Human poverty index (HPI-1) - Value (%)",
        "Probability at birth of not surviving to age 40 (% of cohort) 2000-05",
        "Reference 2",
        "Adult illiteracy rate (% aged 15 and older) 1995-2005",
        "Reference 3",
        "Population not using an improved water source (%) 2004",
        "Reference 4",
        "Children under weight for age (% under age 5) 1996-2005",
        "Reference 5",
        "Population below income poverty line (%) - $1 a day 1990-2005",
        "Reference 6",
        "Population below income poverty line (%) - $2 a day 1990-2005",   
        "Reference 7",
        "Population below income poverty line (%) - National poverty line 1990-2004",   
        "Reference 8",
        "HPI-1 rank minus income poverty rank"
    ]
    method.add_input_data_morph(_id, ["RENAME", columns])

* If you look through the data, you'll see that there are rows that define categories for data that 
  appear below it. Here `HIGH HUMAN DEVELOPMENT` is an `HDI Category` and all the rows between this row
  and the next category `MEDIUM HUMAN DEVELOPMENT` form part of that category. What we need to do is 
  "rotate" these rows into a column and assign the category to the effected data::

    rows = [14,44,120] # These contain the categorical data
    method.add_input_data_morph(_id, ["CATEGORISE", rows, "HDI category"])

* Most of these columns are actually indicators and can be pivoted into an `Indicator` column with 
  the `Values` assigned into a single column. This is called a `MELT`::

    # Select all the columns to be melted
    columns = [
        "HDI rank",
        "HDI category",
        "Human poverty index (HPI-1) - Rank",
        "Human poverty index (HPI-1) - Value (%)",
        "Probability at birth of not surviving to age 40 (% of cohort) 2000-05",
        "Adult illiteracy rate (% aged 15 and older) 1995-2005",
        "Population not using an improved water source (%) 2004",
        "Children under weight for age (% under age 5) 1996-2005",
        "Population below income poverty line (%) - $1 a day 1990-2005",
        "Population below income poverty line (%) - $2 a day 1990-2005",   
        "Population below income poverty line (%) - National poverty line 1990-2004",   
        "HPI-1 rank minus income poverty rank"
    ]
    method.add_input_data_morph(_id, ["MELT", columns, ["Indicator Name", "Indicator Value"]])

* Similarly, the `References` can be pivoted into a separate column as well::

    columns = [
        "Reference 1",
        "Reference 2",
        "Reference 3",
        "Reference 4",
        "Reference 5",
        "Reference 6",  
        "Reference 7",  
        "Reference 8",
    ]
    method.add_input_data_morph(_id, ["MELT", columns, ["Reference Name", "Reference"]])

* Let's add in a final `DEBLANK` just to be sure::

    method.add_input_data_morph(_id, ["DEBLANK"])

Get the current implementation of the morphs and have a look::

    df = method.input_dataframe(_id)
    df.head()

====  ======================  ================  =================  ================  ===========
  ..  Country                 Indicator Name      Indicator Value  Reference Name      Reference
====  ======================  ================  =================  ================  ===========
   0  Hong Kong, China (SAR)  HDI rank                         21  Reference 1               nan
   1  Singapore               HDI rank                         25  Reference 1               nan
   2  Korea (Republic of)     HDI rank                         26  Reference 1               nan
   3  Cyprus                  HDI rank                         28  Reference 1               nan
   4  Brunei Darussalam       HDI rank                         30  Reference 1               nan
====  ======================  ================  =================  ================  ===========

Cool, huh? Let's quickly finish up the `method`::

    method.merge(overwrite_working=True)
    print(method.help("structure"))

`structure` is the core of the wrangling process and is the process where you define the actions
which must be performed to restructure your working data.

Create a list of methods of the form::

	{
		"schema_field1": ["action", "column_name1", ["action", "column_name2"]],
		"schema_field2": ["action", "column_name1", "modifier", ["action", "column_name2"]],
	}

The format for defining a `structure` is as follows::

	[action, column_name, [action, column_name]]

e.g.::

	["CATEGORISE", "+", ["ORDER", "column_1", "column_2"]]

This permits the creation of quite expressive wrangling structures from simple building
blocks.

The schema for this method consists of the following terms::

    ['country_name', 'indicator_name', 'reference', 'year', 'values']

The actions::

    ['CALCULATE', 'CATEGORISE', 'JOIN', 'NEW', 'ORDER', 'ORDER_NEW', 'ORDER_OLD', 'RENAME']

The columns from your working data::

    ['Country', 'Indicator Value', 'Indicator Name', 'Reference Name', 'Reference']

    Data id: working_21ebcf74-e6ab-4a19-bd9a-d1a072ed96a2
    Original source: method.input_data

====  ======================  =================  ================  ================  ===========
  ..  Country                   Indicator Value  Indicator Name    Reference Name      Reference
====  ======================  =================  ================  ================  ===========
   0  Hong Kong, China (SAR)                 21  HDI rank          Reference 1               nan
   1  Singapore                              25  HDI rank          Reference 1               nan
   2  Korea (Republic of)                    26  HDI rank          Reference 1               nan
====  ======================  =================  ================  ================  ===========

    Current method status: `Ready to Structure`

And::

    structure = {
        "country_name": ["RENAME", "Country"],
        "indicator_name": ["RENAME", "Indicator Name"],
        "reference": ["RENAME", "Reference"],
        "values": ["RENAME", "Indicator Value"],
    }
    method.set_structure(**structure)
    method.transform(overwrite_output=True)
    FILENAME = "hdi_report_exercise"
    method.save(directory, filename=FILENAME, overwrite=True)

Concluding the morphs tutorial.