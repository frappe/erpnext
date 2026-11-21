# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation


class TestWorkstationType(FrappeTestCase):
	def test_type_cost_change_reaches_its_workstations(self):
		workstation_type = create_workstation_type(
			workstation_type="_Test WT Rate Change", hour_rate_labour=500, hour_rate_rent=100
		)
		follows_type = make_workstation(
			workstation_name="_Test WS Rate Follows", workstation_type=workstation_type.name
		)
		own_rate = make_workstation(
			workstation_name="_Test WS Rate Own", workstation_type=workstation_type.name
		)
		own_rate.hour_rate_labour = 650
		own_rate.save()

		workstation_type.hour_rate_labour = 800
		workstation_type.hour_rate_rent = 0
		workstation_type.save()

		self.assertEqual(frappe.db.get_value("Workstation", follows_type.name, "hour_rate"), 800)
		self.assertEqual(frappe.db.get_value("Workstation", own_rate.name, "hour_rate"), 750)


def create_workstation_type(**args):
	args = frappe._dict(args)

	if workstation_type := frappe.db.exists("Workstation Type", args.workstation_type):
		return frappe.get_doc("Workstation Type", workstation_type)
	else:
		doc = frappe.new_doc("Workstation Type")
		doc.update(args)
		doc.insert()
		return doc
