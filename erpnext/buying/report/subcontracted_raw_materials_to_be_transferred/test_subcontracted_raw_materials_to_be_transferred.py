# Python bytecode 2.7 (62211)
# Embedded file name: /Users/anuragmishra/frappe-develop/apps/erpnext/erpnext/buying/report/subcontracted_raw_materials_to_be_transferred/test_subcontracted_raw_materials_to_be_transferred.py
# Compiled at: 2019-05-06 10:24:35
# Decompiled by https://python-decompiler.com

import frappe
from frappe.desk.query_report import run

from erpnext.buying.report.subcontracted_item_to_be_received.test_subcontracted_item_to_be_received import (
	get_report_filters,
	make_subcontracting_order,
)
from erpnext.buying.report.subcontracted_raw_materials_to_be_transferred.subcontracted_raw_materials_to_be_transferred import (
	execute,
)
from erpnext.controllers.subcontracting_controller import make_rm_stock_entry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestSubcontractedItemToBeTransferred(ERPNextTestSuite):
	def test_pending_and_transferred_qty(self):
		sco = make_subcontracting_order()

		# Material Receipt of RMs
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=100, basic_rate=100)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=100, basic_rate=100
		)

		transfer_subcontracted_raw_materials(sco)

		col, data = execute(
			filters=frappe._dict(
				{
					"order_type": "Subcontracting Order",
					"supplier": sco.supplier,
					"from_date": frappe.utils.get_datetime(
						frappe.utils.add_to_date(sco.transaction_date, days=-10)
					),
					"to_date": frappe.utils.get_datetime(
						frappe.utils.add_to_date(sco.transaction_date, days=10)
					),
				}
			)
		)
		sco.reload()

		sco_data = [row for row in data if row.get("subcontract_order") == sco.name]
		# Alphabetically sort to be certain of order
		sco_data = sorted(sco_data, key=lambda i: i["rm_item_code"])

		self.assertEqual(len(sco_data), 2)
		self.assertEqual(sco_data[0]["subcontract_order"], sco.name)

		self.assertEqual(sco_data[0]["rm_item_code"], "_Test Item")
		self.assertEqual(sco_data[0]["p_qty"], 8)
		self.assertEqual(sco_data[0]["transferred_qty"], 2)

		self.assertEqual(sco_data[1]["rm_item_code"], "_Test Item Home Desktop 100")
		self.assertEqual(sco_data[1]["p_qty"], 19)
		self.assertEqual(sco_data[1]["transferred_qty"], 1)

	def test_report_runs_from_desk(self):
		sco = make_subcontracting_order()

		filters = get_report_filters(sco)
		result = run("Subcontracted Raw Materials To Be Transferred", filters=filters)["result"]
		self.assertIn(sco.name, {row["subcontract_order"] for row in result if isinstance(row, dict)})

	def test_closed_order_is_not_listed(self):
		sco = make_subcontracting_order()
		sco.update_status("Closed")

		data = execute(get_report_filters(sco))[1]
		self.assertNotIn(sco.name, {row["subcontract_order"] for row in data})


def transfer_subcontracted_raw_materials(sco):
	# Order of supplied items fetched in SCO is flaky
	transfer_qty_map = {"_Test Item": 2, "_Test Item Home Desktop 100": 1}

	item_1 = sco.supplied_items[0].rm_item_code
	item_2 = sco.supplied_items[1].rm_item_code

	rm_items = [
		{
			"name": sco.supplied_items[0].name,
			"item_code": item_1,
			"rm_item_code": item_1,
			"item_name": item_1,
			"qty": transfer_qty_map[item_1],
			"warehouse": "_Test Warehouse - _TC",
			"rate": 100,
			"amount": 100 * transfer_qty_map[item_1],
			"stock_uom": "Nos",
		},
		{
			"name": sco.supplied_items[1].name,
			"item_code": item_2,
			"rm_item_code": item_2,
			"item_name": item_2,
			"qty": transfer_qty_map[item_2],
			"warehouse": "_Test Warehouse - _TC",
			"rate": 100,
			"amount": 100 * transfer_qty_map[item_2],
			"stock_uom": "Nos",
		},
	]
	se = frappe.get_doc(make_rm_stock_entry(sco.name, rm_items))
	se.from_warehouse = "_Test Warehouse - _TC"
	se.to_warehouse = "_Test Warehouse - _TC"
	se.stock_entry_type = "Send to Subcontractor"
	se.save()
	se.submit()
	return se
