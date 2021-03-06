from pathlib import Path
import os

import whyqd as _w
from whyqd.core import common as _c

method_name = "/data/test_method.json"
schema_name = "/data/test_schema.json"
DIRECTORY = str(Path(__file__).resolve().parent)
METHOD_SOURCE = DIRECTORY + method_name
SCHEMA_SOURCE = DIRECTORY + schema_name
METHOD = _c.load_json(METHOD_SOURCE)
SCHEMA = _c.load_json(SCHEMA_SOURCE)
INPUT_DATA = [DIRECTORY + "/data/raw_E06000044_014_0.XLSX",
			  DIRECTORY + "/data/raw_E06000044_014_1.XLSX",
			  DIRECTORY + "/data/raw_E06000044_014_2.XLSX"]

class TestMethod:

	def test_create(self, tmp_path):
		DIRECTORY = str(tmp_path) + "/"
		_c.check_path(DIRECTORY)
		method = _w.Method(SCHEMA_SOURCE, directory=DIRECTORY, input_data=INPUT_DATA)
		method.set_details(name="test_method")
		method.save()
		test_source = DIRECTORY + "test_method.json"
		method = _w.Method(test_source, directory=DIRECTORY)
		# Reversed
		assert METHOD["input_data"][2]["checksum"] == method.input_data[0]["checksum"]
		assert METHOD["input_data"][1]["checksum"] == method.input_data[1]["checksum"]
		assert METHOD["input_data"][0]["checksum"] == method.input_data[2]["checksum"]

	def test_method(self, tmp_path):
		DIRECTORY = str(tmp_path) + "/"
		_c.check_path(DIRECTORY)
		# Create a test method
		method = _w.Method(SCHEMA_SOURCE, directory=DIRECTORY, input_data=INPUT_DATA)
		method.set_details(name="test_method")
		# Merge input data
		oak = [
			{
				"id": method.input_data[2]["id"],
				"key": "Property ref no"
			},
			{
				"id": method.input_data[1]["id"],
				"key": "Property Reference Number"
			},
			{
				"id": method.input_data[0]["id"],
				"key": "Property Reference Number"
			}
		]
		method.merge(order_and_key=oak)
		method.save(overwrite=True)
		# Test merge
		test_source = DIRECTORY + "test_method.json"
		method = _w.Method(test_source, directory=DIRECTORY)
		assert METHOD["working_data"]["checksum"] == method.working_data["checksum"]
		assert method.validate_merge
		# Create structure
		structure = {
			"la_code": ["NEW", "E06000044"],
			"ba_ref": ["RENAME", "Property ref no"],
			"prop_ba_rates": ["ORDER", "Current Rateable Value_x", "Current Rateable Value_y", "Current Rateable Value"],
			"occupant_name": ["ORDER", "Primary Liable party name_x", "Primary Liable party name_y", "Primary Liable party name"],
			"postcode": ["ORDER", "Full Property Address_x", "Full Property Address_y", "Full Property Address"],
			"occupation_state": ["CATEGORISE",
								 "+", 'Current Property Exemption Code',
								 "+", "Current Relief Type"],
			"occupation_state_date": ["ORDER_NEW",
									  "Current Prop Exemption Start Date", "+", "Current Prop Exemption Start Date",
									  "Current Relief Award Start Date", "+", "Current Relief Award Start Date",
									  "Account Start date_x", "+", "Account Start date_x",
									  "Account Start date_y", "+", "Account Start date_y"],
			"occupation_state_reliefs": ["CATEGORISE",
										 "+", 'Current Property Exemption Code',
										 "+", "Current Relief Type"]
		}
		method.set_structure(**structure)
		method.save(overwrite=True)
		# Test structure
		test_source = DIRECTORY + "test_method.json"
		method = _w.Method(test_source, directory=DIRECTORY)
		method.validate_structure
		# Create category
		category = {
			"occupation_state_reliefs": {
				"small_business": [
					'Small Business Relief England::Current Relief Type',
					'Sbre Extension For 12 Months::Current Relief Type',
					'Supporting Small Business Relief::Current Relief Type'
					],
				"enterprise_zone": ['INDUSTRIAL::Current Property Exemption Code'],
				"vacancy": [
					'EPRN::Current Property Exemption Code',
					'EPRI::Current Property Exemption Code',
					'VOID::Current Property Exemption Code',
					'Empty Property Rate Non-Industrial::Current Relief Type',
					'Empty Property Rate Industrial::Current Relief Type',
					'EPCH::Current Property Exemption Code',
					'LIQUIDATE::Current Property Exemption Code',
					'DECEASED::Current Property Exemption Code',
					'PROHIBITED::Current Property Exemption Code',
					'BANKRUPT::Current Property Exemption Code',
					'Empty Property Rate Charitable::Current Relief Type'
					],
				"retail": ['Retail Discount::Current Relief Type'],
				"exempt": [
					'C::Current Property Exemption Code',
					'LOW RV::Current Property Exemption Code',
					'LAND::Current Property Exemption Code'
					],
				"other": [
					'Sports Club (Registered CASC)::Current Relief Type',
					'Mandatory::Current Relief Type'
					]
				},
			"occupation_state": {
				"false": [
					'EPRN::Current Property Exemption Code',
					'EPRI::Current Property Exemption Code',
					'VOID::Current Property Exemption Code',
					'Empty Property Rate Non-Industrial::Current Relief Type',
					'Empty Property Rate Industrial::Current Relief Type',
					'EPCH::Current Property Exemption Code',
					'LIQUIDATE::Current Property Exemption Code',
					'DECEASED::Current Property Exemption Code',
					'PROHIBITED::Current Property Exemption Code',
					'BANKRUPT::Current Property Exemption Code',
					'Empty Property Rate Charitable::Current Relief Type'
					]
				}
			}
		method.set_category(**category)
		method.save(overwrite=True)
		# Test Category
		test_source = DIRECTORY + "test_method.json"
		method = _w.Method(test_source, directory=DIRECTORY)
		test_category = {}
		for field_name in method.all_field_names:
			if method.field(field_name).get("category"):
				test_category[field_name] = method.category(field_name).get("assigned")
		assert category.keys() == test_category.keys()
		for key in category:
			assert category[key].keys() == test_category[key].keys()
			for k in category[key]:
				assert set(category[key][k]) == set(test_category[key][k])
		assert method.validate_category
		# Create Filter
		method.set_filter("occupation_state_date", "AFTER", "2010-01-01", "ba_ref")
		method.save(overwrite=True)
		# Test Filter
		test_source = DIRECTORY + "test_method.json"
		method = _w.Method(test_source, directory=DIRECTORY)
		assert method.validate_filter
		# Run Transform
		method.transform(overwrite_output=True)
		method.save(overwrite=True)
		# Test Transform
		method = _w.Method(test_source, directory=DIRECTORY)
		assert method.validate_transform