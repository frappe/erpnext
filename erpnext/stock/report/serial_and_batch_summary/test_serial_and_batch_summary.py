# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSerialAndBatchSummary(ERPNextTestSuite):
	def run_report(self, **extra):
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import execute

		return execute(frappe._dict(extra))[1]

	def test_serial_filter_needs_voucher_and_item_read(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import get_serial_nos
		from erpnext.tests.permission_test_utils import (
			OTHER_COMPANY,
			as_user,
			make_company_fenced_user,
			make_fenced_user,
		)

		item = "_Test Serialized Item With Series"
		se = make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=2, basic_rate=100)
		voucher_filters = {"voucher_type": "Stock Entry", "voucher_no": [se.name]}
		expected = get_serial_nos("Serial No", "", "name", 0, 10, voucher_filters)
		self.assertEqual(len(expected), 2)

		self.assertEqual(get_serial_nos("Serial No", "", "name", 0, 10, {"voucher_no": [se.name]}), [])

		with as_user(make_company_fenced_user("summary-stock-user@example.com", ["Stock User"], se.company)):
			self.assertEqual(get_serial_nos("Serial No", "", "name", 0, 10, voucher_filters), expected)

		outsider = make_fenced_user("summary-outsider@example.com", [])
		with as_user(outsider):
			self.assertRaises(
				frappe.PermissionError, get_serial_nos, "Serial No", "", "name", 0, 10, voucher_filters
			)
			self.assertRaises(
				frappe.PermissionError, get_serial_nos, "Serial No", "", "name", 0, 10, {"item_code": item}
			)

		fenced = make_company_fenced_user("summary-fenced@example.com", ["Stock User"], OTHER_COMPANY)
		with as_user(fenced):
			self.assertRaises(
				frappe.PermissionError, get_serial_nos, "Serial No", "", "name", 0, 10, voucher_filters
			)

	def test_group_warehouse_includes_its_warehouses(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import execute

		item = "_Test Serialized Item With Series"
		se = make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=2, basic_rate=100)
		group = frappe.db.get_value("Warehouse", "Stores - _TC", "parent_warehouse")

		columns, data = execute(
			frappe._dict(voucher_no=[se.name], voucher_type="Stock Entry", warehouse=group)
		)[:2]

		self.assertEqual(len(data), 2)
		self.assertIn("warehouse", [column.get("fieldname") for column in columns])
		self.assertEqual({row.warehouse for row in data}, {"Stores - _TC"})

	def test_qty_column_is_shown_for_serial_items(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import execute

		item = "_Test Serialized Item With Series"
		se = make_stock_entry(item_code=item, to_warehouse="Stores - _TC", qty=1, basic_rate=100)

		columns = execute(frappe._dict(item_code=item, voucher_no=[se.name], voucher_type="Stock Entry"))[0]

		self.assertIn("qty", [column.get("fieldname") for column in columns])

	def test_batch_filter_lists_nothing_without_access_to_batches(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import get_batch_nos

		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		frappe.get_doc(doctype="Batch", item=item, batch_id="Summary-Hidden-Batch").insert()
		user = "summary-purchase-user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				doctype="User",
				email=user,
				first_name="Summary",
				send_welcome_email=0,
				roles=[{"role": "Purchase User"}],
			).insert()

		with self.set_user(user):
			rows = get_batch_nos("Batch", "Summary-Hidden", "name", 0, 5, {"item_code": item})

		self.assertEqual(rows, [])

	def test_pick_list_bundle_moves_no_stock(self):
		from erpnext.selling.doctype.sales_order.sales_order import create_pick_list
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.valuation_adjustment import get_ledger_lots

		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SBPL-.#####",
			}
		).name
		make_stock_entry(item_code=item, to_warehouse="_Test Warehouse - _TC", qty=10, basic_rate=50)
		sales_order = make_sales_order(item_code=item, warehouse="_Test Warehouse - _TC", qty=3, rate=100)
		pick_list = create_pick_list(sales_order.name)
		pick_list.submit()

		self.assertEqual({row.voucher_type for row in self.run_report(item_code=item)}, {"Stock Entry"})
		self.assertEqual(
			[row.voucher_no for row in self.run_report(item_code=item, voucher_type="Pick List")],
			[pick_list.name],
		)

		lots = get_ledger_lots(item, "_Test Warehouse - _TC", frappe.utils.add_days(frappe.utils.now(), 1))
		self.assertEqual(sum(lots.batch_qty.values()), 10)

	def make_open_pos_invoice(self):
		"""A POS Invoice for 3 of a batch of 10, in a POS that is still open."""
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
		from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
		from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
			get_batch_from_bundle,
		)
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, user.name)
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SBPOS-.#####",
			}
		).name
		receipt = make_stock_entry(
			item_code=item, to_warehouse="_Test Warehouse - _TC", qty=10, basic_rate=50
		)
		pos_invoice = create_pos_invoice(
			item=item,
			qty=3,
			rate=100,
			batch_no=get_batch_from_bundle(receipt.items[0].serial_and_batch_bundle),
			use_serial_batch_fields=1,
			do_not_save=1,
		)
		pos_invoice.append("payments", {"mode_of_payment": "Cash", "amount": 300, "default": 1})
		pos_invoice.submit()
		return opening_entry, pos_invoice

	@ERPNextTestSuite.change_settings("POS Settings", {"invoice_type": "POS Invoice"})
	def test_unconsolidated_pos_invoice_bundle_moves_no_stock(self):
		from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
			make_closing_entry_from_opening,
		)
		from erpnext.stock.valuation_adjustment import get_ledger_lots

		opening_entry, pos_invoice = self.make_open_pos_invoice()
		item = pos_invoice.items[0].item_code

		self.assertEqual({row.voucher_type for row in self.run_report(item_code=item)}, {"Stock Entry"})

		lots = get_ledger_lots(item, "_Test Warehouse - _TC", frappe.utils.add_days(frappe.utils.now(), 1))
		self.assertEqual(sum(lots.batch_qty.values()), 10)
		# an open entry blocks restoring the POS Settings invoice type
		make_closing_entry_from_opening(opening_entry).submit()

	@ERPNextTestSuite.change_settings("POS Settings", {"invoice_type": "POS Invoice"})
	def test_consolidated_pos_invoice_bundle_with_old_entries_moves_stock(self):
		from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
			make_closing_entry_from_opening,
		)
		from erpnext.stock.valuation_adjustment import get_ledger_lots

		opening_entry, pos_invoice = self.make_open_pos_invoice()
		make_closing_entry_from_opening(opening_entry).submit()
		# older consolidations left the entries on the POS Invoice
		frappe.db.set_value(
			"Serial and Batch Entry",
			{"parent": pos_invoice.items[0].serial_and_batch_bundle},
			"voucher_type",
			"POS Invoice",
		)

		lots = get_ledger_lots(
			pos_invoice.items[0].item_code,
			"_Test Warehouse - _TC",
			frappe.utils.add_days(frappe.utils.now(), 1),
		)
		self.assertEqual(sum(lots.batch_qty.values()), 7)
