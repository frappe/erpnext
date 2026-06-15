# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchasePartnerType(ERPNextTestSuite):
	def test_purchase_partner_type_creation(self):
		if not frappe.db.exists("Purchase Partner Type", "_Test Purchase Partner Type"):
			ppt = frappe.new_doc("Purchase Partner Type")
			ppt.purchase_partner_type = "_Test Purchase Partner Type"
			ppt.insert(ignore_permissions=True)

		self.assertTrue(frappe.db.exists("Purchase Partner Type", "_Test Purchase Partner Type"))
		frappe.delete_doc("Purchase Partner Type", "_Test Purchase Partner Type", force=True)
