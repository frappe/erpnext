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
	OTHER_COMPANY,
	as_user,
	assert_refused_for_names,
	assert_refused_without,
	make_company_fenced_user,
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

	def make_fenced_manufacturing_manager(self):
		return make_company_fenced_user(
			"bom_replace_fenced@example.com", ["Manufacturing Manager"], "_Test Company"
		)

	def make_fence_bom(self, item, company, rows):
		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"item": item,
				"company": company,
				"quantity": 1,
				"currency": "INR",
				"rm_cost_as_per": "Valuation Rate",
			}
		)
		for item_code, rate, bom_no in rows:
			bom.append("items", {"item_code": item_code, "qty": 1, "rate": rate, "bom_no": bom_no})
		bom.insert()
		bom.submit()
		return bom.name

	def make_fence_boms(self):
		for item_code in ["BOM Fence RM", "BOM Fence Sub", "BOM Fence FG", "BOM Fence Top"]:
			create_item(item_code, valuation_rate=10)
		current_bom = self.make_fence_bom("BOM Fence Sub", "_Test Company", [("BOM Fence RM", 10, None)])
		new_bom = self.make_fence_bom("BOM Fence Sub", "_Test Company", [("BOM Fence RM", 20, None)])
		return current_bom, new_bom

	def get_child_bom(self, parent, item_code):
		return frappe.db.get_value("BOM Item", {"parent": parent, "item_code": item_code}, "bom_no")

	def assert_replaced(self, update_log, parent_boms, new_bom):
		self.assertEqual(frappe.db.get_value("BOM Update Log", update_log.name, "status"), "Completed")
		for parent_bom in parent_boms:
			self.assertEqual(self.get_child_bom(parent_bom, "BOM Fence Sub"), new_bom)

	def test_enqueue_replace_bom_respects_company_user_permission(self):
		current_bom, new_bom = self.make_fence_boms()
		other_company_bom = self.make_fence_bom("BOM Fence Sub", OTHER_COMPANY, [("BOM Fence RM", 30, None)])
		parent_bom = self.make_fence_bom(
			"BOM Fence FG", "_Test Company", [("BOM Fence Sub", 10, current_bom)]
		)
		grandparent_bom = self.make_fence_bom(
			"BOM Fence Top", "_Test Company", [("BOM Fence FG", 10, parent_bom)]
		)
		user = self.make_fenced_manufacturing_manager()

		with as_user(user):
			assert_refused_without(
				self,
				[OTHER_COMPANY],
				enqueue_replace_bom,
				boms={"current_bom": other_company_bom, "new_bom": new_bom},
			)
			assert_refused_without(
				self,
				[OTHER_COMPANY],
				enqueue_replace_bom,
				boms={"current_bom": current_bom, "new_bom": other_company_bom},
			)
			self.assertEqual(self.get_child_bom(parent_bom, "BOM Fence Sub"), current_bom)

			update_log = enqueue_replace_bom(boms={"current_bom": current_bom, "new_bom": new_bom})

		self.assert_replaced(update_log, [parent_bom], new_bom)
		self.assertEqual(self.get_child_bom(grandparent_bom, "BOM Fence FG"), parent_bom)

	def test_enqueue_replace_bom_refuses_when_a_parent_bom_is_outside_company_permission(self):
		current_bom, new_bom = self.make_fence_boms()
		parent_bom = self.make_fence_bom(
			"BOM Fence FG", "_Test Company", [("BOM Fence Sub", 10, current_bom)]
		)
		other_company_parent_bom = self.make_fence_bom(
			"BOM Fence FG", OTHER_COMPANY, [("BOM Fence Sub", 10, current_bom)]
		)
		fenced_user = self.make_fenced_manufacturing_manager()
		unfenced_user = make_fenced_user("bom_replace_unfenced@example.com", ["Manufacturing Manager"])

		with as_user(fenced_user):
			assert_refused_without(
				self,
				[other_company_parent_bom, OTHER_COMPANY],
				enqueue_replace_bom,
				boms={"current_bom": current_bom, "new_bom": new_bom},
			)

		self.assertEqual(self.get_child_bom(other_company_parent_bom, "BOM Fence Sub"), current_bom)
		self.assertEqual(self.get_child_bom(parent_bom, "BOM Fence Sub"), current_bom)

		with as_user(unfenced_user):
			update_log = enqueue_replace_bom(boms={"current_bom": current_bom, "new_bom": new_bom})

		self.assert_replaced(update_log, [other_company_parent_bom, parent_bom], new_bom)

	def test_enqueue_replace_bom_refuses_when_an_ancestor_bom_is_outside_company_permission(self):
		current_bom, new_bom = self.make_fence_boms()
		parent_bom = self.make_fence_bom(
			"BOM Fence FG", "_Test Company", [("BOM Fence Sub", 10, current_bom)]
		)
		other_company_grandparent_bom = self.make_fence_bom(
			"BOM Fence Top", OTHER_COMPANY, [("BOM Fence FG", 10, parent_bom)]
		)
		fenced_user = self.make_fenced_manufacturing_manager()

		with as_user(fenced_user):
			assert_refused_without(
				self,
				[other_company_grandparent_bom, OTHER_COMPANY],
				enqueue_replace_bom,
				boms={"current_bom": current_bom, "new_bom": new_bom},
			)

		self.assertEqual(self.get_child_bom(parent_bom, "BOM Fence Sub"), current_bom)
		frappe.get_doc("BOM", other_company_grandparent_bom).cancel()

		other_company_new_bom_parent = self.make_fence_bom(
			"BOM Fence FG", OTHER_COMPANY, [("BOM Fence Sub", 10, new_bom)]
		)
		with as_user(fenced_user):
			assert_refused_without(
				self,
				[other_company_new_bom_parent, OTHER_COMPANY],
				enqueue_replace_bom,
				boms={"current_bom": current_bom, "new_bom": new_bom},
			)

		self.assertEqual(self.get_child_bom(parent_bom, "BOM Fence Sub"), current_bom)
		frappe.get_doc("BOM", other_company_new_bom_parent).cancel()

		with as_user(fenced_user):
			update_log = enqueue_replace_bom(boms={"current_bom": current_bom, "new_bom": new_bom})

		self.assert_replaced(update_log, [parent_bom], new_bom)

	def test_enqueue_replace_bom_refuses_forbidden_missing_and_malformed_names(self):
		current_bom, new_bom = self.make_fence_boms()
		other_company_bom = self.make_fence_bom("BOM Fence Sub", OTHER_COMPANY, [("BOM Fence RM", 30, None)])
		user = self.make_fenced_manufacturing_manager()
		forbidden = [[current_bom, other_company_bom]]

		def as_current_bom(name):
			return {"boms": {"current_bom": name, "new_bom": new_bom}}

		def as_new_bom(name):
			return {"boms": {"current_bom": current_bom, "new_bom": name}}

		with as_user(user):
			for build_kwargs in [as_current_bom, as_new_bom]:
				assert_refused_without(
					self, [OTHER_COMPANY], enqueue_replace_bom, **build_kwargs(other_company_bom)
				)
				assert_refused_for_names(
					self, enqueue_replace_bom, build_kwargs, forbidden, caller_supplied=True
				)

		self.assertFalse(frappe.db.exists("BOM Update Log", {"current_bom": current_bom}))
