from pathlib import Path

import whyqd
from whyqd.parsers import CoreScript

SCHEMA_NAME = "/data/test_schema.json"
SOURCE_DIRECTORY = str(Path(__file__).resolve().parent)
SCHEMA_SOURCE = SOURCE_DIRECTORY + SCHEMA_NAME
SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
INPUT_DATA = [
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_0.XLSX",
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_1.XLSX",
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_2.XLSX",
]


class TestMethod:
    def test_tutorial(self, tmp_path):
        """Portsmouth ratepayer data in multiple spreadsheets. Demonstrating create method, add date,
        actions and perform a merge, plus filter the final result."""
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(DIRECTORY)
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
        schema_scripts = [
            "NEW > 'la_code' < ['E06000044']",
            "RENAME > 'ba_ref' < ['Property ref no']",
            "ORDER > 'prop_ba_rates' < ['Current Rateable Value_x', 'Current Rateable Value_y', 'Current Rateable Value']",
            "ORDER > 'occupant_name' < ['Primary Liable party name_x', 'Primary Liable party name_y', 'Primary Liable party name']",
            "ORDER > 'postcode' < ['Full Property Address_x', 'Full Property Address_y', 'Full Property Address']",
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
            "ORDER_NEW > 'occupation_state_date' < ['Current Prop Exemption Start Date' + 'Current Prop Exemption Start Date', 'Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date_x' + 'Account Start date_x', 'Account Start date_y' + 'Account Start date_y']",
        ]
        source_data = method.get.working_data
        method.add_actions(schema_scripts, source_data.uuid.hex)
        filter_script = "FILTER_AFTER > 'occupation_state_date'::'2010-01-01'"
        method.add_actions(filter_script, source_data.uuid.hex)
        method.build()
        method.validate()
