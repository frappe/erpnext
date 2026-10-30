# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.utils import add_days, today

from erpnext.buying.report.subcontract_order_summary.subcontract_order_summary import execute
from erpnext.buying.report.subcontracted_item_to_be_received.test_subcontracted_item_to_be_received import (
	make_subcontracting_order,
)
from erpnext.controllers.tests.test_subcontracting_controller import (
	get_subcontracting_order,
	make_bom_for_subcontracted_items,
	make_raw_materials,
	make_service_items,
	make_subcontracted_items,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSubcontractOrderSummary(ERPNextTestSuite):
	def setUp(self):
		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()

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

	def test_restricted_user_sees_only_permitted_suppliers(self):
		permitted = get_subcontracting_order()
		other = get_subcontracting_order()
		frappe.db.set_value("Subcontracting Order", other.name, "supplier", "_Test Supplier 1")
		user = create_user("subcontract_summary_restricted@example.com", "Purchase User").name
		add_user_permission("Supplier", "_Test Supplier", user)

		filters = frappe._dict(
			order_type="Subcontracting Order",
			company="_Test Company",
			from_date=add_days(today(), -1),
			to_date=add_days(today(), 1),
		)
		with self.set_user(user):
			orders = {row.get("order_id") for row in execute(filters)[1] if row.get("order_id")}

		self.assertIn(permitted.name, orders)
		self.assertNotIn(other.name, orders)
