# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestShareholder(IntegrationTestCase):
	def test_nominee_allocations_must_total_one_hundred_percent(self):
		shareholder = frappe.get_doc(
			{
				"doctype": "Shareholder",
				"legal_name": "Test Nominee Allocation",
				"shareholder_type": "Individual",
				"tax_id_type": "Test Tax ID",
				"tax_id": "TEST-NOMINEE-ALLOCATION",
				"tax_id_country": "India",
				"nominees": [
					{"nominee_name": "Nominee 1", "allocation_percentage": 33.33},
					{"nominee_name": "Nominee 2", "allocation_percentage": 33.33},
					{"nominee_name": "Nominee 3", "allocation_percentage": 33.34},
				],
			}
		).insert()
		shareholder.nominees[2].allocation_percentage = 30
		with self.assertRaisesRegex(frappe.ValidationError, "must total 100"):
			shareholder.save()
