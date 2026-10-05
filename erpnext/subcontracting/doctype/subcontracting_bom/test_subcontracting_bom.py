# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.stock.doctype.item.test_item import make_item


class TestSubcontractingBOM(FrappeTestCase):
	def test_finished_good_bom_must_be_active_and_submitted(self):
		finished_good = make_item(
			"Subcontracted BOM Check Item", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		)
		service_item = make_item("Subcontracted BOM Check Service Item", {"is_stock_item": 0})
		bom = make_bom(item=finished_good.name, raw_materials=["_Test Item"])
		draft_bom = make_bom(item=finished_good.name, raw_materials=["_Test Item"], do_not_submit=True)

		self.assertRaises(
			frappe.ValidationError,
			create_subcontracting_bom,
			finished_good=finished_good.name,
			finished_good_bom=draft_bom.name,
			service_item=service_item.name,
		)

		subcontracting_bom = create_subcontracting_bom(
			finished_good=finished_good.name, finished_good_bom=bom.name, service_item=service_item.name
		)
		frappe.db.set_value("BOM", bom.name, "is_active", 0)
		subcontracting_bom.is_active = 0
		subcontracting_bom.save()

	def test_quantities_must_be_greater_than_zero(self):
		finished_good = make_item(
			"Subcontracted BOM Check Item", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		)
		service_item = make_item("Subcontracted BOM Check Service Item", {"is_stock_item": 0})
		bom = make_bom(item=finished_good.name, raw_materials=["_Test Item"])
		subcontracting_bom = create_subcontracting_bom(
			finished_good=finished_good.name, finished_good_bom=bom.name, service_item=service_item.name
		)

		for fieldname in ("finished_good_qty", "service_item_qty"):
			subcontracting_bom.reload()
			subcontracting_bom.set(fieldname, 0)
			self.assertRaises(frappe.ValidationError, subcontracting_bom.save)


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
