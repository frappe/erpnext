# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
	get_subcontracting_boms_for_finished_goods,
	get_subcontracting_boms_for_service_item,
)
from erpnext.tests.permission_test_utils import as_user, make_fenced_user


class TestSubcontractingBOM(FrappeTestCase):
	def test_lookups_need_order_read_permission(self):
		finished_good = make_item(
			"Subcontracting BOM Lookup FG", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		)
		raw_material = make_item("Subcontracting BOM Lookup RM", {"is_stock_item": 1})
		finished_good_bom = make_bom(item=finished_good.name, raw_materials=[raw_material.name])
		service_item = make_item("Subcontracting BOM Lookup Service Item", {"is_stock_item": 0})
		create_subcontracting_bom(
			finished_good=finished_good.name,
			finished_good_bom=finished_good_bom.name,
			service_item=service_item.name,
		)
		purchase_user = make_fenced_user("subcontracting-bom-purchase@example.com", ["Purchase User"])
		website_user = make_fenced_user("subcontracting-bom-website@example.com", [])

		with as_user(purchase_user):
			subcontracting_bom = get_subcontracting_boms_for_finished_goods(finished_good.name)
		self.assertEqual(subcontracting_bom.service_item, service_item.name)
		self.assertNotIn("owner", subcontracting_bom)

		with as_user(website_user):
			self.assertRaises(
				frappe.PermissionError, get_subcontracting_boms_for_finished_goods, finished_good.name
			)
			self.assertRaises(
				frappe.PermissionError, get_subcontracting_boms_for_service_item, service_item.name
			)


def create_subcontracting_bom(**kwargs):
	kwargs = frappe._dict(kwargs)

	doc = frappe.new_doc("Subcontracting BOM")
	doc.is_active = kwargs.is_active or 1
	doc.finished_good = kwargs.finished_good
	doc.finished_good_uom = kwargs.finished_good_uom
	doc.finished_good_qty = kwargs.finished_good_qty or 1
	doc.finished_good_bom = kwargs.finished_good_bom
	doc.service_item = kwargs.service_item
	doc.service_item_uom = kwargs.service_item_uom
	doc.service_item_qty = kwargs.service_item_qty or 1
	doc.save()

	return doc
