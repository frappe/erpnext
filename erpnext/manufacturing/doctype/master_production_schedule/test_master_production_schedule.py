# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.manufacturing.doctype.master_production_schedule.master_production_schedule import (
	get_mps_details,
	get_own_lead_time,
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

	def test_demand_rows_keep_their_warehouse(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		item = make_item("_Test MPS Warehouse Item", {"is_stock_item": 1}).name
		order = make_sales_order(item_code=item, qty=3, warehouse="Stores - _TC", do_not_submit=True)
		order.append(
			"items", {**order.items[0].as_dict(), "name": None, "qty": 4, "warehouse": "Finished Goods - _TC"}
		)
		order.submit()

		mps = make_mps(to_date=add_days(today(), 30), sales_orders=[order.name])
		mps.get_actual_demand()

		self.assertEqual(
			sorted((row.warehouse, row.planned_qty) for row in mps.items),
			[("Finished Goods - _TC", 4), ("Stores - _TC", 3)],
		)

	def test_delivery_schedules_leave_out_delivered_and_closed_orders(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			create_dn_against_so,
			make_sales_order,
		)

		item = make_item("_Test MPS Schedule Item", {"is_stock_item": 1}).name
		orders = []
		for qty in (10, 4):
			order = make_sales_order(item_code=item, qty=qty)
			order.create_delivery_schedule(
				order.items[0].as_dict(),
				[
					{"delivery_date": add_days(today(), 5), "qty": qty / 2},
					{"delivery_date": add_days(today(), 10), "qty": qty / 2},
				],
			)
			orders.append(order)

		delivered, closed = orders
		create_dn_against_so(delivered.name, delivered_qty=6)
		closed.reload()
		closed.update_status("Closed")

		mps = make_mps(
			to_date=add_days(today(), 30), select_items=[item], sales_orders=[o.name for o in orders]
		)
		mps.get_actual_demand()

		self.assertEqual([(row.item_code, row.planned_qty) for row in mps.items], [(item, 4)])

	def test_later_schedule_of_a_partly_delivered_order_stays_out_of_the_window(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			create_dn_against_so,
			make_sales_order,
		)

		item = make_item("_Test MPS Later Schedule Item", {"is_stock_item": 1}).name
		order = make_sales_order(item_code=item, qty=100)
		order.create_delivery_schedule(
			order.items[0].as_dict(),
			[
				{"delivery_date": add_days(today(), 5), "qty": 50},
				{"delivery_date": add_days(today(), 30), "qty": 50},
			],
		)
		create_dn_against_so(order.name, delivered_qty=50)

		mps = make_mps(to_date=add_days(today(), 10), select_items=[item], sales_orders=[order.name])
		mps.get_actual_demand()

		self.assertEqual(mps.items, [])

	def test_mps_details_need_read_permission(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user

		mps = make_mps(to_date=add_days(today(), 30))
		user = create_user("mps-sales-user@example.com", "Sales User")

		with self.set_user(user.name):
			self.assertRaises(frappe.PermissionError, get_mps_details, mps.name)

		self.assertEqual(get_mps_details(mps.name).name, mps.name)

	def test_lead_time_is_not_int_truncated(self):
		lead_time = frappe._dict(manufacturing_time_in_mins=720, shift_time_in_hours=8, buffer_time=0)
		self.assertAlmostEqual(get_own_lead_time(lead_time, 1, True), 1.5, places=2)

	def test_cumulative_lead_time_follows_the_longest_path(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		rm_1, rm_2, rm_3, sub_item, fg_item = (
			make_item(f"_Test MPS Lead {name}", {"is_stock_item": 1}).name
			for name in ("RM 1", "RM 2", "RM 3", "Sub", "FG")
		)
		sub_bom = make_bom(item=sub_item, raw_materials=[rm_3])
		fg_bom = make_bom(item=fg_item, raw_materials=[rm_1, rm_2, sub_item])
		self.assertEqual(
			frappe.db.get_value("BOM Item", {"parent": fg_bom.name, "item_code": sub_item}, "bom_no"),
			sub_bom.name,
		)

		make_lead_time(fg_item, buffer_time=1, manufacturing_time_in_mins=5, shift_time_in_hours=8)
		for item in (rm_1, rm_2, rm_3):
			make_lead_time(item, purchase_time=10)
		make_lead_time(sub_item, buffer_time=2)

		order = make_sales_order(item_code=fg_item, qty=1000)
		mps = make_mps(to_date=add_days(today(), 30), sales_orders=[order.name])
		mps.get_actual_demand()

		self.assertEqual(mps.items[0].cumulative_lead_time, 24)


def make_lead_time(item_code, **values):
	frappe.db.delete("Item Lead Time", {"item_code": item_code})
	frappe.get_doc({"doctype": "Item Lead Time", "item_code": item_code, **values}).insert()


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
