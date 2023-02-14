from pathlib import Path

import whyqd
from whyqd.transform.parsers import CoreScript

SOURCE_DIRECTORY = str(Path(__file__).resolve().parent)
SOURCE_DATA = SOURCE_DIRECTORY + "/data/working_test_world_bank_data.xlsx"


class TestMethod:
    def test_tutorial(self, tmp_path):
        """World Bank urban population time-series, in wide format. Demonstrate define a schema,
        create a method, import data, perform actions and generate a schema-compliant output.
        From https://databank.worldbank.org/reports.aspx?source=2&type=metadata&series=SP.URB.TOTL"""
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        # DEFINE SCHEMA
        details = {
            "name": "urban_population",
            "title": "Urban population",
            "description": "Urban population refers to people living in urban areas as defined by national statistical offices. It is calculated using World Bank population estimates and urban ratios from the United Nations World Urbanization Prospects. Aggregation of urban and rural population may not add up to total population because of different country coverages.",
        }
        schema = whyqd.Schema()
        schema.set(schema=details)
        fields = [
            {
                "name": "indicator_code",
                "title": "Indicator Code",
                "type": "string",
                "description": "World Bank code reference for Indicator Name.",
                "constraints": {"required": True},
            },
            {
                "name": "country_name",
                "title": "Country Name",
                "type": "string",
                "description": "Official country names.",
                "constraints": {"required": True},
            },
            {
                "name": "country_code",
                "title": "Country Code",
                "type": "string",
                "description": "UN ISO 3-letter country code.",
                "constraints": {"required": True},
            },
            {
                "name": "indicator_name",
                "title": "Indicator Name",
                "type": "string",
                "description": "Indicator described in the data series.",
                "constraints": {"required": True},
            },
            {
                "name": "year",
                "title": "Year",
                "type": "year",
                "description": "Year of release.",
                "constraints": {"required": True},
            },
            {
                "name": "values",
                "title": "Values",
                "type": "number",
                "description": "Value for the Year and Indicator Name.",
                "constraints": {"required": True},
            },
        ]
        for field in fields:
            schema.add_field(field=field)
        schema.save(directory=DIRECTORY)
        # CREATE METHOD
        SCHEMA_SOURCE = DIRECTORY + "urban_population.json"
        SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
        method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
        method.set({"name": "urban_population_method"})
        input_data = {"path": SOURCE_DATA}
        method.add_data(source=input_data)
        # Define actions
        schema_scripts = [
            "DEBLANK",
            "DEDUPE",
            "REBASE < [2]",
        ]
        source_data = method.get.input_data[0]
        method.add_actions(actions=schema_scripts, uid=source_data.uuid.hex, sheet_name=source_data.sheet_name)
        # df = method.transform(source_data)
        source_data = method.get.input_data[0]
        source_columns = [c.name for c in source_data.columns]
        schema_scripts = [
            f"PIVOT_LONGER > {source_columns[4:]}",
            "RENAME > 'indicator_code' < ['Indicator Code']",
            "RENAME > 'indicator_name' < ['Indicator Name']",
            "RENAME > 'country_code' < ['Country Code']",
            "RENAME > 'country_name' < ['Country Name']",
            "RENAME > 'year' < ['PIVOT_LONGER_names_idx_4']",
            "RENAME > 'values' < ['PIVOT_LONGER_values_idx_5']",
        ]
        method.add_actions(actions=schema_scripts, uid=source_data.uuid.hex, sheet_name=source_data.sheet_name)
        # Unambiguous deletion so they are not part of the research record
        for unwanted_data in method.get.input_data[1:]:
            method.remove_data(unwanted_data.uuid.hex, sheet_name=unwanted_data.sheet_name)
        method.build()
        assert method.validate()
