import frappe
from frappe.utils import today

from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry as make_stock_entry_from_wo
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.subcontracting.doctype.subcontracting_inward_order.test_subcontracting_inward_order import (
	create_so_scio,
	create_test_data,
)
from erpnext.subcontracting.report.subcontracted_raw_materials_to_be_received.subcontracted_raw_materials_to_be_received import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSubcontractedRawMaterialsToBeReceived(ERPNextTestSuite):
	def setUp(self):
		create_test_data()
		make_stock_entry(
			item_code="Self RM", qty=100, to_warehouse="Stores - _TC", purpose="Material Receipt"
		)

	def test_pending_qty_counts_returned_raw_materials(self):
		_so, scio = create_so_scio()
		receive_basic_rm(scio, 2)
		return_basic_rm(scio, 1)

		rows = get_report_rows(scio)

		self.assertNotIn("Self RM", rows)
		self.assertEqual(rows["Basic RM"].required_qty, 5)
		self.assertEqual(rows["Basic RM"].received_qty, 2)
		self.assertEqual(rows["Basic RM"].returned_qty, 1)
		self.assertEqual(rows["Basic RM"].pending_qty, 4)
		self.assertEqual(rows["RM with Batch"].pending_qty, 5)

	def test_fully_received_raw_material_is_excluded(self):
		_so, scio = create_so_scio()
		receive_basic_rm(scio, 5)

		rows = get_report_rows(scio)

		self.assertNotIn("Basic RM", rows)
		self.assertIn("RM with Batch", rows)

	def test_pending_qty_includes_raw_materials_for_process_loss(self):
		_so, scio = create_so_scio()
		frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward()).submit()
		scio.reload()
		manufacture_with_process_loss(scio, 1)

		rows = get_report_rows(scio)

		self.assertEqual(rows["Basic RM"].received_qty, 5)
		self.assertEqual(rows["Basic RM"].process_loss_qty, 1)
		self.assertEqual(rows["Basic RM"].pending_qty, 1)


def receive_basic_rm(scio, qty):
	rm_in = frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward())
	rm_in.items = [item for item in rm_in.items if item.item_code == "Basic RM"]
	rm_in.items[0].qty = qty
	rm_in.submit()
	scio.reload()


def return_basic_rm(scio, qty):
	rm_return = frappe.new_doc("Stock Entry").update(scio.make_rm_return())
	rm_return.items = [item for item in rm_return.items if item.item_code == "Basic RM"]
	rm_return.items[0].qty = qty
	rm_return.submit()
	scio.reload()


def manufacture_with_process_loss(scio, process_loss_qty):
	work_order = frappe.get_doc("Work Order", scio.make_work_order()[0])
	work_order.skip_transfer = 1
	work_order.required_items[-1].source_warehouse = "Stores - _TC"
	work_order.submit()

	manufacture = frappe.new_doc("Stock Entry").update(
		make_stock_entry_from_wo(work_order.name, "Manufacture")
	)
	manufacture.save()
	manufacture.process_loss_qty = process_loss_qty
	manufacture.items[-1].qty = work_order.qty - process_loss_qty
	manufacture.submit()
	scio.reload()


def get_report_rows(scio):
	_columns, data = execute(
		frappe._dict(company=scio.company, from_date=today(), to_date=today(), customer=scio.customer)
	)
	return {row.rm_item_code: row for row in data if row.subcontracting_inward_order == scio.name}
