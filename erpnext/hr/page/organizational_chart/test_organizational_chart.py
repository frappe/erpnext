# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.page.organizational_chart.organizational_chart import get_children


class TestOrganizationalChart(FrappeTestCase):
	def setUp(self):
		self.company = create_company("Test Org Chart").name
		frappe.db.delete("Employee", {"company": self.company})

	def test_get_children(self):
		company = create_company("Test Org Chart").name
		emp1 = make_employee("testemp1@mail.com", company=self.company)
		emp2 = make_employee("testemp2@mail.com", company=self.company, reports_to=emp1)
		emp3 = make_employee("testemp3@mail.com", company=self.company, reports_to=emp1)
		make_employee("testemp4@mail.com", company=self.company, reports_to=emp2)

		# root node
		children = get_children(company=self.company)
		self.assertEqual(len(children), 1)
		self.assertEqual(children[0].id, emp1)
		self.assertEqual(children[0].connections, 3)

		# root's children
		children = get_children(parent=emp1, company=self.company)
		self.assertEqual(len(children), 2)
		self.assertEqual(children[0].id, emp2)
		self.assertEqual(children[0].connections, 1)
		self.assertEqual(children[1].id, emp3)
		self.assertEqual(children[1].connections, 0)


def create_company(name):
	if frappe.db.exists("Company", name):
		return frappe.get_doc("Company", name)

	company = frappe.new_doc("Company")
	company.update(
		{
			"company_name": name,
			"default_currency": "USD",
			"country": "United States",
		}
	)
	return company.insert()
