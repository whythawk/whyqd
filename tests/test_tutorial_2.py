from pathlib import Path

import whyqd as qd
from whyqd.parsers import CoreParser

SOURCE_DIRECTORY = Path(__file__).resolve().parent / "data"
SOURCE_DATA = SOURCE_DIRECTORY / "working_test_world_bank_data.xlsx"
MIMETYPE = "xlsx"


class TestTutorialPopulation:
    def test_tutorial_urban_population(self, tmp_path):
        """World Bank urban population time-series, in wide format. Demonstrate define a schema,
        create a method, import data, perform actions and generate a schema-compliant output.
        From https://databank.worldbank.org/reports.aspx?source=2&type=metadata&series=SP.URB.TOTL"""
        DIRECTORY = tmp_path
        CoreParser().check_path(directory=DIRECTORY)
        # 1. Import a data source and derive a source schema
        datasource = qd.DataSourceDefinition()
        # There are three sheets:
        # - Data, header row + 3
        # - Metadata - Countries
        # - Metadata - Indicators
        # We're only going to use the first
        datasource.derive_model(source=SOURCE_DATA, mimetype=MIMETYPE, header=[3, 0, 0])
        schema_source = qd.SchemaDefinition()
        schema_source.derive_model(data=datasource.get[0])
        # 2. Create a destination schema
        schema: qd.models.SchemaModel = {
            "name": "urban_population",
            "title": "Urban population",
            "description": "Urban population refers to people living in urban areas as defined by national statistical offices. It is calculated using World Bank population estimates and urban ratios from the United Nations World Urbanization Prospects. Aggregation of urban and rural population may not add up to total population because of different country coverages.",
        }
        fields: list[qd.models.FieldModel] = [
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
        schema_destination = qd.SchemaDefinition()
        schema_destination.set(schema=schema)
        schema_destination.fields.add_multi(terms=fields)
        # 3. Define a Crosswalk
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(schema_source=schema_source, schema_destination=schema_destination)
        # Create the crosswalk
        schema_scripts = [
            "DEBLANK",
            "DEDUPE",
            "DELETE_ROWS < [0, 1, 2, 3]",
            f"PIVOT_LONGER > ['year', 'values'] < {datasource.model[0].names[4:]}",
            "RENAME > 'indicator_code' < ['Indicator Code']",
            "RENAME > 'indicator_name' < ['Indicator Name']",
            "RENAME > 'country_code' < ['Country Code']",
            "RENAME > 'country_name' < ['Country Name']",
        ]
        crosswalk.actions.add_multi(terms=schema_scripts)
        # 4. Transform a data source
        transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=datasource.get[0])
        transform.process()
        transform.save(directory=DIRECTORY)
        # 5. Validate a data source
        DESTINATION_DATA = DIRECTORY / transform.model.dataDestination.name
        DESTINATION_MIMETYPE = "parquet"
        TRANSFORM = DIRECTORY / f"{transform.model.name}.transform"
        valiform = qd.TransformDefinition()
        valiform.validate(
            transform=TRANSFORM, data_destination=DESTINATION_DATA, mimetype_destination=DESTINATION_MIMETYPE
        )
