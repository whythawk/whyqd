from pathlib import Path

import whyqd as qd
from whyqd.parsers import CoreParser

SOURCE_DIRECTORY = Path(__file__).resolve().parent / "data"
SOURCE_DATA = SOURCE_DIRECTORY / "raw-e07000066-tutorial-4.xlsx"
MIMETYPE = "xlsx"
DESTINATION_MIMETYPE = "csv"
SCHEMA_NAME = "test_schema.json"
SCHEMA_DESTINATION = SOURCE_DIRECTORY / SCHEMA_NAME
CATEGORY_FIELDS = ["MandRlfCd", "DiscRlfCd", "AddRlfCd", "SBRFlag", "ChgType"]
SCRIPTS = [
    "NEW > 'la_code' < ['E07000066']",
    "RENAME > 'ba_ref' < ['PlaceRef']",
    "RENAME > 'occupant_name' < ['FOIName']",
    "RENAME > 'occupation_state_date' < ['LiabStart']",
    "UNITE > 'postcode' < ', '::['PropAddress1','PropAddress2','PropAddress3','PropAddress4','PropAddress5','PropPostCode']",
    "CATEGORISE > 'occupation_state_reliefs'::'exempt' < 'MandRlfCd'::['CASC','EDUC80','MAND80','PCON','POSTO2']",
    "CATEGORISE > 'occupation_state_reliefs'::'discretionary' < 'DiscRlfCd'::['DIS100','DISC10','DISC15','DISC30','DISC40','DISC50','DISCXX','POSTOF']",
    "CATEGORISE > 'occupation_state_reliefs'::'retail' < 'AddRlfCd'::['RETDS3']",
    "CATEGORISE > 'occupation_state_reliefs'::'small_business' < 'SBRFlag'::['yes']",
    "CATEGORISE > 'occupation_state'::False < 'ChgType'::['V']",
    "COLLATE > 'prop_ba_rates' < ['MandRlf', 'DiscRlf', 'AdditionalRlf', ~]"
]


class TestTutorialVariations:
    def test_tutorial_basildon_rates_data_variations(self, tmp_path):
        """Basildon ratepayer data consist of dates in US format, and numbers as currency strings.

        Demonstrating create method, date and number coersions, array collations, and explode."""
        DIRECTORY = tmp_path
        CoreParser().check_path(directory=DIRECTORY)
        # 1. Import a data source and derive a source schema
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=SOURCE_DATA, mimetype=MIMETYPE)
        schema_source = qd.SchemaDefinition()
        schema_source.derive_model(data=datasource.get)
        for field in schema_source.fields.get_all():
            if field.name in ["LiabStart"]:
                field.dtype = "usdate"
            if field.name in ["MandRlf", "DiscRlf", "AdditionalRlf"]:
                field.dtype = "number"
        for cat_field in CATEGORY_FIELDS:
            if cat_field in datasource.get_data().columns:
                schema_source.fields.set_categories(name=cat_field, terms=datasource.get_data())
        # 2. Import and modify a destination schema
        schema_destination = qd.SchemaDefinition()
        schema_destination.set(schema=SCHEMA_DESTINATION)
        for field in schema_destination.fields.get_all():
            if field.name in ["occupation_state_reliefs", "prop_ba_rates"]:
                field.dtype = "array"
        # 3. Define a Crosswalk
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(schema_source=schema_source, schema_destination=schema_destination)
        crosswalk.actions.add_multi(terms=SCRIPTS)
        crosswalk.save(directory=DIRECTORY)
        # 4. Transform a data source
        transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=datasource.get)
        transform.process()
        transform.save(directory=DIRECTORY, mimetype=DESTINATION_MIMETYPE)
        # 5. Validate a data source
        DESTINATION_DATA = DIRECTORY / transform.model.dataDestination.name
        TRANSFORM = DIRECTORY / f"{transform.model.name}.transform"
        valiform = qd.TransformDefinition()
        valiform.validate(
            transform=TRANSFORM, data_destination=DESTINATION_DATA, mimetype_destination=DESTINATION_MIMETYPE
        )
        # 6. Explode the array data columns
        df = transform.data.copy()
        df = df.explode(["occupation_state_reliefs", "prop_ba_rates"])
        df.dropna(subset=["occupation_state_reliefs", "prop_ba_rates"], inplace=True)
        df.drop_duplicates(inplace=True)
        assert len(df) == 1127
