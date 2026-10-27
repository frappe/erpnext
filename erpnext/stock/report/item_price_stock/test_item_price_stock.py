# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.item_price_stock.item_price_stock import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemPriceStock(ERPNextTestSuite):
	def run_report(self, **extra):
		return execute(frappe._dict(extra))[1]

	def test_users_who_cannot_read_item_prices_cannot_run_it(self):
		user = "item-price-stock-sales-user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Price Reader", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Sales User", "Stock User")

		frappe.set_user(user)
		try:
			self.assertRaises(frappe.PermissionError, self.run_report, item_code="_Test Item")
		finally:
			frappe.set_user("Administrator")

	def test_only_current_prices_are_listed_with_their_uom_and_party(self):
		from frappe.utils import add_days, today

		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			properties={"is_stock_item": 1, "uoms": [{"uom": "Box", "conversion_factor": 12}]}
		).name
		for rate, extra in (
			(500, {}),
			(450, {"customer": "_Test Customer"}),
			(400, {"valid_from": add_days(today(), -60), "valid_upto": add_days(today(), -31)}),
			(6000, {"uom": "Box"}),
		):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": item,
					"price_list": "Standard Selling",
					"price_list_rate": rate,
					**extra,
				}
			).insert()

		rows = self.run_report(item_code=item)

		self.assertEqual(
			sorted((row["selling_rate"], row["uom"], row["customer"]) for row in rows),
			[(450, "Nos", "_Test Customer"), (500, "Nos", None), (6000, "Box", None)],
		)

	def test_price_uom_and_stock_uom_are_shown_apart(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.report.item_price_stock.item_price_stock import execute

		item = make_item(
			properties={"is_stock_item": 1, "uoms": [{"uom": "Box", "conversion_factor": 12}]}
		).name
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item,
				"price_list": "Standard Selling",
				"price_list_rate": 6000,
				"uom": "Box",
			}
		).insert()

		columns, rows = execute(frappe._dict(item_code=item))
		labels = {column["fieldname"]: column["label"] for column in columns}

		self.assertEqual((labels["uom"], labels["stock_uom"]), ("Price UOM", "Stock UOM"))
		self.assertEqual([(row["uom"], row["stock_uom"]) for row in rows], [("Box", "Nos")])
