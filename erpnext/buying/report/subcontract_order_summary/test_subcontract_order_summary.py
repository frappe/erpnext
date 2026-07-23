# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.buying.report.subcontract_order_summary.subcontract_order_summary import execute
from erpnext.controllers.tests.test_subcontracting_controller import (
	get_subcontracting_order,
	make_bom_for_subcontracted_items,
	make_raw_materials,
	make_service_items,
	make_subcontracted_items,
)
from erpnext.tests.utils import ERPNextTestSuite

FG_ITEM = "Subcontracted Item SA7"


class TestSubcontractOrderSummary(ERPNextTestSuite):
	"""The report lists Subcontracting Order finished items with their ordered and
	received quantities within the transaction-date window."""

	def setUp(self):
		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()

	def run_report(self, **extra):
		filters = frappe._dict(
			{"company": "_Test Company", "from_date": add_days(today(), -1), "to_date": add_days(today(), 1)}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_subcontracting_order_is_listed(self):
		sco = get_subcontracting_order()

		rows = [r for r in self.run_report(name=sco.name) if r.get("item_code") == FG_ITEM]
		self.assertTrue(rows, "Subcontracting Order finished item missing from report")
		self.assertEqual(rows[0]["qty"], 10)
		self.assertEqual(rows[0]["received_qty"], 0)  # nothing received yet

	def test_out_of_range_date_excludes_order(self):
		sco = get_subcontracting_order()

		data = self.run_report(name=sco.name, from_date="2019-01-01", to_date="2019-01-31")
		self.assertEqual(data, [])
