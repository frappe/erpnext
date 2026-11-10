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

	def test_dimensions_and_weight_must_be_positive(self):
		values = {"length": 20, "width": 10, "height": 10, "weight": 1}
		for fieldname, invalid_value in (("length", -20), ("width", 0), ("height", 0), ("weight", 0)):
			template = frappe.get_doc(
				{
					"doctype": "Shipment Parcel Template",
					"parcel_template_name": f"_Test Parcel {fieldname}",
					**values,
					fieldname: invalid_value,
				}
			)
			self.assertRaises(frappe.ValidationError, template.insert)
