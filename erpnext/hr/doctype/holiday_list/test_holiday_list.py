# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestHolidayList(unittest.TestCase):
 
    def test_holiday_list(self):
        test_make_holiday_list = make_holiday_list()
        test_get_holiday_list = get_holiday_list()
        self.assertEquals(test_make_holiday_list, test_get_holiday_list)

def make_holiday_list():
    holiday_list = frappe.get_doc({
        "doctype": "Holiday List",
        "holiday_list_name": "_Test Holiday List",
        "from_date": "2013-01-01",
        "to_date":"2013-12-31",
        "holidays": [
            {
                "description": "New Year",
                "holiday_date": "2013-01-01"
            },
            {
                "description": "Republic Day",
                "holiday_date": "2013-01-26"
            },
            {
                "description": "Test Holiday",
                "holiday_date": "2013-02-01"
            }
        ]
    })
    holiday_list_exist = frappe.db.exists("Holiday List", "_Test Holiday List")
    if not holiday_list_exist:
    	holiday_list.insert()
    	return holiday_list.holiday_list_name
    else:
    	return holiday_list_exist

def get_holiday_list():
	holiday_list = frappe.db.exists("Holiday List", "_Test Holiday List")
	return holiday_list