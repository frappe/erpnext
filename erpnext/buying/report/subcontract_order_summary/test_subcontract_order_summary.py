# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.buying.report.subcontract_order_summary.subcontract_order_summary import execute
from erpnext.buying.report.subcontracted_item_to_be_received.test_subcontracted_item_to_be_received import (
	make_subcontracting_order,
)


class TestSubcontractOrderSummary(FrappeTestCase):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"order_type": "Subcontracting Order",
				"company": "_Test Company",
				"from_date": add_days(today(), -1),
				"to_date": add_days(today(), 1),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_every_raw_material_row_has_its_order(self):
		sco = make_subcontracting_order()

		rows = self.run_report(name=sco.name)
		self.assertGreater(len(rows), 1)
		self.assertEqual({row.get("order_id") for row in rows}, {sco.name})
