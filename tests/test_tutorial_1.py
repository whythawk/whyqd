from pathlib import Path
import modin.pandas as pd

import whyqd as qd
from whyqd.parsers import CoreParser, DataSourceParser

reader = DataSourceParser()

SOURCE_DIRECTORY = Path(__file__).resolve().parent / "data"
SOURCE_DATA = SOURCE_DIRECTORY / "raw_multi_E06000044_014.xlsx"
MIMETYPE = "xlsx"
DESTINATION_MIMETYPE = "parquet"
SCHEMA_NAME = "test_schema.json"
SCHEMA_DESTINATION = SOURCE_DIRECTORY / SCHEMA_NAME
CATEGORY_FIELDS = ["Current Relief Type", "Current Property Exemption Code"]

SCHEMA_SCRIPTS = {
    "Report1": [
        "NEW > 'la_code' < ['E06000044']",
        "RENAME > 'ba_ref' < ['Property Reference Number']",
        "RENAME > 'prop_ba_rates' < ['Current Rateable Value']",
        "RENAME > 'occupant_name' < ['Primary Liable party name']",
        "RENAME > 'postcode' < ['Full Property Address']",
        "CATEGORISE > 'occupation_state'::False < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
        "CATEGORISE > 'occupation_state_reliefs'::'small_business' < 'Current Relief Type'::['Small Business Relief England', 'Sbre Extension For 12 Months', 'Supporting Small Business Relief']",
        "CATEGORISE > 'occupation_state_reliefs'::'vacancy' < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
        "CATEGORISE > 'occupation_state_reliefs'::'retail' < 'Current Relief Type'::['Retail Discount']",
        "CATEGORISE > 'occupation_state_reliefs'::'other' < 'Current Relief Type'::['Sports Club (Registered CASC)', 'Mandatory']",
        "SELECT_NEWEST > 'occupation_state_date' < ['Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date' + 'Account Start date']",
    ],
    "Report2": [
        "NEW > 'la_code' < ['E06000044']",
        "RENAME > 'ba_ref' < ['Property Reference Number']",
        "RENAME > 'prop_ba_rates' < ['Current Rateable Value']",
        "RENAME > 'occupant_name' < ['Primary Liable party name']",
        "RENAME > 'postcode' < ['Full Property Address']",
        "CATEGORISE > 'occupation_state'::False < 'Current Property Exemption Code'::['EPRN', 'EPRI', 'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']",
        "CATEGORISE > 'occupation_state_reliefs'::'enterprise_zone' < 'Current Property Exemption Code'::['INDUSTRIAL']",
        "CATEGORISE > 'occupation_state_reliefs'::'vacancy' < 'Current Property Exemption Code'::['EPRN', 'EPRI', 'VOID', 'EPCH', 'LIQUIDATE', 'DECEASED', 'PROHIBITED', 'BANKRUPT']",
        "CATEGORISE > 'occupation_state_reliefs'::'exempt' < 'Current Property Exemption Code'::['C', 'LOW RV', 'LAND']",
        "RENAME > 'occupation_state_date' < ['Current Prop Exemption Start Date']",
    ],
    "Report3": [
        "NEW > 'la_code' < ['E06000044']",
        "RENAME > 'ba_ref' < ['Property ref no']",
        "RENAME > 'prop_ba_rates' < ['Current Rateable Value']",
        "RENAME > 'occupant_name' < ['Primary Liable party name']",
        "RENAME > 'postcode' < ['Full Property Address']",
        "SELECT_NEWEST > 'occupation_state_date' < ['Account Start date' + 'Account Start date']",
    ],
}


class TestTutorialRates:
    def test_tutorial_portsmouth_rates_data(self, tmp_path):
        """Portsmouth ratepayer data in multiple sheets. Demonstrating create method, add date,
        actions and perform a merge, plus filter the final result."""
        DIRECTORY = tmp_path
        CoreParser().check_path(directory=DIRECTORY)
        # 1. Import a destination schema
        schema_destination = qd.SchemaDefinition()
        schema_destination.set(schema=SCHEMA_DESTINATION)
        # 2. Import a data source and derive a source schema
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=SOURCE_DATA, mimetype=MIMETYPE)
        assert len(datasource.get) == 3
        # Looping
        chunks = []
        for ds in datasource.get:
            schema_source = qd.SchemaDefinition()
            schema_source.derive_model(data=ds)
            field_names = [c.name for c in ds.columns]
            if not set(CATEGORY_FIELDS).isdisjoint(field_names):
                df = reader.get(source=ds)
                for cat_field in CATEGORY_FIELDS:
                    if cat_field in df.columns:
                        schema_source.fields.set_categories(name=cat_field, terms=df)
            # 3. Define a Crosswalk
            crosswalk = qd.CrosswalkDefinition()
            crosswalk.set(schema_source=schema_source, schema_destination=schema_destination)
            crosswalk.actions.add_multi(terms=SCHEMA_SCRIPTS[ds.sheet_name])
            # 4. Transform a data source
            transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=ds)
            transform.process()
            transform.save(directory=DIRECTORY)
            # 5. Validate a data source
            DESTINATION_DATA = DIRECTORY / transform.model.dataDestination.name
            TRANSFORM = DIRECTORY / f"{transform.model.name}.transform"
            valiform = qd.TransformDefinition()
            valiform.validate(
                transform=TRANSFORM, data_destination=DESTINATION_DATA, mimetype_destination=DESTINATION_MIMETYPE
            )
            # Gather chunks in May
            chunks.append(transform.data)
        df = pd.concat(chunks)
