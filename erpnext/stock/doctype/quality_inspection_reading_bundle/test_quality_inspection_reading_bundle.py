# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


def ensure_parameter(name):
	if not frappe.db.exists("Quality Inspection Parameter", name):
		frappe.get_doc({"doctype": "Quality Inspection Parameter", "parameter": name}).insert(
			ignore_permissions=True
		)
	return name


def make_bundle(quantity, unit_results, item_code=None):
	"""unit_results: {unit_no: [status, status, ...]} — one status per parameter row."""
	bundle = frappe.new_doc("Quality Inspection Reading Bundle")
	bundle.item_code = item_code or make_item(properties={"is_stock_item": 1}).name
	bundle.quantity = quantity
	for unit_no, statuses in unit_results.items():
		for index, status in enumerate(statuses):
			bundle.append(
				"entries",
				{
					"unit_no": unit_no,
					"specification": ensure_parameter(f"_Test Bundle Parameter {index}"),
					"status": status,
				},
			)
	bundle.insert(ignore_permissions=True)
	bundle.submit()
	return bundle


class TestQualityInspectionReadingBundle(ERPNextTestSuite):
	def test_unit_is_rejected_if_any_reading_fails(self):
		bundle = make_bundle(
			3,
			{
				1: ["Accepted", "Accepted"],
				2: ["Accepted", "Rejected"],  # one failing reading rejects the unit
				3: ["Accepted", "Accepted"],
			},
		)
		self.assertEqual(bundle.accepted_qty, 2)
		self.assertEqual(bundle.rejected_qty, 1)

	def test_unit_numbers_must_fit_the_quantity(self):
		self.assertRaises(frappe.ValidationError, make_bundle, 2, {5: ["Accepted"]})

	def test_entry_status_derived_from_reading(self):
		bundle = frappe.new_doc("Quality Inspection Reading Bundle")
		bundle.item_code = make_item(properties={"is_stock_item": 1}).name
		bundle.quantity = 2
		entry_rows = [
			# numeric: inside and outside [1, 10]
			{"unit_no": 1, "numeric": 1, "min_value": 1, "max_value": 10, "reading_value": "5"},
			{"unit_no": 2, "numeric": 1, "min_value": 1, "max_value": 10, "reading_value": "12"},
			# non-numeric: case-insensitive match against the criteria value
			{"unit_no": 1, "numeric": 0, "value": "Yes", "reading_value": " yes "},
			{"unit_no": 2, "numeric": 0, "value": "Yes", "reading_value": "no"},
		]
		for row in entry_rows:
			row["specification"] = ensure_parameter("_Test Derived Status Parameter")
			bundle.append("entries", row)
		bundle.insert(ignore_permissions=True)

		self.assertEqual(
			[entry.status for entry in bundle.entries], ["Accepted", "Rejected", "Accepted", "Rejected"]
		)
		self.assertEqual(bundle.accepted_qty, 1)  # unit 1 passed both readings
		self.assertEqual(bundle.rejected_qty, 1)  # unit 2 failed both
