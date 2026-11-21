# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.report.bom_operations_time.bom_operations_time import execute
from erpnext.stock.doctype.item.test_item import make_item

OPERATION = "_Test BOM Ops Time Operation"
WORKSTATION = "_Test BOM Ops Time Workstation"
OTHER_OPERATION = "_Test BOM Ops Time Operation 2"
OTHER_WORKSTATION = "_Test BOM Ops Time Workstation 2"
TIME_IN_MINS = 45


class TestBOMOperationsTime(FrappeTestCase):
	def setUp(self):
		ensure_workstation_and_operation(WORKSTATION, OPERATION)
		self.rm_item = make_item(properties={"is_stock_item": 1, "valuation_rate": 100}).name

	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **filters):
		return execute(frappe._dict(filters))[1]

	def test_sub_assembly_bom_count_on_every_row(self):
		ensure_workstation_and_operation(OTHER_WORKSTATION, OTHER_OPERATION)
		sub_assembly = make_item(properties={"is_stock_item": 1}).name
		sub_bom = build_bom_with_operation(
			sub_assembly, self.rm_item, OPERATION, WORKSTATION, do_not_submit=True
		)
		sub_bom.append(
			"operations",
			{
				"operation": OTHER_OPERATION,
				"workstation": OTHER_WORKSTATION,
				"time_in_mins": 30,
				"hour_rate": 100,
			},
		)
		sub_bom.save()
		sub_bom.submit()

		make_parent_bom(sub_assembly, sub_bom.name, rows=2).submit()
		make_parent_bom(sub_assembly, sub_bom.name)
		cancelled = make_parent_bom(sub_assembly, sub_bom.name)
		cancelled.submit()
		cancelled.cancel()
		inactive = make_parent_bom(sub_assembly, sub_bom.name)
		inactive.submit()
		inactive.db_set("is_active", 0)

		rows = self.run_report(bom_id=[sub_bom.name])

		self.assertEqual(len(rows), 2)
		self.assertEqual([row.used_as_subassembly_items for row in rows], [1, 1])


def ensure_workstation_and_operation(workstation, operation):
	if not frappe.db.exists("Workstation", workstation):
		frappe.get_doc({"doctype": "Workstation", "workstation_name": workstation}).insert(
			ignore_permissions=True
		)

	if not frappe.db.exists("Operation", operation):
		frappe.get_doc({"doctype": "Operation", "name": operation, "workstation": workstation}).insert(
			ignore_permissions=True
		)


def build_bom_with_operation(fg_item, rm_item, operation, workstation, do_not_submit=False):
	bom = make_bom(
		item=fg_item,
		raw_materials=[rm_item],
		with_operations=1,
		do_not_save=True,
	)
	bom.append(
		"operations",
		{
			"operation": operation,
			"workstation": workstation,
			"time_in_mins": TIME_IN_MINS,
			"hour_rate": 100,
		},
	)
	bom.insert(ignore_permissions=True)
	if not do_not_submit:
		bom.submit()
	return bom


def make_parent_bom(sub_assembly, sub_bom, rows=1):
	bom = make_bom(
		item=make_item(properties={"is_stock_item": 1}).name,
		raw_materials=[sub_assembly] * rows,
		do_not_save=True,
	)
	for row in bom.items:
		row.bom_no = sub_bom
	bom.insert(ignore_permissions=True)
	return bom
