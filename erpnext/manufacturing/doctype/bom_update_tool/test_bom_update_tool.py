# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, timeout

from erpnext.manufacturing.doctype.bom_update_log.test_bom_update_log import (
	update_cost_in_all_boms_in_test,
)
from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import enqueue_replace_bom
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.tests.permission_test_utils import (
	OTHER_COMPANY,
	as_user,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	make_company_fenced_user,
	make_fenced_user,
)

test_records = frappe.get_test_records("BOM")


class TestBOMUpdateTool(FrappeTestCase):
	"Test major functions run via BOM Update Tool."

	def tearDown(self):
		frappe.db.rollback()

	@timeout
	def test_replace_bom(self):
		current_bom = "BOM-_Test Item Home Desktop Manufactured-001"

		bom_doc = frappe.copy_doc(test_records[0])
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


class TestBOMUpdateToolPermissions(FrappeTestCase):
	def setUp(self):
		self.current_bom = "BOM-_Test Item Home Desktop Manufactured-001"
		new_bom = frappe.copy_doc(test_records[0])
		new_bom.items[1].item_code = "_Test Item"
		new_bom.insert()
		self.new_bom = new_bom.name
		self.parents = frappe.get_all(
			"BOM Item",
			filters={"bom_no": self.current_bom, "docstatus": 1, "parenttype": "BOM"},
			pluck="parent",
			distinct=True,
		)
		self.assertTrue(self.parents)

	def tearDown(self):
		frappe.db.rollback()

	def replace_kwargs(self, current_bom=None):
		return {"boms": {"current_bom": current_bom or self.current_bom, "new_bom": self.new_bom}}

	def parents_still_on_current_bom(self):
		return frappe.db.exists("BOM Item", {"bom_no": self.current_bom, "docstatus": 1, "parenttype": "BOM"})

	def test_enqueue_replace_bom_refuses_a_parent_outside_the_company_fence(self):
		frappe.db.set_value("BOM", self.parents[0], "company", OTHER_COMPANY)
		fenced = make_company_fenced_user(
			"bom-replace-company@example.com", ["Manufacturing Manager"], "_Test Company"
		)
		with as_user(fenced):
			assert_refused(self, enqueue_replace_bom, **self.replace_kwargs())
		self.assertTrue(self.parents_still_on_current_bom())

	def test_enqueue_replace_bom_refuses_ancestors_outside_a_bom_fence(self):
		fenced = make_fenced_user(
			"bom-replace-bom@example.com",
			["Manufacturing Manager"],
			[("BOM", self.current_bom), ("BOM", self.new_bom)],
		)
		with as_user(fenced):
			assert_refused_without(self, self.parents, enqueue_replace_bom, **self.replace_kwargs())
		self.assertTrue(self.parents_still_on_current_bom())

	def test_enqueue_replace_bom_refuses_malformed_boms(self):
		user = make_fenced_user("bom-replace-malformed@example.com", ["Manufacturing Manager"])
		with as_user(user):
			assert_refused_for_names(self, enqueue_replace_bom, self.replace_kwargs, [], caller_supplied=True)

	def test_enqueue_replace_bom_allows_an_unfenced_manufacturing_manager(self):
		user = make_fenced_user("bom-replace-open@example.com", ["Manufacturing Manager"])
		with as_user(user):
			enqueue_replace_bom(**self.replace_kwargs())
		self.assertFalse(self.parents_still_on_current_bom())
