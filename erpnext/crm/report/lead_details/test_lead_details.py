# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.crm.report.lead_details.lead_details import get_data

test_dependencies = ["Company", "Territory"]


class TestLeadDetailsReport(FrappeTestCase):
	def test_territory_group_includes_child_territories(self):
		lead = make_lead(territory="_Test Territory India")

		names = [row.name for row in get_data(make_filters(territory="All Territories"))]
		self.assertIn(lead.name, names)


def make_lead(**fields):
	return frappe.get_doc(
		{"doctype": "Lead", "lead_name": "_Test Lead Details", "company": "_Test Company", **fields}
	).insert()


def make_filters(**filters):
	return frappe._dict(
		company="_Test Company", from_date=add_days(today(), -1), to_date=add_days(today(), 1), **filters
	)
