import frappe

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.controllers.draft_links import get_existing_drafts
from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.delivery_note.mapper import make_packing_slip
from erpnext.tests.utils import ERPNextTestSuite


class TestDraftLinks(ERPNextTestSuite):
	def test_finds_draft_via_child_table_link(self):
		so = make_sales_order()
		dn = make_delivery_note(so.name)
		dn.insert()

		self.assertIn(dn.name, get_existing_drafts("Sales Order", so.name, "Delivery Note"))

		frappe.db.set_value("Delivery Note", dn.name, "docstatus", 1)
		self.assertNotIn(dn.name, get_existing_drafts("Sales Order", so.name, "Delivery Note"))

	def test_finds_draft_via_dynamic_link(self):
		pi = make_purchase_invoice()
		pe = get_payment_entry("Purchase Invoice", pi.name)
		pe.insert()

		self.assertIn(pe.name, get_existing_drafts("Purchase Invoice", pi.name, "Payment Entry"))

	def test_finds_draft_via_parent_link(self):
		so = make_sales_order()
		dn = make_delivery_note(so.name)
		dn.insert()
		packing_slip = make_packing_slip(dn.name)
		packing_slip.insert()

		self.assertIn(packing_slip.name, get_existing_drafts("Delivery Note", dn.name, "Packing Slip"))

	def test_nonexistent_target_doctype_does_not_raise_for_non_admin(self):
		# guards check ordering: for non-Administrator users has_permission()
		# raises DoesNotExistError on unknown doctypes, so existence must be
		# checked first (Administrator short-circuits and would not catch this)
		with self.set_user("test@example.com"):
			drafts = get_existing_drafts("Sales Order", "SO-0001", "Inter Company Purchase Order")
		self.assertEqual(drafts, [])

	def test_requires_permission_on_target_doctype(self):
		so = make_sales_order()
		dn = make_delivery_note(so.name)
		dn.insert()

		# test1@example.com has no roles, so no read permission on Delivery Note
		with self.set_user("test1@example.com"):
			drafts = get_existing_drafts("Sales Order", so.name, "Delivery Note")
		self.assertEqual(drafts, [])
