# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from erpnext.manufacturing.doctype.operation.test_operation import make_operation
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.stock.doctype.item.test_item import make_item


class TestWorkstationType(FrappeTestCase):
	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 0})
	def test_type_without_workstation_gives_a_clear_error(self):
		workstation_type = create_workstation_type(workstation_type="_Test WT No Workstation").name

		fg_item = make_item("_Test FG No Workstation", {"is_stock_item": 1}).name
		rm_item = make_item("_Test RM No Workstation", {"is_stock_item": 1}).name
		operation = make_operation(operation="_Test Op No Workstation").name
		bom = make_bom(item=fg_item, raw_materials=[rm_item], with_operations=1, do_not_submit=True)
		bom.append(
			"operations",
			{
				"operation": operation,
				"workstation_type": workstation_type,
				"time_in_mins": 60,
				"hour_rate": 100,
			},
		)
		bom.submit()

		self.assertRaisesRegex(
			frappe.ValidationError,
			"has no Workstation",
			make_wo_order_test_record,
			item=fg_item,
			bom_no=bom.name,
			qty=1,
		)

	def test_type_cost_change_reaches_its_workstations(self):
		workstation_type = create_workstation_type(
			workstation_type="_Test WT Rate Change", hour_rate_labour=500, hour_rate_rent=100
		)
		follows_type = make_workstation(
			workstation_name="_Test WS Rate Follows", workstation_type=workstation_type.name
		)
		own_rate = make_workstation(
			workstation_name="_Test WS Rate Own", workstation_type=workstation_type.name
		)
		own_rate.hour_rate_labour = 650
		own_rate.save()

		workstation_type.hour_rate_labour = 800
		workstation_type.hour_rate_rent = 0
		workstation_type.save()

		self.assertEqual(frappe.db.get_value("Workstation", follows_type.name, "hour_rate"), 800)
		self.assertEqual(frappe.db.get_value("Workstation", own_rate.name, "hour_rate"), 750)


def create_workstation_type(**args):
	args = frappe._dict(args)

	if workstation_type := frappe.db.exists("Workstation Type", args.workstation_type):
		return frappe.get_doc("Workstation Type", workstation_type)
	else:
		doc = frappe.new_doc("Workstation Type")
		doc.update(args)
		doc.insert()
		return doc
