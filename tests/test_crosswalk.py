from pathlib import Path

import whyqd as qd
from whyqd.parsers import CoreParser

CORE = CoreParser()
SOURCE_DIRECTORY = Path(__file__).resolve().parent / "data"
SOURCE_SCHEMA_PATH = SOURCE_DIRECTORY / "test_source_schema.schema"
CROSSWALK_PATH = SOURCE_DIRECTORY / "test_crosswalk.crosswalk"
CROSSWALK = CORE.load_json(source=CROSSWALK_PATH)
CROSSWALK.pop("version", None)
CROSSWALK["schemaSource"].pop("version", None)
CROSSWALK["schemaDestination"].pop("version", None)
DESTINATION_SCHEMA_PATH = SOURCE_DIRECTORY / "test_schema.schema"
SCHEMA_SOURCE = qd.SchemaDefinition(source=SOURCE_SCHEMA_PATH)
SCHEMA_DESTINATION = qd.SchemaDefinition(source=DESTINATION_SCHEMA_PATH)
SCHEMA_SCRIPTS = [
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
]
NEW_SCRIPT = "SELECT > 'occupation_state_date' < ['Account Start date', 'Current Relief Award Start Date']"


class TestCrosswalk:
    def test_create_validate(self, tmp_path):
        DIRECTORY = tmp_path
        CORE.check_path(directory=DIRECTORY)
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(
            crosswalk={"name": "test_crosswalk"}, schema_source=SCHEMA_SOURCE, schema_destination=SCHEMA_DESTINATION
        )
        crosswalk.actions.add_multi(terms=SCHEMA_SCRIPTS)
        crosswalk.save(directory=DIRECTORY, hide_uuid=True)
        # Validate
        c = crosswalk.exclude_uuid(model=crosswalk.get)
        c.pop("version", None)
        c["schemaSource"].pop("version", None)
        c["schemaDestination"].pop("version", None)
        assert c == CROSSWALK

    def test_add_remove_update(self):
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(
            crosswalk={"name": "test_crosswalk"}, schema_source=SCHEMA_SOURCE, schema_destination=SCHEMA_DESTINATION
        )
        # Add
        for script in SCHEMA_SCRIPTS:
            crosswalk.actions.add(term=script)
        # Update
        script = crosswalk.actions.get_all()[-1]
        script.script = NEW_SCRIPT
        crosswalk.actions.update(term=script)
        # Remove
        script = crosswalk.actions.get_all()[0]
        script = crosswalk.actions.remove(name=script.uuid)
        # All there
        cw = {cw.script for cw in crosswalk.actions.get_all()}
        CW = set(SCHEMA_SCRIPTS)
        assert cw - CW == {NEW_SCRIPT}
        assert CW - cw == set([SCHEMA_SCRIPTS[0], SCHEMA_SCRIPTS[-1]])
