from pathlib import Path
import os

import whyqd as _w
import whyqd.common as _c

method_name = "/data/test_method.json"
schema_name = "/data/test_schema.json"
METHOD_SOURCE = str(Path(__file__).resolve().parent) + method_name
SCHEMA_SOURCE = str(Path(__file__).resolve().parent) + schema_name
METHOD = _c.load_json(METHOD_SOURCE)
SCHEMA = _c.load_json(SCHEMA_SOURCE)
INPUT_DATA = ["/mnt/c/Users/Turukawa/Documents/GitHub/whyqd/tests/data/raw_E06000044_014_0.XLSX",
			  "/mnt/c/Users/Turukawa/Documents/GitHub/whyqd/tests/data/raw_E06000044_014_1.XLSX",
			  "/mnt/c/Users/Turukawa/Documents/GitHub/whyqd/tests/data/raw_E06000044_014_2.XLSX"]

class TestMethod:

	def test_create(self, tmp_path):
		DIRECTORY = str(tmp_path) + "/"
		_c.check_path(DIRECTORY)
		method = _w.Method(SCHEMA_SOURCE, directory=DIRECTORY, input_data=INPUT_DATA)
		method.set_details(name="test_method")
		method.save()
		test_source = DIRECTORY + "test_method.json"
		method = _w.Method(test_source, directory=DIRECTORY)
		assert METHOD["input_data"][0]["checksum"] == method.input_data[0]["checksum"]
		assert METHOD["input_data"][1]["checksum"] == method.input_data[1]["checksum"]
		assert METHOD["input_data"][2]["checksum"] == method.input_data[2]["checksum"]

	def test_merge(self, tmp_path):
		DIRECTORY = str(tmp_path) + "/"
		_c.check_path(DIRECTORY)
		method = _w.Method(SCHEMA_SOURCE, directory=DIRECTORY, input_data=INPUT_DATA)
		method.set_details(name="test_method")
		oak = [
			{
				"id": method.input_data[0]["id"],
				"key": "Property Reference Number"
			},
			{
				"id": method.input_data[1]["id"],
				"key": "Property Reference Number"
			},
			{
				"id": method.input_data[2]["id"],
				"key": "Property ref no"
			}
		]
		method.merge(order_and_key=oak)
		method.save(overwrite=True)
		test_source = DIRECTORY + "test_method.json"
		method = _w.Method(test_source, directory=DIRECTORY)
		assert METHOD["working_data"]["checksum"] == method.working_data["checksum"]

	def test_structure(self, tmp_path):
		DIRECTORY = str(tmp_path) + "/"
		_c.check_path(DIRECTORY)
		method = _w.Method(SCHEMA_SOURCE, directory=DIRECTORY, input_data=INPUT_DATA)
		method.set_details(name="test_method")
		oak = [
			{
				"id": method.input_data[0]["id"],
				"key": "Property Reference Number"
			},
			{
				"id": method.input_data[1]["id"],
				"key": "Property Reference Number"
			},
			{
				"id": method.input_data[2]["id"],
				"key": "Property ref no"
			}
		]
		method.merge(order_and_key=oak)
		structure = {
			"la_code": ["NEW", "E06000044"],
			"ba_ref": ["ORDER", "Property Reference Number", "Property ref no"],
			"prop_ba_rates": ["ORDER", "Current Rateable Value_x", "Current Rateable Value_y", "Current Rateable Value"],
			"occupant_name": ["ORDER", "Primary Liable party name_x", "Primary Liable party name_y", "Primary Liable party name"],
			"postcode": ["ORDER", "Full Property Address_x", "Full Property Address_y", "Full Property Address"],
			"occupation_state": ["CATEGORISE",
								 "+", "Current Property Exemption Code",
								 "+", "Current Relief Type"],
			"occupation_state_date": ["ORDER_NEW",
									  "Current Prop Exemption Start Date", "+", "Current Prop Exemption Start Date",
									  "Current Relief Award Start Date", "+", "Current Relief Award Start Date",
									  "Account Start date_x", "+", "Account Start date_x",
									  "Account Start date_y", "+", "Account Start date_y"],
			"occupation_state_reliefs": ["CATEGORISE",
										 "+", "Current Property Exemption Code",
										 "+", "Current Relief Type"]

		}
		method.set_structure(**structure)
		method.save(overwrite=True)