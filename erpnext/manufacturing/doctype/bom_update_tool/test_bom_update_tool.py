# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import update_cost

test_records = frappe.get_test_records('BOM')

class TestBOMUpdateTool(unittest.TestCase):
	def test_replace_bom(self):
		current_bom = "BOM-_Test Item Home Desktop Manufactured-001"

		bom_doc = frappe.copy_doc(test_records[0])
		bom_doc.items[1].item_code = "_Test Item"
		bom_doc.insert()

		update_tool = frappe.get_doc("BOM Update Tool")
		update_tool.current_bom = current_bom
		update_tool.new_bom = bom_doc.name
		update_tool.replace_bom()

		self.assertFalse(frappe.db.sql("select name from `tabBOM Item` where bom_no=%s", current_bom))
		self.assertTrue(frappe.db.sql("select name from `tabBOM Item` where bom_no=%s", bom_doc.name))

		# reverse, as it affects other testcases
		update_tool.current_bom = bom_doc.name
		update_tool.new_bom = current_bom
		update_tool.replace_bom()

	def test_bom_cost(self):
		for item in ["BOM Cost Test Item 1", "BOM Cost Test Item 2", "BOM Cost Test Item 3"]:
			item_doc = create_item(item, valuation_rate=100)
			if item_doc.valuation_rate != 100.00:
				frappe.db.set_value("Item", item_doc.name, "valuation_rate", 100)

		bom_no = frappe.db.get_value('BOM', {'item': 'BOM Cost Test Item 1'}, "name")
		if not bom_no:
			doc = make_bom(item = 'BOM Cost Test Item 1',
				raw_materials =['BOM Cost Test Item 2', 'BOM Cost Test Item 3'], currency="INR")
		else:
			doc = frappe.get_doc("BOM", bom_no)

		self.assertEquals(doc.total_cost, 200)

		frappe.db.set_value("Item", "BOM Cost Test Item 2", "valuation_rate", 200)
		update_cost()

		doc.load_from_db()
		self.assertEquals(doc.total_cost, 300)

		frappe.db.set_value("Item", "BOM Cost Test Item 2", "valuation_rate", 100)
		update_cost()

		doc.load_from_db()
		self.assertEquals(doc.total_cost, 200)
