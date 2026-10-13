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
