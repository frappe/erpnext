# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_to_date, now

from erpnext.manufacturing.doctype.job_card.mapper import make_corrective_job_card
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.cost_of_poor_quality_report.cost_of_poor_quality_report import execute
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestCostOfPoorQualityReport(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("BOM")
		# BOM with operations for _Test FG Item 2, so submitting the work order creates Job Cards
		bom = frappe.copy_doc(self.globalTestRecords["BOM"][2])
		bom.set_rate_of_sub_assembly_item_based_on_bom = 0
		bom.rm_cost_as_per = "Valuation Rate"
		bom.items[0].uom = "_Test UOM 1"
		bom.items[0].conversion_factor = 5
		bom.insert(ignore_if_duplicate=True)

	def test_batch_no_filter_is_case_insensitive(self):
		# The report's batch_no filter used an exact `==`, which is case-sensitive on Postgres -- a
		# differently-cased batch_no would miss job cards that MariaDB (case-insensitive collation)
		# matches. Lower() both sides keeps MariaDB unchanged and makes Postgres match too.
		wo = make_wo_order_test_record(item="_Test FG Item 2", qty=2, transfer_material_against="Work Order")
		for item in wo.required_items:
			make_stock_entry(
				item_code=item.item_code,
				target=item.source_warehouse,
				qty=item.required_qty * 2,
				basic_rate=100,
			)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo.name})
		job_card.append(
			"time_logs", {"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 2}
		)
		job_card.submit()

		corrective_op = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()
		corrective_jc = make_corrective_job_card(
			job_card.name, operation=corrective_op.name, for_operation=job_card.operation
		)
		corrective_jc.hour_rate = 100
		corrective_jc.insert()
		corrective_jc.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=2),
				"to_time": add_to_date(now(), hours=2, minutes=30),
				"completed_qty": 2,
			},
		)
		corrective_jc.submit()
		# store an uppercase batch_no; the report is then filtered with a lowercase value
		corrective_jc.db_set("batch_no", "TESTCOPQBATCH")

		_columns, data = execute(frappe._dict({"batch_no": "testcopqbatch"}))
		self.assertTrue(any(row.get("name") == corrective_jc.name for row in data))
