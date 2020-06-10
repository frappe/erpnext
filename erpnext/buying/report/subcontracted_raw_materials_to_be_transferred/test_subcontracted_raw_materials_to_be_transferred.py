# Python bytecode 2.7 (62211)
# Embedded file name: /Users/anuragmishra/frappe-develop/apps/erpnext/erpnext/buying/report/subcontracted_raw_materials_to_be_transferred/test_subcontracted_raw_materials_to_be_transferred.py
# Compiled at: 2019-05-06 10:24:35
# Decompiled by https://python-decompiler.com
from __future__ import unicode_literals
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.purchase_order.purchase_order import make_rm_stock_entry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.buying.report.subcontracted_raw_materials_to_be_transferred.subcontracted_raw_materials_to_be_transferred import execute
import json, frappe, unittest

class TestSubcontractedItemToBeReceived(unittest.TestCase):

	def test_pending_and_received_qty(self):
		po = create_purchase_order(item_code='_Test FG Item', is_subcontracted='Yes')
		make_stock_entry(item_code='_Test Item', target='_Test Warehouse 1 - _TC', qty=100, basic_rate=100)
		make_stock_entry(item_code='_Test Item Home Desktop 100', target='_Test Warehouse 1 - _TC', qty=100, basic_rate=100)
		transfer_subcontracted_raw_materials(po.name)
		col, data = execute(filters=frappe._dict({'supplier': po.supplier,
		   'from_date': frappe.utils.get_datetime(frappe.utils.add_to_date(po.transaction_date, days=-10)),
		   'to_date': frappe.utils.get_datetime(frappe.utils.add_to_date(po.transaction_date, days=10))}))
		self.assertEqual(data[0]['purchase_order'], po.name)
		self.assertIn(data[0]['rm_item_code'], ['_Test Item', '_Test Item Home Desktop 100'])
		self.assertIn(data[0]['p_qty'], [9, 18])
		self.assertIn(data[0]['t_qty'], [1, 2])

		self.assertEqual(data[1]['purchase_order'], po.name)
		self.assertIn(data[1]['rm_item_code'], ['_Test Item', '_Test Item Home Desktop 100'])
		self.assertIn(data[1]['p_qty'], [9, 18])
		self.assertIn(data[1]['t_qty'], [1, 2])


def transfer_subcontracted_raw_materials(po):
	rm_item = [
	 {'item_code': '_Test Item', 'rm_item_code': '_Test Item', 'item_name': '_Test Item', 'qty': 1,
		'warehouse': '_Test Warehouse - _TC', 'rate': 100, 'amount': 100, 'stock_uom': 'Nos'},
	 {'item_code': '_Test Item Home Desktop 100', 'rm_item_code': '_Test Item Home Desktop 100', 'item_name': '_Test Item Home Desktop 100', 'qty': 2,
		'warehouse': '_Test Warehouse - _TC', 'rate': 100, 'amount': 200, 'stock_uom': 'Nos'}]
	rm_item_string = json.dumps(rm_item)
	se = frappe.get_doc(make_rm_stock_entry(po, rm_item_string))
	se.to_warehouse = '_Test Warehouse 1 - _TC'
	se.stock_entry_type = 'Send to Subcontractor'
	se.save()
	se.submit()