# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestWarehouseType(ERPNextTestSuite):
	def test_transit_type_cannot_be_deleted(self):
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert()

		frappe.db.set_value("Warehouse", {"warehouse_type": "Transit"}, "warehouse_type", None)
		self.assertRaises(frappe.ValidationError, frappe.delete_doc, "Warehouse Type", "Transit")
		self.assertTrue(frappe.db.exists("Warehouse Type", "Transit"))
