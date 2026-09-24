import frappe
from frappe.utils import today

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


def get_report_rows(scio):
	_columns, data = execute(
		frappe._dict(company=scio.company, from_date=today(), to_date=today(), customer=scio.customer)
	)
	return {row.rm_item_code: row for row in data if row.subcontracting_inward_order == scio.name}
