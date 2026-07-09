# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import now, today

from erpnext.templates.pages.material_request_info import get_more_items_info
from erpnext.tests.utils import ERPNextTestSuite


class TestMaterialRequestInfo(ERPNextTestSuite):
	"""Covers the two converted queries in ``get_more_items_info``: the query-builder
	join that links Work Orders (via Work Order Item) to a Material Request's items,
	and the ``SUM(transfer_qty)`` aggregate over submitted Stock Entry Detail rows that
	feeds ``item.delivered_qty``.
	"""

	def setUp(self):
		self.item_code = "_Test Item"
		self.company = "_Test Company"

		# A submitted Material Request that the page is rendered for.
		self.material_request = self._make_material_request()

		# A Work Order whose child Work Order Item references the same item.
		# The converted query joins Work Order Item -> Work Order on this item.
		self.work_order = self._make_linked_work_order(self.material_request.name)

	def _make_material_request(self):
		mr = frappe.new_doc("Material Request")
		mr.material_request_type = "Manufacture"
		mr.company = self.company
		mr.append(
			"items",
			{
				"item_code": self.item_code,
				"qty": 5,
				"uom": "_Test UOM",
				"conversion_factor": 1,
				"schedule_date": today(),
				"warehouse": "_Test Warehouse - _TC",
			},
		)
		mr.insert()
		mr.submit()
		return mr

	def _make_linked_work_order(self, material_request):
		"""Insert a Work Order + Work Order Item row directly.

		We avoid the BOM-driven Work Order controller (heavy, needs a default
		BOM and a submit cycle) because the query under test only reads the
		columns we set here: ``name``, ``status`` and ``consumed_qty``.
		"""
		wo = frappe.new_doc("Work Order")
		wo.production_item = self.item_code
		wo.item_name = self.item_code
		wo.qty = 5
		wo.company = self.company
		wo.fg_warehouse = "_Test Warehouse - _TC"
		wo.wip_warehouse = "_Test Warehouse - _TC"
		wo.planned_start_date = now()
		wo.material_request = material_request
		wo.status = "Not Started"  # not in the excluded set
		wo.bom_no = "TEST-BOM-MRI"  # placeholder; never read by the query
		wo.flags.ignore_validate = True
		wo.flags.ignore_mandatory = True
		wo.flags.name_set = True
		wo.name = frappe.generate_hash("wo-mri", 12)
		wo.db_insert()

		wo_item = frappe.new_doc("Work Order Item")
		wo_item.parent = wo.name
		wo_item.parenttype = "Work Order"
		wo_item.parentfield = "required_items"
		wo_item.idx = 1
		wo_item.item_code = self.item_code
		wo_item.item_name = self.item_code
		wo_item.required_qty = 5
		wo_item.consumed_qty = 0  # the query filters on consumed_qty == 0
		wo_item.flags.name_set = True
		wo_item.name = frappe.generate_hash("woi-mri", 12)
		wo_item.db_insert()

		return wo

	def _make_stock_entry_detail(self, transfer_qty, docstatus=1):
		"""Insert a Stock Entry Detail row directly (parentless) for this MR + item.

		The converted ``delivered_qty`` aggregate reads the child table alone
		(``SUM(transfer_qty)`` filtered by material_request/item_code/docstatus), so a
		parentless row with the docstatus set is enough to exercise it.
		"""
		sed = frappe.new_doc("Stock Entry Detail")
		sed.parent = frappe.generate_hash("se-mri", 12)
		sed.parenttype = "Stock Entry"
		sed.parentfield = "items"
		sed.idx = 1
		sed.item_code = self.item_code
		sed.item_name = self.item_code
		sed.uom = "_Test UOM"
		sed.stock_uom = "_Test UOM"
		sed.conversion_factor = 1
		sed.qty = transfer_qty
		sed.transfer_qty = transfer_qty
		sed.material_request = self.material_request.name
		sed.docstatus = docstatus
		sed.flags.name_set = True
		sed.name = frappe.generate_hash("sed-mri", 12)
		sed.db_insert()
		return sed

	def test_delivered_qty_sums_submitted_stock_entry_details(self):
		# Two submitted rows for this MR + item must sum; a draft (docstatus 0) row must
		# be excluded by the converted SUM(transfer_qty) aggregate.
		self._make_stock_entry_detail(transfer_qty=3, docstatus=1)
		self._make_stock_entry_detail(transfer_qty=4, docstatus=1)
		self._make_stock_entry_detail(transfer_qty=99, docstatus=0)  # draft -> ignored

		items = [frappe._dict({"item_code": self.item_code})]
		result = get_more_items_info(items, self.material_request.name)

		self.assertEqual(result[0].delivered_qty, 7.0)

	def test_delivered_qty_is_zero_when_no_stock_entry(self):
		# No matching Stock Entry Detail -> SUM is NULL -> flt(None) must coerce to 0.0.
		items = [frappe._dict({"item_code": self.item_code})]
		result = get_more_items_info(items, self.material_request.name)

		self.assertEqual(result[0].delivered_qty, 0.0)

	def test_converted_query_returns_linked_work_order(self):
		items = [frappe._dict({"item_code": self.item_code})]

		result = get_more_items_info(items, self.material_request.name)

		# Helper mutates and returns the same list of items.
		self.assertEqual(len(result), 1)
		item = result[0]

		work_orders = item.work_orders
		self.assertIsInstance(work_orders, list)

		# Our seeded Work Order must be present with well-formed columns.
		names = {wo.name for wo in work_orders}
		self.assertIn(self.work_order.name, names)

		seeded = next(wo for wo in work_orders if wo.name == self.work_order.name)
		self.assertEqual(seeded.status, "Not Started")
		self.assertEqual(seeded.consumed_qty, 0)
		# Selected columns are exactly those projected by the query.
		self.assertEqual(set(seeded.keys()), {"name", "status", "consumed_qty"})

	def test_excluded_status_work_order_is_filtered_out(self):
		# Flip the seeded Work Order to an excluded status; the query must drop it.
		frappe.db.set_value("Work Order", self.work_order.name, "status", "Completed")

		items = [frappe._dict({"item_code": self.item_code})]
		result = get_more_items_info(items, self.material_request.name)

		names = {wo.name for wo in result[0].work_orders}
		self.assertNotIn(self.work_order.name, names)
