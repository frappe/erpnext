# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestSubcontractingBOM(FrappeTestCase):
	pass


def create_subcontracting_bom(args):
	args = frappe._dict(args)

	doc = frappe.new_doc("Subcontracting BOM")
	doc.is_active = args.is_active or 1
	doc.finished_good = args.finished_good
	doc.finished_good_uom = args.finished_good_uom
	doc.finished_good_qty = args.finished_good_qty or 1
	doc.finished_good_bom = args.finished_good_bom
	doc.service_item = args.service_item
	doc.service_item_uom = args.service_item_uom
	doc.service_item_qty = args.service_item_qty or 1
	doc.save()

	return doc
