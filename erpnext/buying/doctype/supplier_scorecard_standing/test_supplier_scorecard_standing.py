# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.buying.doctype.supplier_scorecard_standing.supplier_scorecard_standing import (
	get_scoring_standing,
	get_standings_list,
)
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestSupplierScorecardStanding(ERPNextTestSuite):
	def test_standings_need_read_permission(self):
		standing = frappe.get_doc(
			{"doctype": "Supplier Scorecard Standing", "standing_name": "_Test Standing", "max_grade": 30}
		).insert()
		stock_user = make_fenced_user("scorecard-standing-stock@example.com", ["Stock User"])

		with as_user(stock_user):
			self.assertRaises(frappe.PermissionError, get_scoring_standing, standing.name)
			self.assertRaises(frappe.PermissionError, get_standings_list)
