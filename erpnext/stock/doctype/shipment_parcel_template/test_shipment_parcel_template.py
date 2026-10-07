# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user

from erpnext.tests.utils import ERPNextTestSuite


class TestShipmentParcelTemplate(ERPNextTestSuite):
	def test_stock_manager_can_load_and_create_template(self):
		user = create_user("test_parcel_template@example.com", "Stock Manager")

		for ptype in ("read", "create", "write"):
			self.assertTrue(frappe.has_permission("Shipment Parcel Template", ptype, user=user.name))
