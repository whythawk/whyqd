# whyqd: simplicity, transparency, speed

## What is it?

**whyqd** provides an intuitive method for restructuring messy data to conform to a standardised
metadata schema. It supports data managers and researchers looking to rapidly, and continuously,
normalise any messy spreadsheets using a simple series of steps. Once complete, you can import
wrangled data into more complex analytical systems or full-feature wrangling tools.

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

[Read the docs](https://whyqd.readthedocs.io/en/latest/) and a
[full tutorial](https://whyqd.readthedocs.io/en/latest/tutorial.html).

## Why use it?

If all you want to do is test whether your source data are even useful, spending days or weeks
slogging through data restructuring could kill a project. If you already have a workflow and
established software which includes Python and pandas, having to change your code every time your
source data changes is really, really frustrating.

There are two complex and time-consuming parts to preparing data for analysis: social, and technical.

The social part requires multi-stakeholder engagement with source data-publishers, and with
destination database users, to agree structural metadata. Without any agreement on data publication
formats or destination structure, you are left with the tedious frustration of manually wrangling
each independent dataset into a single schema.

**whyqd** allows you to get to work without requiring you to achieve buy-in from anyone or change
your existing code.

## Wrangling process

  - Create, update or import a data schema which defines the destination data structure;
  - Create a new method and associate it with your schema and input data source/s;
  - Assign a foreign key column and (if required) merge input data sources;
  - Structure input data fields to conform to the requriements for each schema field;
  - Assign categorical data identified during structuring;
  - Transform and filter input data to produce a final destination data file;
  - Share your data and a citation;

## Installation and dependencies

  pip install whyqd

Code has been tested on the following dependency versions:

* numpy=1.18.1
* openpyxl=3.0.3
* pandas=1.0.0
* tabulate=0.8.3
* xlrd=1.2.0

## Background

**whyqd** was created to serve a continuous data wrangling process, including collaboration on more
complex messy sources, ensuring the integrity of the source data, and producing a complete audit
trail from data imported to our database, back to source. You can see the product of that at
[Sqwyre.com](https://sqwyre.com).

[Frictionlessdata.io](https://frictionlessdata.io/) is intended as a containerised validation schema
for CSV files. **whyqd** uses their *table schema* as a starting-point, but our objectives
are different.

For starters, there is no guarantee that a restructured dataset emerging from a
**whyqd** method will validate against *table schema* as this output is still an interim point
prior to automated data munging. There is also no expectation that the final destination for these
data would be a CSV, since it is more likely you are going to import into a database.

There are additional terms in the schema which are there to support data wrangling and data integrity,
and some of the less meaningful field names have been changed.

The 'backronym' for **whyqd** /wɪkɪd/ is *Whythawk Quantitative Data*, [Whythawk](https://whythawk.com)
is an open data science and open research technical consultancy.

## Licence
[BSD 3](LICENSE)