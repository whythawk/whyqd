from pathlib import Path
import numpy as np

import whyqd as qd
from whyqd.parsers import CoreParser

SOURCE_DIRECTORY = Path(__file__).resolve().parent / "data"
SOURCE_DATA = SOURCE_DIRECTORY / "HDR-2007-2008-Table-03.xlsx"
MIMETYPE = "xlsx"


class TestTutorialCthulhu:
    def test_tutorial_cthulhu(self, tmp_path):
        """World Bank Human Development Report 2007 - 2008 in Cthulhu format. Demonstrate define a schema,
        create a method, import data, perform actions and generate a schema-compliant output.
        Copies at: https://github.com/whythawk/data-wrangling-and-validation/tree/master/data/lesson-spreadsheet"""
        DIRECTORY = tmp_path
        CoreParser().check_path(directory=DIRECTORY)
        ##################################### FIRST CROSSWALK #####################################
        # 1. Import a data source and derive a source schema
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=SOURCE_DATA, mimetype=MIMETYPE, header=None)
        schema_source = qd.SchemaDefinition()
        schema_source.derive_model(data=datasource.get)
        # 2. Create an interim schema
        NEW_COLUMNS = [
            "HDI rank",
            "Country",
            "Human poverty index (HPI-1) - Rank;;2008",
            "Reference 1",
            "Human poverty index (HPI-1) - Value (%);;2008",
            "Probability at birth of not surviving to age 40 (% of cohort);;2000-05",
            "Reference 2",
            "Adult illiteracy rate (% aged 15 and older);;1995-2005",
            "Reference 3",
            "Population not using an improved water source (%);;2004",
            "Reference 4",
            "Children under weight for age (% under age 5);;1996-2005",
            "Reference 5",
            "Population below income poverty line (%) - $1 a day;;1990-2005",
            "Reference 6",
            "Population below income poverty line (%) - $2 a day;;1990-2005",
            "Reference 7",
            "Population below income poverty line (%) - National poverty line;;1990-2004",
            "Reference 8",
            "HPI-1 rank minus income poverty rank;;2008",
            "HDI Category",
        ]
        schema: qd.models.SchemaModel = {
            "name": "human-development-report-interim",
            "title": "UN Human Development Report 2007 - 2008",
            "description": """
                In 1990 the first Human Development Report introduced a new approach for
                advancing human wellbeing. Human development – or the human development approach - is about
                expanding the richness of human life, rather than simply the richness of the economy in which
                human beings live. It is an approach that is focused on people and their opportunities and choices.""",
        }
        fields: list[qd.models.FieldModel] = [{"name": c, "type": "string"} for c in NEW_COLUMNS]
        schema_interim = qd.SchemaDefinition()
        schema_interim.set(schema=schema)
        schema_interim.fields.add_multi(terms=fields)
        # 3. Define a Crosswalk
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(schema_source=schema_source, schema_destination=schema_interim)
        # Create the crosswalk
        schema_scripts = [
            f"DELETE_ROWS < {list(range(15)) + list(np.arange(144, schema_source.get.index))}",
            "PIVOT_CATEGORIES > 'HDI Category' < 'column_0'::[15, 45, 121]",
        ]
        indices = [0, 1, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
        for i, j in enumerate(indices):
            source_field = schema_source.fields.get_all()[j]
            interim_field = schema_interim.fields.get_all()[i]
            schema_scripts.append(f"RENAME > '{interim_field.name}' < ['{source_field.name}']")
        crosswalk.actions.add_multi(terms=schema_scripts)
        # 4. Transform an interim data source
        transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=datasource.get)
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
        ##################################### SECOND CROSSWALK #####################################
        # 6. Create a destination schema
        schema: qd.models.SchemaModel = {
            "name": "human-development-report",
            "title": "UN Human Development Report 2007 - 2008",
            "description": """
                In 1990 the first Human Development Report introduced a new approach for
                advancing human wellbeing. Human development – or the human development approach - is about
                expanding the richness of human life, rather than simply the richness of the economy in which
                human beings live. It is an approach that is focused on people and their opportunities and choices.""",
        }
        fields: list[qd.models.FieldModel] = [
            {
                "name": "year",
                "title": "Year",
                "type": "string",
                "description": "Year of release.",
            },
            {
                "name": "country_name",
                "title": "Country Name",
                "type": "string",
                "description": "Official country names.",
                # "constraints": {"required": True},
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
                # "constraints": {"required": True},
            },
            {
                "name": "reference",
                "title": "Reference",
                "type": "string",
                "description": "Reference to data source.",
            },
        ]
        schema_destination = qd.SchemaDefinition()
        schema_destination.set(schema=schema)
        schema_destination.fields.add_multi(terms=fields)
        # 7. Define a Crosswalk
        # Ensure that the data indices line up
        schema_interim.get.index = transform.get.dataDestination.index
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(schema_source=schema_interim, schema_destination=schema_destination)
        # Create the crosswalk
        reference_columns = [c.name for c in schema_interim.fields.get_all() if c.name.startswith("Reference")]
        schema_scripts = [
            f"UNITE > 'reference' < {reference_columns}",
            "RENAME > 'country_name' < ['Country']",
            "PIVOT_LONGER > ['indicator_name', 'values'] < ['HDI rank', 'HDI Category', 'Human poverty index (HPI-1) - Rank;;2008', 'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Population not using an improved water source (%);;2004', 'Children under weight for age (% under age 5);;1996-2005', 'Population below income poverty line (%) - $1 a day;;1990-2005', 'Population below income poverty line (%) - $2 a day;;1990-2005', 'Population below income poverty line (%) - National poverty line;;1990-2004', 'HPI-1 rank minus income poverty rank;;2008']",
            "SEPARATE > ['indicator_name', 'year'] < ';;'::['indicator_name']",
            "DEBLANK",
            "DEDUPE",
        ]
        crosswalk.actions.add_multi(terms=schema_scripts)
        # 8. Transform an interim data source
        transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=transform.get.dataDestination)
        transform.process()
        transform.save(directory=DIRECTORY)
        # 9. Validate a data source
        DESTINATION_DATA = DIRECTORY / transform.model.dataDestination.name
        DESTINATION_MIMETYPE = "parquet"
        TRANSFORM = DIRECTORY / f"{transform.model.name}.transform"
        valiform = qd.TransformDefinition()
        valiform.validate(
            transform=TRANSFORM, data_destination=DESTINATION_DATA, mimetype_destination=DESTINATION_MIMETYPE
        )
