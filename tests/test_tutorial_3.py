from pathlib import Path
import numpy as np

import whyqd
from whyqd.transform.parsers import CoreScript

SOURCE_DIRECTORY = str(Path(__file__).resolve().parent)
SOURCE_DATA = SOURCE_DIRECTORY + "/data/HDR-2007-2008-Table-03.xlsx"


class TestMethod:
    def test_tutorial(self, tmp_path):
        """World Bank Human Development Report 2007 - 2008 in Cthulhu format. Demonstrate define a schema,
        create a method, import data, perform actions and generate a schema-compliant output.
        Copies at: https://github.com/whythawk/data-wrangling-and-validation/tree/master/data/lesson-spreadsheet"""
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        # DEFINE SCHEMA
        details = {
            "name": "human-development-report",
            "title": "UN Human Development Report 2007 - 2008",
            "description": """
                In 1990 the first Human Development Report introduced a new approach for
                advancing human wellbeing. Human development – or the human development approach - is about
                expanding the richness of human life, rather than simply the richness of the economy in which
                human beings live. It is an approach that is focused on people and their opportunities and choices.""",
        }
        schema = whyqd.Schema()
        schema.set(schema=details)
        fields = [
            {
                "name": "year",
                "title": "Year",
                "type": "year",
                "description": "Year of release.",
            },
            {
                "name": "country_name",
                "title": "Country Name",
                "type": "string",
                "description": "Official country names.",
                "constraints": {"required": True},
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
                "constraints": {"required": True},
            },
            {
                "name": "reference",
                "title": "Reference",
                "type": "string",
                "description": "Reference to data source.",
            },
        ]
        for field in fields:
            schema.add_field(field=field)
        schema.save(directory=DIRECTORY)
        # CREATE METHOD
        SCHEMA_SOURCE = DIRECTORY + "human-development-report.json"
        SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
        method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
        method.set({"name": "human-development-report-method"})
        input_data = {"path": SOURCE_DATA}
        method.add_data(source=input_data)
        # Define actions
        schema_scripts = [
            "DEBLANK",
            "DEDUPE",
            "REBASE < [11]",
        ]
        source_data = method.get.input_data[0]
        method.add_actions(actions=schema_scripts, uid=source_data.uuid.hex, sheet_name=source_data.sheet_name)
        # Get the index
        source_data = method.get.input_data[0]
        df = method.transform(source_data)
        schema_scripts = [
            f"DELETE_ROWS < {[int(i) for i in np.arange(144, df.index[-1]+1)]}",
            "RENAME_ALL > ['HDI rank', 'Country', 'Human poverty index (HPI-1) - Rank;;2008', 'Reference 1', 'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05', 'Reference 2', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Reference 3', 'Population not using an improved water source (%);;2004', 'Reference 4', 'Children under weight for age (% under age 5);;1996-2005', 'Reference 5', 'Population below income poverty line (%) - $1 a day;;1990-2005', 'Reference 6', 'Population below income poverty line (%) - $2 a day;;1990-2005', 'Reference 7', 'Population below income poverty line (%) - National poverty line;;1990-2004', 'Reference 8', 'HPI-1 rank minus income poverty rank;;2008']",
            "PIVOT_CATEGORIES > ['HDI rank'] < [14,44,120]",
            "RENAME_NEW > 'HDI Category'::['PIVOT_CATEGORIES_idx_20_0']",
            "PIVOT_LONGER > = ['HDI rank', 'HDI Category', 'Human poverty index (HPI-1) - Rank;;2008', 'Human poverty index (HPI-1) - Value (%);;2008', 'Probability at birth of not surviving to age 40 (% of cohort);;2000-05', 'Adult illiteracy rate (% aged 15 and older);;1995-2005', 'Population not using an improved water source (%);;2004', 'Children under weight for age (% under age 5);;1996-2005', 'Population below income poverty line (%) - $1 a day;;1990-2005', 'Population below income poverty line (%) - $2 a day;;1990-2005', 'Population below income poverty line (%) - National poverty line;;1990-2004', 'HPI-1 rank minus income poverty rank;;2008']",
            "SPLIT > ';;'::['PIVOT_LONGER_names_idx_9']",
            "DEBLANK",
            "DEDUPE",
        ]
        method.add_actions(actions=schema_scripts, uid=source_data.uuid.hex, sheet_name=source_data.sheet_name)
        # Get the column list
        reference_columns = [c.name for c in method.get.input_data[0].columns if c.name.startswith("Reference")]
        schema_scripts = [
            f"JOIN > 'reference' < {reference_columns}",
            "RENAME > 'indicator_name' < ['SPLIT_idx_11_0']",
            "RENAME > 'country_name' < ['Country']",
            "RENAME > 'year' < ['SPLIT_idx_12_1']",
            "RENAME > 'values' < ['PIVOT_LONGER_values_idx_10']",
        ]
        method.add_actions(actions=schema_scripts, uid=source_data.uuid.hex, sheet_name=source_data.sheet_name)
        method.build()
        assert method.validate()
