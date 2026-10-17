# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestShipmentParcelTemplate(ERPNextTestSuite):
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
