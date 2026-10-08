# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.sales_order.mapper import make_project
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectType(ERPNextTestSuite):
	def test_project_from_sales_order_without_external_project_type(self):
		frappe.db.delete("Project Type", "External")
		project = make_project(make_sales_order().name)
		project.insert()
		self.assertFalse(project.project_type)
