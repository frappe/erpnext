# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom import (
	finished_good_bom_query,
	get_subcontracting_boms_for_finished_goods,
)
from erpnext.subcontracting.doctype.subcontracting_order.test_subcontracting_order import (
	make_subcontracted_variant,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSubcontractingBOM(ERPNextTestSuite):
	def test_variant_finished_good_can_use_template_bom(self):
		variant, template_bom = make_subcontracted_variant()
		service_item = make_item("Subcontracted Template Service Item", {"is_stock_item": 0})

		create_subcontracting_bom(
			finished_good=variant.name, finished_good_bom=template_bom.name, service_item=service_item.name
		)

		subcontracting_bom = get_subcontracting_boms_for_finished_goods(variant.name)
		self.assertEqual(subcontracting_bom.finished_good_bom, template_bom.name)

	def test_finished_good_bom_must_belong_to_finished_good(self):
		variant, _ = make_subcontracted_variant()
		service_item = make_item("Subcontracted Template Service Item", {"is_stock_item": 0})
		unrelated_item = make_item("Subcontracted Unrelated Item", {"is_stock_item": 1})
		unrelated_bom = make_bom(item=unrelated_item.name, raw_materials=["Subcontracted Template RM Item"])

		self.assertRaises(
			frappe.ValidationError,
			create_subcontracting_bom,
			finished_good=variant.name,
			finished_good_bom=unrelated_bom.name,
			service_item=service_item.name,
		)

	def test_finished_good_bom_query_lists_variant_and_template_boms(self):
		variant, template_bom = make_subcontracted_variant()
		variant_bom = make_bom(item=variant.name, raw_materials=["Subcontracted Template RM Item"])

		boms = finished_good_bom_query("BOM", "", "name", 0, 20, {"finished_good": variant.name})

		self.assertEqual({row[0] for row in boms}, {template_bom.name, variant_bom.name})


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
