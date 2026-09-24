import frappe
from frappe.utils import today

from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry as make_stock_entry_from_wo
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.subcontracting.doctype.subcontracting_inward_order.test_subcontracting_inward_order import (
	create_so_scio,
	create_test_data,
)
from erpnext.subcontracting.report.subcontracted_items_to_be_delivered.subcontracted_items_to_be_delivered import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSubcontractedItemsToBeDelivered(ERPNextTestSuite):
	def setUp(self):
		create_test_data()
		make_stock_entry(
			item_code="Self RM", qty=100, to_warehouse="Stores - _TC", purpose="Material Receipt"
		)

	def test_pending_qty_for_partial_delivery(self):
		_so, scio = create_so_scio()
		produce_and_deliver(scio, 2)

		rows = get_report_rows(scio)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].item_code, "Basic FG Item")
		self.assertEqual(rows[0].qty, 5)
		self.assertEqual(rows[0].produced_qty, 5)
		self.assertEqual(rows[0].delivered_qty, 2)
		self.assertEqual(rows[0].pending_qty, 3)

	def test_fully_delivered_item_is_excluded(self):
		_so, scio = create_so_scio()
		produce_and_deliver(scio, 5)

		self.assertEqual(get_report_rows(scio), [])

	def test_customer_return_does_not_reopen_pending_qty(self):
		_so, scio = create_so_scio()
		produce_and_deliver(scio, 2)
		return_finished_good(scio, 1)

		rows = get_report_rows(scio)

		self.assertEqual(rows[0].delivered_qty, 2)
		self.assertEqual(rows[0].pending_qty, 3)


def produce_and_deliver(scio, qty):
	frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward()).submit()
	scio.reload()

	work_order = frappe.get_doc("Work Order", scio.make_work_order()[0])
	work_order.skip_transfer = 1
	work_order.required_items[-1].source_warehouse = "Stores - _TC"
	work_order.submit()
	frappe.new_doc("Stock Entry").update(make_stock_entry_from_wo(work_order.name, "Manufacture")).submit()
	scio.reload()

	delivery = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_delivery())
	delivery.items[0].qty = qty
	delivery.submit()
	scio.reload()


def return_finished_good(scio, qty):
	fg_return = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_return())
	fg_return.items[0].qty = qty
	fg_return.items[0].t_warehouse = "_Test Warehouse - _TC"
	fg_return.submit()
	scio.reload()


def get_report_rows(scio):
	_columns, data = execute(
		frappe._dict(company=scio.company, from_date=today(), to_date=today(), customer=scio.customer)
	)
	return [row for row in data if row.subcontracting_inward_order == scio.name]
