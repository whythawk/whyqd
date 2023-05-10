from pathlib import Path

import whyqd as qd
from whyqd.parsers import CoreParser

CORE = CoreParser()
SOURCE_DIRECTORY = Path(__file__).resolve().parent / "data"
# CTHULHU
# World Bank Human Development Report 2007 - 2008 in Cthulhu format. Demonstrate define a schema,
# create a method, import data, perform actions and generate a schema-compliant output.
# Copies at: https://github.com/whythawk/data-wrangling-and-validation/tree/master/data/lesson-spreadsheet
SOURCE_DATA_CTHULHU = SOURCE_DIRECTORY / "test_cthulu_source.data"
INTERIM_DATA_CTHULHU = SOURCE_DIRECTORY / "test_cthulu_interim.data"
SOURCE_SCHEMA_CTHULHU = SOURCE_DIRECTORY / "test_cthulu_source.schema"
INTERIM_SCHEMA_CTHULHU = SOURCE_DIRECTORY / "test_cthulu_interim.schema"
DESTINATION_SCHEMA_CTHULHU = SOURCE_DIRECTORY / "test_cthulu_destination.schema"
# PORTSMOUTH
# Portsmouth ratepayer data in multiple sheets. Demonstrating create method, add date,
# actions and perform a merge, plus filter the final result.
SOURCE_DATA_PORTSMOUTH = SOURCE_DIRECTORY / "test_portsmouth_source.data"
SOURCE_SCHEMA_PORTSMOUTH = SOURCE_DIRECTORY / "test_portsmouth_source.schema"
DESTINATION_SCHEMA_PORTSMOUTH = SOURCE_DIRECTORY / "test_portsmouth_destination.schema"


def _test_script_action(script, schema_source, schema_destination, data_source):
    crosswalk = qd.CrosswalkDefinition()
    crosswalk.set(schema_source=schema_source, schema_destination=schema_destination)
    if isinstance(script, list):
        crosswalk.actions.add_multi(terms=script)
    else:
        crosswalk.actions.add(term=script)
    transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=data_source)
    transform.process()
    return True


"""
The mechanism for testing every action is:

- create a script for the source data
- parse the script
- run the transform on the method

# CTHULHU
Source Schema:      ['column_0', 'column_1', 'column_2', 'column_3', 'column_4', 'column_5', 'column_6', 'column_7',
                    'column_8', 'column_9', 'column_10', 'column_11', 'column_12', 'column_13', 'column_14', 'column_15',
                    'column_16', 'column_17', 'column_18', 'column_19', 'column_20', 'column_21']
Interim Schema:     ['HDI rank', 'Country', 'Human poverty index (HPI-1) - Rank;;2008', 'Reference 1',
                    'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05',
                    'Reference 2', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Reference 3',
                    'Population not using an improved water source (%);;2004', 'Reference 4',
                    'Children under weight for age (% under age 5);;1996-2005', 'Reference 5',
                    'Population below income poverty line (%) - $1 a day;;1990-2005', 'Reference 6',
                    'Population below income poverty line (%) - $2 a day;;1990-2005', 'Reference 7',
                    'Population below income poverty line (%) - National poverty line;;1990-2004', 'Reference 8',
                    'HPI-1 rank minus income poverty rank;;2008', 'HDI Category']
Destination Schema: ['year', 'country_name', 'indicator_name', 'values', 'reference']

# PORTSMOUTH
Source Schema:      ['Property Reference Number', 'Primary Liable party name', 'Full Property Address',
                    'Current Relief Type', 'Account Start date', 'Current Relief Award Start Date',
                    'Current Rateable Value']
Destination Schema: ['la_code', 'ba_ref', 'prop_ba_rates', 'occupant_name', 'postcode', 'occupation_state',
                    'occupation_state_date', 'occupation_state_reliefs']

Base test:

    def test_deblank(self):
        script = "DEBLANK"
        assert _test_script_action(script, schema_source, schema_destination, data_source)
"""


class TestAction:
    """TEST IN ALPHABETICAL SELECT - EXCEPT FOR CATEGORY ASSIGN!"""

    def test_calculate(self):
        script = "CALCULATE > 'prop_ba_rates' < [+ 'Current Rateable Value', - 'Current Rateable Value', + 'Current Rateable Value']"
        assert _test_script_action(
            script, SOURCE_SCHEMA_PORTSMOUTH, DESTINATION_SCHEMA_PORTSMOUTH, SOURCE_DATA_PORTSMOUTH
        )

    def test_categorise(self):
        script = [
            "CATEGORISE > 'occupation_state'::False < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
            "CATEGORISE > 'occupation_state_reliefs'::'small_business' < 'Current Relief Type'::['Small Business Relief England', 'Sbre Extension For 12 Months', 'Supporting Small Business Relief']",
            "CATEGORISE > 'occupation_state_reliefs'::'vacancy' < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
            "CATEGORISE > 'occupation_state_reliefs'::'retail' < 'Current Relief Type'::['Retail Discount']",
            "CATEGORISE > 'occupation_state_reliefs'::'other' < 'Current Relief Type'::['Sports Club (Registered CASC)', 'Mandatory']",
        ]
        assert _test_script_action(
            script, SOURCE_SCHEMA_PORTSMOUTH, DESTINATION_SCHEMA_PORTSMOUTH, SOURCE_DATA_PORTSMOUTH
        )

    def test_deblank(self):
        script = "DEBLANK"
        assert _test_script_action(script, INTERIM_SCHEMA_CTHULHU, DESTINATION_SCHEMA_CTHULHU, INTERIM_DATA_CTHULHU)

    def test_dedupe(self):
        script = "DEDUPE"
        assert _test_script_action(script, INTERIM_SCHEMA_CTHULHU, DESTINATION_SCHEMA_CTHULHU, INTERIM_DATA_CTHULHU)

    def test_delete_rows(self):
        script = f"DELETE_ROWS < {list(range(15))}"
        assert _test_script_action(script, SOURCE_SCHEMA_CTHULHU, INTERIM_SCHEMA_CTHULHU, SOURCE_DATA_CTHULHU)

    def test_new(self):
        script = "NEW > 'la_code' < ['E06000044']"
        assert _test_script_action(
            script, SOURCE_SCHEMA_PORTSMOUTH, DESTINATION_SCHEMA_PORTSMOUTH, SOURCE_DATA_PORTSMOUTH
        )

    def test_pivot_categories(self):
        script = "PIVOT_CATEGORIES > 'HDI Category' < 'column_0'::[15, 45, 121]"
        assert _test_script_action(script, SOURCE_SCHEMA_CTHULHU, INTERIM_SCHEMA_CTHULHU, SOURCE_DATA_CTHULHU)

    def test_pivot_longer(self):
        script = "PIVOT_LONGER > ['indicator_name', 'values'] < ['HDI rank', 'HDI Category', 'Human poverty index (HPI-1) - Rank;;2008', 'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Population not using an improved water source (%);;2004', 'Children under weight for age (% under age 5);;1996-2005', 'Population below income poverty line (%) - $1 a day;;1990-2005', 'Population below income poverty line (%) - $2 a day;;1990-2005', 'Population below income poverty line (%) - National poverty line;;1990-2004', 'HPI-1 rank minus income poverty rank;;2008']"
        assert _test_script_action(script, INTERIM_SCHEMA_CTHULHU, DESTINATION_SCHEMA_CTHULHU, INTERIM_DATA_CTHULHU)

    def test_rename(self):
        script = "RENAME > 'country_name' < ['Country']"
        assert _test_script_action(script, INTERIM_SCHEMA_CTHULHU, DESTINATION_SCHEMA_CTHULHU, INTERIM_DATA_CTHULHU)

    def test_select_newest(self):
        script = "SELECT_NEWEST > 'occupation_state_date' < ['Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date' + 'Account Start date']"
        assert _test_script_action(
            script, SOURCE_SCHEMA_PORTSMOUTH, DESTINATION_SCHEMA_PORTSMOUTH, SOURCE_DATA_PORTSMOUTH
        )

    def test_select_oldest(self):
        script = "SELECT_OLDEST > 'occupation_state_date' < ['Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date' + 'Account Start date']"
        assert _test_script_action(
            script, SOURCE_SCHEMA_PORTSMOUTH, DESTINATION_SCHEMA_PORTSMOUTH, SOURCE_DATA_PORTSMOUTH
        )

    def test_select(self):
        script = "SELECT > 'occupation_state_date' < ['Account Start date', 'Current Relief Award Start Date']"
        assert _test_script_action(
            script, SOURCE_SCHEMA_PORTSMOUTH, DESTINATION_SCHEMA_PORTSMOUTH, SOURCE_DATA_PORTSMOUTH
        )

    def test_separate(self):
        script = [
            "PIVOT_LONGER > ['indicator_name', 'values'] < ['HDI rank', 'HDI Category', 'Human poverty index (HPI-1) - Rank;;2008', 'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Population not using an improved water source (%);;2004', 'Children under weight for age (% under age 5);;1996-2005', 'Population below income poverty line (%) - $1 a day;;1990-2005', 'Population below income poverty line (%) - $2 a day;;1990-2005', 'Population below income poverty line (%) - National poverty line;;1990-2004', 'HPI-1 rank minus income poverty rank;;2008']",
            "SEPARATE > ['indicator_name', 'year'] < ';;'::['indicator_name']",
        ]
        assert _test_script_action(script, INTERIM_SCHEMA_CTHULHU, DESTINATION_SCHEMA_CTHULHU, INTERIM_DATA_CTHULHU)

    def test_unite(self):
        script = "UNITE > 'reference' < ['Reference 1', 'Reference 2', 'Reference 3', 'Reference 4', 'Reference 5', 'Reference 6', 'Reference 7', 'Reference 8']"
        assert _test_script_action(script, INTERIM_SCHEMA_CTHULHU, DESTINATION_SCHEMA_CTHULHU, INTERIM_DATA_CTHULHU)
        script = "UNITE > 'reference' < '*'::['Reference 1', 'Reference 2', 'Reference 3', 'Reference 4', 'Reference 5', 'Reference 6', 'Reference 7', 'Reference 8']"
        assert _test_script_action(script, INTERIM_SCHEMA_CTHULHU, DESTINATION_SCHEMA_CTHULHU, INTERIM_DATA_CTHULHU)
