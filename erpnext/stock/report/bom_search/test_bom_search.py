from __future__ import unicode_literals
import frappe, unittest
from erpnext.stock.report.bom_search.bom_search import execute
from erpnext.manufacturing.report.bom_explorer.test_bom_explorer import get_bom,get_item
from frappe.utils import now, add_to_date

class TestBOMSearch(unittest.TestCase):

	def test_bom_search(self):
		root_item = get_item("BOM Search Root Item")
		item_1 = get_item("child_item_1")
		item_2 = get_item("child_item_2")
		item_3 = get_item("child_item_3")
		item_4 = get_item("child_item_4")
		item_5 = get_item("child_item_5")

		bom = get_bom(root_item.name, [item_1.name, item_2.name, item_3.name, item_4.name, item_5.name])

		cols, rows = execute(filters = frappe._dict({
			"item1": item_1.name,
			"item2": item_2.name,
			"item3": item_3.name,
			"item4": item_4.name,
			"item5": item_5.name,
		}))

		self.assertEquals(rows[0][0], bom.name)





