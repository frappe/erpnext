# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.manufacturing.doctype.master_production_schedule.master_production_schedule import (
	get_item_lead_time,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestMasterProductionSchedule(ERPNextTestSuite):
	def test_to_date_is_kept_on_save(self):
		mps = make_mps(to_date=add_days(today(), 30))
		self.assertEqual(getdate(mps.to_date), getdate(add_days(today(), 30)))

		mps.save()
		self.assertEqual(getdate(mps.to_date), getdate(add_days(today(), 30)))

	def test_actual_demand_is_pending_qty_of_selected_items(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			create_dn_against_so,
			make_sales_order,
		)
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		item = make_item("_Test MPS Demand Item", {"is_stock_item": 1}).name
		other_item = make_item("_Test MPS Other Item", {"is_stock_item": 1}).name

		delivered = make_sales_order(item_code=item, qty=10)
		create_dn_against_so(delivered.name, delivered_qty=10)
		closed = make_sales_order(item_code=item, qty=4)
		closed.update_status("Closed")
		partial = make_sales_order(item_code=item, qty=5)
		create_dn_against_so(partial.name, delivered_qty=2)
		unselected = make_sales_order(item_code=other_item, qty=7)

		request = make_material_request(
			item_code=item,
			qty=6,
			uom="Nos",
			material_request_type="Manufacture",
			schedule_date=add_days(today(), 5),
		)
		request.items[0].db_set("ordered_qty", 6)

		mps = make_mps(
			to_date=add_days(today(), 30),
			select_items=[item],
			sales_orders=[delivered.name, closed.name, partial.name, unselected.name],
			material_requests=[request.name],
		)
		mps.get_actual_demand()

		self.assertEqual([(row.item_code, row.planned_qty) for row in mps.items], [(item, 3)])

	def test_cumulative_lead_time_is_not_int_truncated(self):
		"""cumulative_lead_time = manufacturing_time_in_mins / 1440 + purchase_time + buffer_time.
		manufacturing_time_in_mins is an Int column; integer/integer division truncates on
		PostgreSQL (720/1440 -> 0) while MariaDB yields 0.5, changing the planned release date."""
		item = make_item("_Test MPS Lead Time Item", {"is_stock_item": 1}).name
		# idempotent across re-runs / a shared CI database
		frappe.db.delete("Item Lead Time", {"item_code": item})
		frappe.get_doc(
			{
				"doctype": "Item Lead Time",
				"item_code": item,
				"manufacturing_time_in_mins": 720,
				"purchase_time": 0,
				"buffer_time": 0,
			}
		).insert()
		# 720 / 1440 = 0.5; a truncating integer division on PostgreSQL would give 0.
		self.assertAlmostEqual(float(get_item_lead_time(item)), 0.5, places=2)


def make_mps(**args):
	args = frappe._dict(args)
	mps = frappe.get_doc(
		{
			"doctype": "Master Production Schedule",
			"company": args.company or "_Test Company",
			"posting_date": today(),
			"from_date": args.from_date or today(),
			"to_date": args.to_date,
			"parent_warehouse": args.parent_warehouse,
			"select_items": [{"item_code": item} for item in args.select_items or []],
			"sales_orders": [{"sales_order": name} for name in args.sales_orders or []],
			"material_requests": [{"material_request": name} for name in args.material_requests or []],
		}
	)
	mps.insert()
	return mps
