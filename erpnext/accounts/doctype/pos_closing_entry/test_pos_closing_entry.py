# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.handler import run_doc_method

from erpnext.accounts.doctype.accounting_dimension.test_accounting_dimension import (
	create_dimension,
	disable_dimension,
)
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
	make_closing_entry_from_opening,
)
from erpnext.accounts.doctype.pos_invoice.pos_invoice import make_sales_return
from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.selling.page.point_of_sale.point_of_sale import get_items
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
)
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry


class TestPOSClosingEntry(unittest.TestCase):
	def setUp(self):
		# Make stock available for POS Sales
		make_stock_entry(target="_Test Warehouse - _TC", qty=2, basic_rate=100)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.sql("delete from `tabPOS Profile`")
		if card_mode := getattr(self, "card_mode", None):
			frappe.delete_doc("Mode of Payment", card_mode, force=True)

	def test_pos_closing_entry(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.save()
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.save()
		pos_inv2.submit()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		payment = pcv_doc.payment_reconciliation[0]

		self.assertEqual(payment.mode_of_payment, "Cash")

		for d in pcv_doc.payment_reconciliation:
			if d.mode_of_payment == "Cash":
				d.closing_amount = 6700

		pcv_doc.submit()

		self.assertEqual(pcv_doc.total_quantity, 2)
		self.assertEqual(pcv_doc.net_total, 6700)

	def test_closing_with_disabled_sales_person(self):
		# A separate POS Profile keeps invoices that other tests leave unconsolidated out of this closing.
		test_user, pos_profile = init_user_and_profile(
			name=f"_Test POS Profile {frappe.generate_hash(length=8)}"
		)
		opening = create_opening_entry(pos_profile, test_user.name)
		frappe.set_user("Administrator")
		person = frappe.get_doc(
			doctype="Sales Person",
			sales_person_name=f"_Test Closing {frappe.generate_hash(length=10)}",
			commission_rate=10,
			enabled=1,
		).insert()
		# The closing collects only the cashier's own invoices, so create the invoice as the cashier.
		frappe.set_user(test_user.name)
		invoice = create_pos_invoice(rate=100, do_not_submit=1, pos_profile=pos_profile.name)
		invoice.append("payments", {"mode_of_payment": "Cash", "amount": 100})
		invoice.append("sales_team", {"sales_person": person.name, "allocated_percentage": 100})
		invoice.save()
		invoice.submit()
		frappe.set_user("Administrator")
		person.enabled = 0
		person.save()

		closing = make_closing_entry_from_opening(opening)
		self.assertEqual([row.pos_invoice for row in closing.pos_transactions], [invoice.name])
		closing.flags.in_test = True
		closing.submit()
		invoice.reload()
		self.assertTrue(invoice.consolidated_invoice)
		self.assertEqual(invoice.sales_team[0].incentives, 10)
		closing.load_from_db()
		closing.cancel()
		invoice.reload()
		self.assertFalse(invoice.consolidated_invoice)
		self.assertEqual(invoice.sales_team[0].incentives, 10)

	def test_pos_closing_without_item_code(self):
		"""
		Test if POS Closing Entry is created without item code
		"""
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv = create_pos_invoice(rate=3500, do_not_submit=1, item_name="Test Item", without_item_code=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv.save()
		pos_inv.submit()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		pcv_doc.submit()

		self.assertTrue(pcv_doc.name)

	def test_pos_qty_for_item(self):
		"""
		Test if quantity is calculated correctly for an item in POS Closing Entry
		"""
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		test_item_qty = get_test_item_qty(pos_profile)

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.save()
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.save()
		pos_inv2.submit()

		# make return entry of pos_inv2
		pos_return = make_sales_return(pos_inv2.name)
		pos_return.paid_amount = pos_return.grand_total
		pos_return.save()
		pos_return.submit()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		pcv_doc.submit()

		opening_entry = create_opening_entry(pos_profile, test_user.name)
		test_item_qty_after_sales = get_test_item_qty(pos_profile)
		self.assertEqual(test_item_qty_after_sales, test_item_qty - 1)

	def test_cancelling_of_pos_closing_entry(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.save()
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.save()
		pos_inv2.submit()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		payment = pcv_doc.payment_reconciliation[0]

		self.assertEqual(payment.mode_of_payment, "Cash")

		for d in pcv_doc.payment_reconciliation:
			if d.mode_of_payment == "Cash":
				d.closing_amount = 6700

		pcv_doc.submit()

		pos_inv1.load_from_db()
		self.assertRaises(frappe.ValidationError, pos_inv1.cancel)

		si_doc = frappe.get_doc("Sales Invoice", pos_inv1.consolidated_invoice)
		self.assertRaises(frappe.ValidationError, si_doc.cancel)

		pcv_doc.load_from_db()
		pcv_doc.cancel()

		cancelled_invoice = frappe.db.get_value(
			"POS Invoice Merge Log", {"pos_closing_entry": pcv_doc.name}, "consolidated_invoice"
		)
		docstatus = frappe.db.get_value("Sales Invoice", cancelled_invoice, "docstatus")
		self.assertEqual(docstatus, 2)

		pos_inv1.load_from_db()
		self.assertEqual(pos_inv1.status, "Paid")

	def test_pos_closing_for_required_accounting_dimension_in_pos_profile(self):
		"""
		test case to check whether we can create POS Closing Entry without mandatory accounting dimension
		"""

		create_dimension()
		pos_profile = make_pos_profile(do_not_insert=1, do_not_set_accounting_dimension=1)

		self.assertRaises(frappe.ValidationError, pos_profile.insert)

		pos_profile.location = "Block 1"
		pos_profile.insert()
		self.assertTrue(frappe.db.exists("POS Profile", pos_profile.name))

		test_user = init_user_and_profile(do_not_create_pos_profile=1)

		opening_entry = create_opening_entry(pos_profile, test_user.name)
		pos_inv1 = create_pos_invoice(rate=350, do_not_submit=1, pos_profile=pos_profile.name)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.save()
		pos_inv1.submit()

		# if in between a mandatory accounting dimension is added to the POS Profile then
		accounting_dimension_department = frappe.get_doc("Accounting Dimension", {"name": "Department"})
		accounting_dimension_department.dimension_defaults[0].mandatory_for_bs = 1
		accounting_dimension_department.save()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		# will assert coz the new mandatory accounting dimension bank is not set in POS Profile
		self.assertRaises(frappe.ValidationError, pcv_doc.submit)

		accounting_dimension_department = frappe.get_doc(
			"Accounting Dimension Detail", {"parent": "Department"}
		)
		accounting_dimension_department.mandatory_for_bs = 0
		accounting_dimension_department.save()
		disable_dimension()

	def test_merging_into_sales_invoice_for_batched_item(self):
		frappe.flags.print_message = False
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import (
			init_user_and_profile,
		)
		from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
			consolidate_pos_invoices,
		)
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		frappe.db.sql("delete from `tabPOS Invoice`")
		item_doc = make_item(
			"_Test Item With Batch FOR POS Merge Test",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "BATCH-PM-POS-MERGE-.####",
				"create_new_batch": 1,
			},
		)

		item_code = item_doc.name
		se = make_stock_entry(
			target="_Test Warehouse - _TC",
			item_code=item_code,
			qty=10,
			basic_rate=100,
			use_serial_batch_fields=0,
		)
		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)

		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv = create_pos_invoice(
			item_code=item_code,
			qty=5,
			rate=300,
			use_serial_batch_fields=1,
			batch_no=batch_no,
			do_not_submit=True,
		)
		pos_inv.payments[0].amount = pos_inv.grand_total
		pos_inv.save()
		pos_inv.submit()
		pos_inv2 = create_pos_invoice(
			item_code=item_code,
			qty=5,
			rate=300,
			use_serial_batch_fields=1,
			batch_no=batch_no,
			do_not_submit=True,
		)
		pos_inv2.payments[0].amount = pos_inv2.grand_total
		pos_inv2.save()
		pos_inv2.submit()

		batch_qty_with_pos = get_batch_qty(batch_no, "_Test Warehouse - _TC", item_code)
		self.assertEqual(batch_qty_with_pos, 0.0)

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		pcv_doc.submit()

		piv_merge = frappe.db.get_value("POS Invoice Merge Log", {"pos_closing_entry": pcv_doc.name}, "name")

		self.assertTrue(piv_merge)
		piv_merge_doc = frappe.get_doc("POS Invoice Merge Log", piv_merge)
		self.assertTrue(piv_merge_doc.pos_invoices[0].pos_invoice)
		self.assertTrue(piv_merge_doc.pos_invoices[1].pos_invoice)

		pos_inv.load_from_db()
		self.assertTrue(pos_inv.consolidated_invoice)
		pos_inv2.load_from_db()
		self.assertTrue(pos_inv2.consolidated_invoice)

		batch_qty = frappe.db.get_value("Batch", batch_no, "batch_qty")
		self.assertEqual(batch_qty, 0.0)

		batch_qty_with_pos = get_batch_qty(batch_no, "_Test Warehouse - _TC", item_code)
		self.assertEqual(batch_qty_with_pos, 0.0)

		frappe.flags.print_message = True

		pcv_doc.reload()
		pcv_doc.cancel()

		batch_qty_with_pos = get_batch_qty(batch_no, "_Test Warehouse - _TC", item_code)
		self.assertEqual(batch_qty_with_pos, 0.0)

		pos_inv.reload()
		pos_inv2.reload()

		pos_inv.cancel()
		pos_inv2.cancel()

		batch_qty_with_pos = get_batch_qty(batch_no, "_Test Warehouse - _TC", item_code)
		self.assertEqual(batch_qty_with_pos, 10.0)

	def test_closing_consolidates_sale_of_batch_disabled_after_sale(self):
		opening_entry, pos_invoice, batch_no = self.make_session_with_batch_sale()
		frappe.db.set_value("Batch", batch_no, "disabled", 1)

		make_closing_entry_from_opening(opening_entry).submit()

		pos_invoice.load_from_db()
		self.assertTrue(pos_invoice.consolidated_invoice)

	def test_closing_consolidates_sale_of_batch_expired_after_sale(self):
		opening_entry, pos_invoice, batch_no = self.make_session_with_batch_sale()
		frappe.db.set_value(
			"Batch", batch_no, "expiry_date", frappe.utils.add_days(pos_invoice.posting_date, -1)
		)

		make_closing_entry_from_opening(opening_entry).submit()

		pos_invoice.load_from_db()
		self.assertTrue(pos_invoice.consolidated_invoice)

	def test_disabled_batch_cannot_be_sold_in_pos(self):
		item_code, batch_no = self.make_batch_item_with_stock()
		frappe.db.set_value("Batch", batch_no, "disabled", 1)
		test_user, pos_profile = init_user_and_profile()
		create_opening_entry(pos_profile, test_user.name)

		pos_invoice = create_pos_invoice(
			item_code=item_code, qty=2, rate=300, batch_no=batch_no, do_not_save=1
		)
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", pos_invoice.insert)

	def make_session_with_batch_sale(self):
		item_code, batch_no = self.make_batch_item_with_stock()
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_invoice = create_pos_invoice(
			item_code=item_code, qty=2, rate=300, batch_no=batch_no, do_not_submit=1
		)
		pos_invoice.payments[0].amount = pos_invoice.grand_total
		pos_invoice.save()
		pos_invoice.submit()

		return opening_entry, pos_invoice, batch_no

	def make_batch_item_with_stock(self):
		item_code = make_item(
			"_Test POS Closing Batch Item",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "BATCH-POS-CLOSING-.####",
				"create_new_batch": 1,
			},
		).name
		stock_entry = make_stock_entry(
			target="_Test Warehouse - _TC", item_code=item_code, qty=10, basic_rate=100
		)

		return item_code, get_batch_from_bundle(stock_entry.items[0].serial_and_batch_bundle)

	def test_change_is_taken_once_with_zero_value_card_payment(self):
		test_user, pos_profile = init_user_and_profile()
		frappe.set_user("Administrator")
		self.card_mode = f"_Test Card {frappe.generate_hash(length=8)}"
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": self.card_mode,
				"type": "General",
				"accounts": [{"company": "_Test Company", "default_account": "Cash - _TC"}],
			}
		).insert()
		pos_profile.append("payments", {"mode_of_payment": self.card_mode})
		pos_profile.save()
		frappe.set_user(test_user.name)

		opening_entry = create_opening_entry(pos_profile, test_user.name)
		pos_invoice = create_pos_invoice(rate=90, pos_profile=pos_profile.name, do_not_save=1)
		pos_invoice.set("payments", [])
		pos_invoice.append(
			"payments", {"mode_of_payment": self.card_mode, "account": "Cash - _TC", "amount": 0}
		)
		pos_invoice.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 100})
		pos_invoice.insert()
		pos_invoice.submit()
		self.assertEqual([row.mode_of_payment for row in pos_invoice.payments], [self.card_mode, "Cash"])

		closing_entry = make_closing_entry_from_opening(opening_entry)
		expected = {row.mode_of_payment: row.expected_amount for row in closing_entry.payment_reconciliation}
		self.assertEqual(expected, {"Cash": 90, self.card_mode: 0})

	def test_closing_refuses_session_invoices_left_out(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		make_paid_pos_invoice([("Cash", 90)])

		closing_entry = make_closing_entry_from_opening(opening_entry)
		late_sale = make_paid_pos_invoice([("Cash", 90)])
		self.assertRaises(frappe.ValidationError, closing_entry.submit)

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.submit()
		self.assertTrue(frappe.db.get_value("POS Invoice", late_sale.name, "consolidated_invoice"))

	def test_cancel_with_ten_merge_logs_unconsolidates_after_commit(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		customers = make_customers(10)
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		for customer in customers:
			make_paid_pos_invoice([("Cash", 90)], customer=customer)

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.submit()
		closing_entry.reload()

		with patch("erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log.enqueue") as enqueue:
			closing_entry.cancel()

		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
		self.assertEqual(closing_entry.ignore_linked_doctypes, ("POS Invoice Merge Log", "Sales Invoice"))
		merge_logs = enqueue.call_args.kwargs["merge_logs"]
		self.assertEqual(len(merge_logs), 10)
		enqueue.call_args.args[0](
			merge_logs=merge_logs, closing_entry=enqueue.call_args.kwargs["closing_entry"]
		)

		for merge_log in merge_logs:
			self.assertEqual(frappe.db.get_value("POS Invoice Merge Log", merge_log, "docstatus"), 2)
		self.assertEqual(frappe.db.get_value("POS Opening Entry", opening_entry.name, "status"), "Open")

	def test_retry_runs_only_on_failed_closing_entry(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		make_paid_pos_invoice([("Cash", 90)])
		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.submit()

		consolidate = "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.consolidate_pos_invoices"
		with patch(consolidate) as consolidate_pos_invoices:
			self.assertRaises(frappe.ValidationError, closing_entry.retry)
			consolidate_pos_invoices.assert_not_called()

			closing_entry.db_set("status", "Failed")
			closing_entry.status = "Submitted"
			closing_entry.retry()
			consolidate_pos_invoices.assert_called_once()

	def test_retry_refuses_session_invoices_sold_after_failed_consolidation(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		make_paid_pos_invoice([("Cash", 90)])
		closing_entry = make_closing_entry_from_opening(opening_entry)

		consolidate = "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.consolidate_pos_invoices"
		with patch(consolidate):
			closing_entry.submit()
		closing_entry.db_set("status", "Failed")
		late_sale = make_paid_pos_invoice([("Cash", 90)])

		with patch(consolidate) as consolidate_pos_invoices:
			with self.assertRaises(frappe.ValidationError) as context:
				closing_entry.retry()
			consolidate_pos_invoices.assert_not_called()

		self.assertIn(late_sale.name, str(context.exception))

	def test_failed_cancel_keeps_closing_entry_submitted(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		make_paid_pos_invoice([("Cash", 90)])
		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.submit()

		with failures_handled_outside_tests(), patch(
			f"{MERGE_LOG_CLASS}.cancel", side_effect=frappe.ValidationError
		):
			self.assertRaises(frappe.ValidationError, closing_entry.cancel)

		self.assertEqual(
			frappe.db.get_value("POS Closing Entry", closing_entry.name, ["docstatus", "status"]),
			(1, "Submitted"),
		)

	def test_failed_submit_keeps_closing_entry_draft(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		make_paid_pos_invoice([("Cash", 90)])
		closing_entry = make_closing_entry_from_opening(opening_entry).insert()

		with failures_handled_outside_tests(), patch(
			f"{MERGE_LOG_CLASS}.submit", side_effect=frappe.ValidationError
		):
			self.assertRaises(frappe.ValidationError, closing_entry.submit)

		self.assertEqual(
			frappe.db.get_value("POS Closing Entry", closing_entry.name, ["docstatus", "status"]),
			(0, "Draft"),
		)

	def test_failed_background_cancel_is_marked_failed_and_can_be_retried(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		customers = make_customers(10)
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		for customer in customers:
			make_paid_pos_invoice([("Cash", 90)], customer=customer)
		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.submit()
		closing_entry.reload()

		with patch("erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log.enqueue") as enqueue:
			closing_entry.cancel()

		job, job_arguments = enqueue.call_args.args[0], enqueue.call_args.kwargs
		with failures_handled_outside_tests(), patch(
			f"{MERGE_LOG_CLASS}.cancel", side_effect=frappe.ValidationError
		):
			self.assertRaises(
				frappe.ValidationError,
				job,
				merge_logs=job_arguments["merge_logs"],
				closing_entry=job_arguments["closing_entry"],
			)

		self.assertEqual(
			frappe.db.get_value("POS Closing Entry", closing_entry.name, ["docstatus", "status"]),
			(2, "Failed"),
		)

		with patch("erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log.enqueue") as enqueue:
			closing_entry.retry()
		enqueue.call_args.args[0](
			merge_logs=enqueue.call_args.kwargs["merge_logs"],
			closing_entry=enqueue.call_args.kwargs["closing_entry"],
		)

		for merge_log in job_arguments["merge_logs"]:
			self.assertEqual(frappe.db.get_value("POS Invoice Merge Log", merge_log, "docstatus"), 2)
		self.assertEqual(
			frappe.db.get_value("POS Closing Entry", closing_entry.name, ["docstatus", "status"]),
			(2, "Cancelled"),
		)
		self.assertEqual(frappe.db.get_value("POS Opening Entry", opening_entry.name, "status"), "Open")

	def test_retry_from_form_reruns_failed_cancel(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		make_paid_pos_invoice([("Cash", 90)])
		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.submit()
		merge_log = frappe.db.get_value("POS Invoice Merge Log", {"pos_closing_entry": closing_entry.name})
		frappe.db.set_value("POS Closing Entry", closing_entry.name, {"docstatus": 2, "status": "Failed"})

		with (
			patch("frappe.handler.is_valid_http_method"),
			patch.object(frappe.local, "response", frappe._dict(docs=[])),
		):
			run_doc_method("retry", dt="POS Closing Entry", dn=closing_entry.name)

		self.assertEqual(
			frappe.db.get_value("POS Closing Entry", closing_entry.name, ["docstatus", "status"]),
			(2, "Cancelled"),
		)
		self.assertEqual(frappe.db.get_value("POS Invoice Merge Log", merge_log, "docstatus"), 2)
		self.assertEqual(frappe.db.get_value("POS Opening Entry", opening_entry.name, "status"), "Open")

	def test_cancel_without_queue_keeps_back_link_check(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		make_paid_pos_invoice([("Cash", 90)])
		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.submit()
		closing_entry.reload()

		closing_entry.cancel()
		self.assertFalse(closing_entry.get("ignore_linked_doctypes"))

	def test_missing_invoices_message_lists_first_ten(self):
		make_stock_entry(target="_Test Warehouse - _TC", qty=11, basic_rate=100)
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)
		closing_entry = make_closing_entry_from_opening(opening_entry)
		late_sales = [make_paid_pos_invoice([("Cash", 90)]).name for _ in range(11)]

		with self.assertRaises(frappe.ValidationError) as context:
			closing_entry.submit()

		message = str(context.exception)
		self.assertIn("and 1 more", message)
		self.assertEqual(sum(name in message for name in late_sales), 10)


MERGE_LOG_CLASS = "erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log.POSInvoiceMergeLog"


@contextmanager
def failures_handled_outside_tests():
	frappe.db.savepoint("before_failure")
	rollback = frappe.db.rollback
	with (
		patch.object(frappe.db, "rollback", lambda **kwargs: rollback(save_point="before_failure")),
		patch.object(frappe.db, "commit"),
	):
		yield


def init_user_and_profile(**args):
	user = "test@example.com"
	test_user = frappe.get_doc("User", user)

	roles = ("Accounts Manager", "Accounts User", "Sales Manager")
	test_user.add_roles(*roles)
	frappe.set_user(user)

	if args.get("do_not_create_pos_profile"):
		return test_user

	pos_profile = make_pos_profile(**args)
	pos_profile.append("applicable_for_users", {"default": 1, "user": user})

	pos_profile.save()

	return test_user, pos_profile


def get_test_item_qty(pos_profile):
	test_item_pos = get_items(
		start=0,
		page_length=5,
		price_list="Standard Selling",
		pos_profile=pos_profile.name,
		search_term="_Test Item",
		item_group="All Item Groups",
	)

	test_item_qty = next(item for item in test_item_pos["items"] if item["item_code"] == "_Test Item").get(
		"actual_qty"
	)
	return test_item_qty


def make_paid_pos_invoice(payments, **args):
	pos_invoice = create_pos_invoice(rate=90, do_not_submit=1, **args)
	for mode_of_payment, amount in payments:
		pos_invoice.append("payments", {"mode_of_payment": mode_of_payment, "amount": amount})
	pos_invoice.save()
	pos_invoice.submit()
	return pos_invoice


def make_customers(count):
	customers = []
	for index in range(count):
		customer_name = f"_Test POS Closing Customer {index + 1}"
		customer = frappe.db.get_value("Customer", {"customer_name": customer_name}) or (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": customer_name,
					"customer_group": "_Test Customer Group",
					"territory": "_Test Territory",
				}
			)
			.insert()
			.name
		)
		customers.append(customer)
	return customers
