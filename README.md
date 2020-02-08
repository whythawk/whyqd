# whyqd: data wrangling simplicity, complete audit transparency, and at speed

## What is it?

**whyqd** provides an intuitive and rapid method for restructuring messy data to conform to a
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

## Why is it needed?

There are two complex and time-consuming parts to preparing data for analysis: social, and technical.

The social part requires multi-stakeholder engagement with source data-publishers, and with
destination database users, to agree structural metadata. Without any agreement on data publication
formats or destination structure, you are left with the tedious frustration of manually wrangling
each independent dataset into a single schema.

If all you want to do is test whether your source data are even useful, this time-consuming slog
could kill a project.

**whyqd** allows you to get to work without requiring you to achieve buy-in from anyone.

## Wrangling process

  - Create, update or import a data schema which defines the destination data structure;
  - Create a new method and associate it with your schema and input data source/s;
  - Assign a foreign key column and (if required) merge input data sources;
  - Structure input data fields to conform to the requriements for each schema field;
  - Assign categorical data identified during structuring;
  - Transform and filter input data to produce a final destination data file;

## Relationship to Frictionless Data

[Frictionlessdata.io](https://frictionlessdata.io/) is intended as a containerised validation schema
for CSV files. **whyqd** uses their *table schema* as a starting-point, but our objectives
are different.

For starters, there is no guarantee that a restructured dataset emerging from a
**whyqd** method will validate against *table schema* as this output is still an interim point
prior to automated data munging. There is also no expectation that the final destination for these
data would be a CSV, since it is more likely you are going to import into a database.

There are additional terms in the schema which are there to support data wrangling, and some of the
less meaningful field names have been changed. That said, **whyqd** was started, in part, as a
response to the frustration of open data projects failing to deliver data publication as government
data owners gave up because they couldn't get their (messy) data to validate against FrictionlessData
prior to official release approval.

## Licence
[BSD 3](LICENSE)
