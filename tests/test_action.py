from pathlib import Path
import os

import whyqd as _w
from whyqd.core import common as _c
from whyqd.action import actions, default_actions

working_data = "/data/working_test_data.xlsx"
DIRECTORY = str(Path(__file__).resolve().parent)
DF = _c.get_dataframe(DIRECTORY + working_data, dtype=object)

class TestAction:

    def test_new(self):
        field_name = "test_field"
        structure = [
            {
                "type": "string",
                "value": "E06000044"
            }
        ]
        actn = actions["NEW"]()
        actn.transform(DF.copy(deep=True), field_name, structure)

    def test_rename(self):
        field_name = "test_field"
        structure = [
            {
                "name": "Property ref no",
                "type": "number"
            }
        ]
        actn = actions["RENAME"]()
        actn.transform(DF.copy(deep=True), field_name, structure)

    def test_join(self):
        field_name = "test_field"
        structure = [
            {
                "name": "Primary Liable party name_x",
                "type": "string"
            },
            {
                "name": "Primary Liable party name_y",
                "type": "string"
            },
            {
                "name": "Primary Liable party name",
                "type": "string"
            }
        ]
        actn = actions["JOIN"]()
        actn.transform(DF.copy(deep=True), field_name, structure)

    def test_order(self):
        field_name = "test_field"
        structure = [
            {
                "name": "Current Rateable Value_x",
                "type": "number"
            },
            {
                "name": "Current Rateable Value_y",
                "type": "number"
            },
            {
                "name": "Current Rateable Value",
                "type": "number"
            }
        ]
        actn = actions["ORDER"]()
        actn.transform(DF.copy(deep=True), field_name, structure)

    def test_order_by_date(self):
        field_name = "test_field"
        structure = [
            {
                "name": "Current Prop Exemption Start Date",
                "type": "number"
            },
            {
                "name": "+",
                "title": "Links",
                "type": "modifier"
            },
            {
                "name": "Current Prop Exemption Start Date",
                "type": "number"
            },
            {
                "name": "Current Relief Award Start Date",
                "type": "date"
            },
            {
                "name": "+",
                "title": "Links",
                "type": "modifier"
            },
            {
                "name": "Current Relief Award Start Date",
                "type": "date"
            },
            {
                "name": "Account Start date_x",
                "type": "date"
            },
            {
                "name": "+",
                "title": "Links",
                "type": "modifier"
            },
            {
                "name": "Account Start date_x",
                "type": "date"
            },
            {
                "name": "Account Start date_y",
                "type": "date"
            },
            {
                "name": "+",
                "title": "Links",
                "type": "modifier"
            },
            {
                "name": "Account Start date_y",
                "type": "date"
            }
        ]
        actn = actions["ORDER_NEW"]()
        actn.transform(DF.copy(deep=True), field_name, structure)
        actn = actions["ORDER_OLD"]()
        actn.transform(DF.copy(deep=True), field_name, structure) 

    def test_calculate(self):
        field_name = "test_field"
        structure = [
            {
                "name": "+",
                "title": "Add",
                "type": "modifier"
            },
            {
                "name": "Current Rateable Value_x",
                "type": "number"
            },
            {
                "name": "+",
                "title": "Add",
                "type": "modifier"
            },
            {
                "name": "Current Rateable Value_y",
                "type": "number"
            },
            {
                "name": "-",
                "title": "Subtract",
                "type": "modifier"
            },
            {
                "name": "Current Rateable Value",
                "type": "number"
            }
        ]
        actn = actions["CALCULATE"]()
        actn.transform(DF.copy(deep=True), field_name, structure)

    def test_categorise(self):
        field_name = "test_field"
        field_type = "array"
        structure = [
            {
                "name": "+",
                "title": "Uniques",
                "type": "modifier"
            },
            {
                "name": "Current Property Exemption Code",
                "type": "number"
            },
            {
                "name": "+",
                "title": "Uniques",
                "type": "modifier"
            },
            {
                "name": "Current Relief Type",
                "type": "string"
            }
        ]
        category = [
            {
                "category_input": [
                    {
                        "column": "Current Relief Type",
                        "terms": [
                            "Small Business Relief England",
                            "Sbre Extension For 12 Months",
                            "Supporting Small Business Relief"
                        ]
                    }
                ],
                "name": "small_business"
            },
            {
                "category_input": [
                    {
                        "column": "Current Property Exemption Code",
                        "terms": [
                            "INDUSTRIAL"
                        ]
                    }
                ],
                "name": "enterprise_zone"
            },
            {
                "category_input": [
                    {
                        "column": "Current Property Exemption Code",
                        "terms": [
                            "EPRN",
                            "EPRI",
                            "VOID",
                            "EPCH",
                            "LIQUIDATE",
                            "DECEASED",
                            "PROHIBITED",
                            "BANKRUPT"
                        ]
                    },
                    {
                        "column": "Current Relief Type",
                        "terms": [
                            "Empty Property Rate Non-Industrial",
                            "Empty Property Rate Industrial",
                            "Empty Property Rate Charitable"
                        ]
                    }
                ],
                "name": "vacancy"
            },
            {
                "category_input": [
                    {
                        "column": "Current Relief Type",
                        "terms": [
                            "Retail Discount"
                        ]
                    }
                ],
                "name": "retail"
            },
            {
                "category_input": [
                    {
                        "column": "Current Property Exemption Code",
                        "terms": [
                            "C",
                            "LOW RV",
                            "LAND"
                        ]
                    }
                ],
                "name": "exempt"
            },
            {
                "category_input": [
                    {
                        "column": "Current Relief Type",
                        "terms": [
                            "Sports Club (Registered CASC)",
                            "Mandatory"
                        ]
                    }
                ],
                "name": "other"
            }
        ]
        actn = actions["CATEGORISE"]()
        actn.transform(DF.copy(deep=True), field_name, structure,
                       category=category, field_type=field_type)