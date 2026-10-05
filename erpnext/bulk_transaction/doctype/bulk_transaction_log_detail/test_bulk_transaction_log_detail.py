# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.bulk_transaction import retry, transaction_processing


class TestBulkTransactionLogDetail(ERPNextTestSuite):
	def setUp(self):
		enqueue = patch("frappe.enqueue", side_effect=run_job_inline)
		enqueue.start()
		self.addCleanup(enqueue.stop)

	def test_retry_skips_sources_converted_by_a_later_run(self):
		order = make_sales_order(do_not_submit=True)
		make_invoices([order])
		order.submit()
		make_invoices([order])

		retry()

		self.assertEqual(len(get_invoices(order.name)), 1)
		failed_log = frappe.get_last_doc(
			"Bulk Transaction Log Detail", {"transaction_name": order.name, "retried": 1}
		)
		self.assertEqual(failed_log.transaction_status, "Failed")

	def test_held_and_closed_orders_are_skipped_without_a_client_status(self):
		held, closed = make_sales_order(), make_sales_order()
		held.update_status("On Hold")
		closed.update_status("Closed")

		make_invoices([held, closed])
		make_invoices([held, closed], status="To Deliver and Bill")

		self.assertFalse(get_invoices(held.name) + get_invoices(closed.name))


def make_invoices(orders: list, **kwargs) -> None:
	data = [{"name": order.name, **kwargs} for order in orders]
	transaction_processing(data, "Sales Order", "Sales Invoice")


def get_invoices(sales_order: str) -> list[str]:
	return frappe.get_all("Sales Invoice Item", {"sales_order": sales_order}, pluck="parent", distinct=True)


def run_job_inline(method, **kwargs) -> MagicMock:
	if callable(method):
		method(**kwargs)
	return MagicMock()
