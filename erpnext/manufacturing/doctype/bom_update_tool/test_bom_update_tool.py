# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import timeout

from erpnext.manufacturing.doctype.bom_update_log.test_bom_update_log import (
	update_cost_in_all_boms_in_test,
)
from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import enqueue_replace_bom
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_refused_for_names,
	assert_refused_without,
	make_fenced_user,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestBOMUpdateTool(ERPNextTestSuite):
	"Test major functions run via BOM Update Tool."

	def setUp(self):
		self.load_test_records("BOM")

	@timeout
	def test_replace_bom(self):
		current_bom = "BOM-_Test Item Home Desktop Manufactured-001"

		bom_doc = frappe.copy_doc(self.globalTestRecords["BOM"][0])
		bom_doc.items[1].item_code = "_Test Item"
		bom_doc.insert()

		boms = frappe._dict(current_bom=current_bom, new_bom=bom_doc.name)
		enqueue_replace_bom(boms=boms)

		self.assertFalse(frappe.db.exists("BOM Item", {"bom_no": current_bom, "docstatus": 1}))
		self.assertTrue(frappe.db.exists("BOM Item", {"bom_no": bom_doc.name, "docstatus": 1}))

	@timeout
	def test_bom_cost(self):
		for item in ["BOM Cost Test Item 1", "BOM Cost Test Item 2", "BOM Cost Test Item 3"]:
			item_doc = create_item(item, valuation_rate=100)
			if item_doc.valuation_rate != 100.00:
				frappe.db.set_value("Item", item_doc.name, "valuation_rate", 100)

		bom_no = frappe.db.get_value("BOM", {"item": "BOM Cost Test Item 1"}, "name")
		if not bom_no:
			doc = make_bom(
				item="BOM Cost Test Item 1",
				raw_materials=["BOM Cost Test Item 2", "BOM Cost Test Item 3"],
				currency="INR",
			)
		else:
			doc = frappe.get_doc("BOM", bom_no)

		self.assertEqual(doc.total_cost, 200)

		frappe.db.set_value("Item", "BOM Cost Test Item 2", "valuation_rate", 200)
		update_cost_in_all_boms_in_test()

		doc.load_from_db()
		self.assertEqual(doc.total_cost, 300)

		frappe.db.set_value("Item", "BOM Cost Test Item 2", "valuation_rate", 100)
		update_cost_in_all_boms_in_test()

		doc.load_from_db()
		self.assertEqual(doc.total_cost, 200)

	def test_bom_cost_refreshes_stale_price_list_exchange_rate(self):
		from erpnext.manufacturing.doctype.bom.test_bom import make_usd_bom, make_usd_buying_price_list
		from erpnext.manufacturing.doctype.bom_update_log.bom_updation_utils import update_cost_in_boms

		price_list = make_usd_buying_price_list(83)
		raw_material = create_item("_Test BOM Update USD Price List Item").name
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": raw_material,
				"price_list": price_list,
				"price_list_rate": 10,
			}
		).insert()
		bom = make_usd_bom(
			create_item("_Test BOM Update USD Price List FG").name,
			[{"item_code": raw_material, "qty": 1}],
			rm_cost_as_per="Price List",
			buying_price_list=price_list,
		)

		# saved before the BOM conversion rate applied to a price list in its currency
		bom.db_set("plc_conversion_rate", 83)
		update_cost_in_boms([bom.name])

		bom.load_from_db()
		self.assertEqual(bom.plc_conversion_rate, 80)
		self.assertEqual(bom.items[0].rate, 10)

	def test_replace_bom_requires_every_rewritten_bom_to_be_writable(self):
		current_bom = "BOM-_Test Item Home Desktop Manufactured-001"
		parent_bom = frappe.db.get_value("BOM Item", {"bom_no": current_bom, "parenttype": "BOM"}, "parent")
		bom_doc = frappe.copy_doc(self.globalTestRecords["BOM"][0])
		bom_doc.items[1].item_code = "_Test Item"
		bom_doc.insert()

		def current_kwargs(name):
			return {"boms": {"current_bom": name, "new_bom": bom_doc.name}}

		def new_kwargs(name):
			return {"boms": {"current_bom": current_bom, "new_bom": name}}

		fenced = make_fenced_user(
			"bom-fenced@example.com", ["Manufacturing Manager"], [("BOM", current_bom), ("BOM", bom_doc.name)]
		)
		with as_user(fenced):
			assert_refused_without(
				self,
				[parent_bom],
				enqueue_replace_bom,
				boms={"current_bom": current_bom, "new_bom": bom_doc.name},
			)
			assert_refused_for_names(self, enqueue_replace_bom, current_kwargs, [], caller_supplied=True)
			assert_refused_for_names(self, enqueue_replace_bom, new_kwargs, [], caller_supplied=True)
		allowed = make_fenced_user(
			"bom-fenced@example.com",
			["Manufacturing Manager"],
			[("BOM", current_bom), ("BOM", bom_doc.name), ("BOM", parent_bom)],
		)
		with as_user(allowed):
			enqueue_replace_bom(boms={"current_bom": current_bom, "new_bom": bom_doc.name})
		self.assertTrue(frappe.db.exists("BOM Item", {"bom_no": bom_doc.name, "parent": parent_bom}))
