# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.controllers.status_updater import OverAllowanceError
from erpnext.stock.doctype.delivery_note.mapper import make_installation_note, make_sales_return
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

	def test_returned_qty_is_not_installable(self):
		dn = create_delivery_note(qty=5)

		ret = make_sales_return(dn.name)
		ret.items[0].qty = -2
		ret.items[0].stock_qty = -2
		ret.submit()
		# nudge the is_return status_updater so the DN's returned_qty is set (auto on submit in prod)
		frappe.get_doc("Delivery Note", ret.name).update_prevdoc_status()

		# mapper should offer only delivered-minus-returned
		note = make_installation_note(dn.name)
		self.assertEqual(note.items[0].qty, 3)

		# installing more than delivered-minus-returned is blocked
		note.inst_date = nowdate()
		note.items[0].qty = 5
		note.insert()
		self.assertRaises(OverAllowanceError, note.submit)

	def test_cannot_install_against_foreign_delivery_row(self):
		own = create_delivery_note(qty=5)
		foreign = create_delivery_note(qty=5, customer="_Test Customer 1")

		note = make_installation_note(own.name)
		note.inst_date = nowdate()
		note.items[0].prevdoc_detail_docname = foreign.items[0].name

		self.assertRaises(frappe.ValidationError, note.insert)

	def test_full_return_blocks_installation(self):
		dn = create_delivery_note(qty=5)
		note = make_installation_note(dn.name)
		note.inst_date = nowdate()
		note.insert()

		ret = make_sales_return(dn.name)
		ret.items[0].qty = -5
		ret.items[0].stock_qty = -5
		ret.submit()
		frappe.get_doc("Delivery Note", ret.name).update_prevdoc_status()

		self.assertRaises(OverAllowanceError, note.submit)

	def test_return_does_not_block_note_cancellation(self):
		dn = create_delivery_note(qty=5)

		note_a = make_installation_note(dn.name)
		note_a.inst_date = nowdate()
		note_a.items[0].qty = 2
		note_a.insert()
		note_a.submit()

		note_b = make_installation_note(dn.name)
		note_b.inst_date = nowdate()
		note_b.items[0].qty = 3
		note_b.insert()
		note_b.submit()

		ret = make_sales_return(dn.name)
		ret.items[0].qty = -3
		ret.items[0].stock_qty = -3
		ret.submit()
		frappe.get_doc("Delivery Note", ret.name).update_prevdoc_status()

		# cancelling reduces installed qty, so it must not be blocked by the lowered limit
		note_a.cancel()

	def test_over_installation_blocked_for_non_stock_item(self):
		item = make_item(properties={"is_stock_item": 0}).name
		dn = create_delivery_note(item=item, qty=2)

		note = make_installation_note(dn.name)
		note.inst_date = nowdate()
		note.items[0].qty = 10
		note.insert()

		self.assertRaises(OverAllowanceError, note.submit)
