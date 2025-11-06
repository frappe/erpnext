# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestSubcontractingBOM(FrappeTestCase):
	def test_get_subcontracting_boms_for_service_item_TC_S_196(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import get_subcontracting_boms_for_service_item
		from erpnext.stock.doctype.item.test_item import make_item



		service_item = make_item("Test Service Item", {
			"is_stock_item": 0,

		})

		finished_good = make_item("Test Finished Good", {
			"is_stock_item": 1,
			"is_sub_contracted_item": 1, 

		})
	

		bom = make_bom(item=finished_good.name, raw_materials=[service_item.name])
		sub_bom = create_subcontracting_bom(
			finished_good=finished_good.name,
			finished_good_uom="Nos",
			finished_good_bom=bom,
			service_item=service_item.name,
			service_item_uom="Nos"
		)

		result = get_subcontracting_boms_for_service_item(service_item.name)
		
		self.assertIn(sub_bom.finished_good, result)
		self.assertEqual(result[sub_bom.finished_good]["name"], sub_bom.name)


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
