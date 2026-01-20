# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.tests import IntegrationTestCase


class TestPriceList(IntegrationTestCase):
	pass


def create_price_list_for_default_check(self, price_list_name, currency="INR", is_default=0):
	price_list = frappe.get_doc(
		{
			"doctype": "Price List",
			"price_list_name": price_list_name,
			"currency": currency,
			"buying": 1,
			"is_default": is_default,
		}
	)
	price_list.insert()
	return price_list
