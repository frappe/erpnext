# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils.data import today

from erpnext.tests.utils import ERPNextTestSuite


class TestMaintenanceVisit(ERPNextTestSuite):
	pass


def make_maintenance_visit():
	mv = frappe.new_doc("Maintenance Visit")
	mv.company = "_Test Company"
	mv.customer = "_Test Customer"
	mv.mntc_date = today()
	mv.completion_status = "Partially Completed"

	sales_person = make_sales_person("Dwight Schrute")

	mv.append(
		"purposes",
		{
			"item_code": "_Test Item",
			"sales_person": "Sales Team",
			"description": "Test Item",
			"work_done": "Test Work Done",
			"service_person": sales_person.name,
		},
	)
	mv.insert(ignore_permissions=True)

	return mv


def make_sales_person(name):
	if frappe.db.exists("Sales Person", name):
		return frappe.get_doc("Sales Person", name)

	sales_person = frappe.get_doc({"doctype": "Sales Person", "sales_person_name": name})
	sales_person.insert()

	return sales_person
