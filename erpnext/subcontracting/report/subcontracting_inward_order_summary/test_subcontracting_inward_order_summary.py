import frappe
from frappe.utils import today

from erpnext.subcontracting.doctype.subcontracting_inward_order.test_subcontracting_inward_order import (
	create_so_scio,
	create_test_data,
)
from erpnext.subcontracting.report.subcontracted_raw_materials_to_be_received.test_subcontracted_raw_materials_to_be_received import (
	receive_basic_rm,
	return_basic_rm,
)
from erpnext.subcontracting.report.subcontracting_inward_order_summary.subcontracting_inward_order_summary import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSubcontractingInwardOrderSummary(ERPNextTestSuite):
	def setUp(self):
		create_test_data()

	def test_finished_good_is_listed_with_customer_provided_raw_materials(self):
		_so, scio = create_so_scio()
		receive_basic_rm(scio, 2)
		return_basic_rm(scio, 1)

		_columns, data = execute(
			frappe._dict(
				company=scio.company,
				from_date=today(),
				to_date=today(),
				subcontracting_inward_order=scio.name,
			)
		)

		self.assertEqual(
			[row["rm_item_code"] for row in data],
			["Basic RM", "RM with Serial", "RM with Batch", "RM with Serial and Batch"],
		)
		self.assertEqual(data[0]["subcontracting_inward_order"], scio.name)
		self.assertEqual(data[0]["item_code"], "Basic FG Item")
		self.assertEqual(data[0]["qty"], 5)
		self.assertEqual(data[0]["required_qty"], 5)
		self.assertEqual(data[0]["received_qty"], 2)
		self.assertEqual(data[0]["rm_returned_qty"], 1)
		self.assertIsNone(data[1]["item_code"])
		self.assertIsNone(data[1]["qty"])
