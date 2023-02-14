from pathlib import Path
import numpy as np
from uuid import uuid4

import whyqd
from whyqd.transform.parsers import CoreScript

SOURCE_DIRECTORY = str(Path(__file__).resolve().parent)


def _test_script_world_bank(DIRECTORY, script, rebase=False):
    """World Bank urban population time-series, in wide format. Demonstrate define a schema,
    create a method, import data, perform actions and generate a schema-compliant output.
    From https://databank.worldbank.org/reports.aspx?source=2&type=metadata&series=SP.URB.TOTL"""
    SCHEMA_NAME = "/data/urban_population.json"
    SCHEMA_SOURCE = SOURCE_DIRECTORY + SCHEMA_NAME
    SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
    SOURCE_DATA = SOURCE_DIRECTORY + "/data/working_test_world_bank_data.xlsx"
    method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
    method.set({"name": "urban_population_method"})
    method.add_data(source=SOURCE_DATA)
    scripts = []
    if rebase:
        scripts = [
            "DEBLANK",
            "DEDUPE",
            "REBASE < [2]",
        ]
    # Run the test script
    scripts.append(script)
    source_data = method.get.input_data[0]
    method.add_actions(actions=scripts, uid=source_data.uuid.hex, sheet_name=source_data.sheet_name)
    method.transform(source_data)
    return True


def _test_script_portsmouth(DIRECTORY, script, test_filter=False):
    """Portsmouth ratepayer data in multiple spreadsheets. Demonstrating create method, add date,
    actions and perform a merge, plus filter the final result."""
    SCHEMA_NAME = "/data/test_schema.json"
    SCHEMA_SOURCE = SOURCE_DIRECTORY + SCHEMA_NAME
    SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
    INPUT_DATA = SOURCE_DIRECTORY + "/data/working_test_data.xlsx"
    if test_filter:
        INPUT_DATA = SOURCE_DIRECTORY + "/data/restructured_test_data.xlsx"
    method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
    method.set({"name": "test_method"})
    method.add_data(source=INPUT_DATA)
    source_data = method.get.input_data[0]
    method.add_actions(actions=script, uid=source_data.uuid.hex, sheet_name=source_data.sheet_name)
    method.transform(source_data)
    return True


"""
The mechanism for testing every action is:

* method = _get_method(tmp_path)
* create a script for the source data
* parse the script
* run the transform on the method

World Bank
Schema: 'indicator_code', 'country_name', 'country_code', 'indicator_name', 'year', 'values'
Columns (with rebase=True):  'Country Name', 'Country Code', 'Indicator Name', 'Indicator Code', '1960', etc...

Portsmouth
Schema: 'la_code', 'ba_ref', 'prop_ba_rates', 'occupant_name', 'postcode', 'occupation_state', 'occupation_state_date',
        'occupation_state_reliefs'
Columns: 'Property ref no', 'Full Property Address_x', 'Primary Liable party name_x', 'Account Start date_x',
         'Current Rateable Value_x', 'Property Reference Number_x', 'Full Property Address_y',
         'Current Property Exemption Code', 'Current Prop Exemption Start Date', 'Primary Liable party name_y',
         'Current Rateable Value_y', 'Property Reference Number_y', 'Primary Liable party name',
         'Full Property Address', 'Current Relief Type', 'Account Start date_y', 'Current Relief Award Start Date',
         'Current Rateable Value'

This is not yet ideal. May need a bespoke dataset for each, but this is a start.
"""


class TestAction:
    """TEST IN ALPHABETICAL ORDER - EXCEPT FOR CATEGORY ASSIGN!"""

    def test_calculate(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "CALCULATE > 'prop_ba_rates' < [+ 'Current Rateable Value_x', - 'Current Rateable Value_y', + 'Current Rateable Value']"
        assert _test_script_portsmouth(DIRECTORY, script)

    def test_categorise(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        scripts = [
            "CATEGORISE > 'occupation_state' < [+ 'Current Property Exemption Code', + 'Current Relief Type']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state'::False < 'Current Property Exemption Code'::['EPRN', 'EPRI', 'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state'::False < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
            "CATEGORISE > 'occupation_state_reliefs' < [+ 'Current Property Exemption Code', + 'Current Relief Type']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'small_business' < 'Current Relief Type'::['Small Business Relief England', 'Sbre Extension For 12 Months', 'Supporting Small Business Relief']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'enterprise_zone' < 'Current Property Exemption Code'::['INDUSTRIAL']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'vacancy' < 'Current Property Exemption Code'::['EPRN', 'EPRI', 'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'vacancy' < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'retail' < 'Current Relief Type'::['Retail Discount']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'exempt' < 'Current Property Exemption Code'::['C', 'LOW RV', 'LAND']",
            "ASSIGN_CATEGORY_UNIQUES > 'occupation_state_reliefs'::'other' < 'Current Relief Type'::['Sports Club (Registered CASC)', 'Mandatory']",
        ]
        assert _test_script_portsmouth(DIRECTORY, scripts)

    def test_deblank(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "DEBLANK"
        assert _test_script_world_bank(DIRECTORY, script)

    def test_dedupe(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "DEDUPE"
        assert _test_script_world_bank(DIRECTORY, script)

    def test_delete_columns(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "DELETE_COLUMNS > ['1960.0', '1961.0', '1962.0']"
        assert _test_script_world_bank(DIRECTORY, script, rebase=True)

    def test_delete_rows(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = f"DELETE_ROWS < {[int(i) for i in np.arange(144, 250)]}"
        assert _test_script_world_bank(DIRECTORY, script, rebase=True)

    def test_filter_after(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "FILTER_AFTER > 'occupation_state_date'::'2010-01-01'"
        assert _test_script_portsmouth(DIRECTORY, script, test_filter=True)

    def test_filter_before(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "FILTER_BEFORE > 'occupation_state_date'::'2018-01-01'"
        assert _test_script_portsmouth(DIRECTORY, script, test_filter=True)

    def test_filter_latest(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "FILTER_LATEST > 'occupation_state_date' < 'ba_ref'"
        assert _test_script_portsmouth(DIRECTORY, script, test_filter=True)

    def test_join(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "JOIN > 'indicator_name' < ['Country Code', 'Indicator Name', 'Indicator Code']"
        assert _test_script_world_bank(DIRECTORY, script, rebase=True)

    def test_merge(self, tmp_path):
        """Portsmouth ratepayer data in multiple spreadsheets. Demonstrating create method, add date,
        actions and perform a merge, plus filter the final result."""
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        SCHEMA_NAME = "/data/test_schema.json"
        SCHEMA_SOURCE = SOURCE_DIRECTORY + SCHEMA_NAME
        SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
        INPUT_DATA = [
            SOURCE_DIRECTORY + "/data/raw_E06000044_014_0.XLSX",
            SOURCE_DIRECTORY + "/data/raw_E06000044_014_1.XLSX",
            SOURCE_DIRECTORY + "/data/raw_E06000044_014_2.XLSX",
        ]
        method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
        method.set({"name": "test_method"})
        input_data = [{"path": d} for d in INPUT_DATA]
        method.add_data(source=input_data)
        # reorder
        input_order = [m.uuid.hex for m in method.get.input_data]
        input_order.reverse()
        method.reorder_data(order=input_order)
        # "MERGE < ['key_column'::'source_hex'::'sheet_name', etc.]"
        merge_reference = [
            {"source_hex": method.get.input_data[0].uuid.hex, "key_column": "Property ref no"},
            {"source_hex": method.get.input_data[1].uuid.hex, "key_column": "Property Reference Number"},
            {"source_hex": method.get.input_data[2].uuid.hex, "key_column": "Property Reference Number"},
        ]
        merge_terms = ", ".join([f"'{m['key_column']}'::'{m['source_hex']}'" for m in merge_reference])
        merge_script = f"MERGE < [{merge_terms}]"
        method.merge(merge_script)

    def test_new(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "NEW > 'la_code' < ['E06000044']"
        assert _test_script_portsmouth(DIRECTORY, script)

    def test_order_new(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "ORDER_NEW > 'occupation_state_date' < ['Current Prop Exemption Start Date' + 'Current Prop Exemption Start Date', 'Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date_x' + 'Account Start date_x', 'Account Start date_y' + 'Account Start date_y']"
        assert _test_script_portsmouth(DIRECTORY, script)

    def test_order_old(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "ORDER_OLD > 'occupation_state_date' < ['Current Prop Exemption Start Date' + 'Current Prop Exemption Start Date', 'Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date_x' + 'Account Start date_x', 'Account Start date_y' + 'Account Start date_y']"
        assert _test_script_portsmouth(DIRECTORY, script)

    def test_order(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "ORDER > 'prop_ba_rates' < ['Current Rateable Value_x', 'Current Rateable Value_y', 'Current Rateable Value']"
        assert _test_script_portsmouth(DIRECTORY, script)

    def test_pivot_categories(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "JOIN > 'indicator_name' < ['Country Code', 'Indicator Name', 'Indicator Code']"
        assert _test_script_world_bank(DIRECTORY, script, rebase=True)

    def test_pivot_longer(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = f"PIVOT_LONGER > {[f'{i}.0' for i in np.arange(1960, 2020)]}"
        assert _test_script_world_bank(DIRECTORY, script, rebase=True)

    def test_rebase(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "REBASE < [2]"
        assert _test_script_world_bank(DIRECTORY, script)

    def test_rename_all(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        # Check length of columns in 'working_test_data.xlsx'
        renames = [uuid4().hex for _ in np.arange(16)]
        script = f"RENAME_ALL > {renames}"
        assert _test_script_portsmouth(DIRECTORY, script)

    def test_rename_new(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = f"RENAME_NEW > '{uuid4().hex}'::['Current Rateable Value']"
        assert _test_script_portsmouth(DIRECTORY, script)

    def test_rename(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "RENAME > 'indicator_code' < ['Indicator Code']"
        assert _test_script_world_bank(DIRECTORY, script, rebase=True)

    def test_split(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        script = "SPLIT > ' '::['Country Name']"
        assert _test_script_world_bank(DIRECTORY, script, rebase=True)
