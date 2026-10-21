# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.stock.doctype.delivery_note.mapper import make_installation_note
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestInstallationNote(ERPNextTestSuite):
	def test_item_must_match_delivery_note_row(self):
		dn = create_delivery_note(qty=5)
		note = make_installation_note(dn.name)
		note.inst_date = nowdate()
		note.items[0].item_code = make_item(properties={"is_stock_item": 0}).name

		self.assertRaises(frappe.ValidationError, note.insert)

	def test_cannot_install_against_cancelled_delivery_note(self):
		dn = create_delivery_note(qty=5)
		note = make_installation_note(dn.name)
		note.inst_date = nowdate()
		note.insert()

		dn.cancel()

		self.assertRaises(frappe.ValidationError, note.submit)

	def test_cannot_install_against_foreign_delivery_row(self):
		own = create_delivery_note(qty=5)
		foreign = create_delivery_note(qty=5, customer="_Test Customer 1")

		note = make_installation_note(own.name)
		note.inst_date = nowdate()
		note.items[0].prevdoc_detail_docname = foreign.items[0].name

		self.assertRaises(frappe.ValidationError, note.insert)
