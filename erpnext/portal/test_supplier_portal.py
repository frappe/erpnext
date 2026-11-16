# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.desk.notifications import extract_mentions
from frappe.utils import add_days, today

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.request_for_quotation.mapper import make_supplier_quotation_from_rfq
from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
	make_request_for_quotation,
)
from erpnext.exceptions import PartyDisabled, PartyFrozen
from erpnext.portal import supplier_portal
from erpnext.tests.utils import ERPNextTestSuite

SUPPLIER = "_Test Supplier"
OTHER_SUPPLIER = "_Test Supplier 1"
USER = "supplier-portal@example.com"


class TestSupplierPortal(ERPNextTestSuite):
	def setUp(self):
		make_portal_user(USER, SUPPLIER)
		# cached documents and roles outlive the rollback after each test
		self.addCleanup(frappe.clear_document_cache, "Supplier", SUPPLIER)
		self.addCleanup(frappe.clear_cache, user=USER)

	def test_another_suppliers_documents_are_not_found(self):
		rfq = make_request_for_quotation()
		own = make_quotation(rfq, SUPPLIER)
		other = make_quotation(rfq, OTHER_SUPPLIER)
		order = create_purchase_order(supplier=OTHER_SUPPLIER)

		with self.set_user(USER):
			self.assertEqual(supplier_portal.get_quotation(own.name)["name"], own.name)
			self.assertRaises(frappe.DoesNotExistError, supplier_portal.get_quotation, other.name)
			self.assertRaises(frappe.DoesNotExistError, supplier_portal.get_order, order.name)

	def test_drafts_are_not_found(self):
		order = create_purchase_order(supplier=SUPPLIER, do_not_submit=True)

		with self.set_user(USER):
			self.assertRaises(frappe.DoesNotExistError, supplier_portal.get_order, order.name)

	def test_rfq_the_supplier_is_not_invited_to_is_not_found(self):
		rfq = make_request_for_quotation(supplier_data=[{"supplier": OTHER_SUPPLIER}])

		with self.set_user(USER):
			self.assertRaises(frappe.DoesNotExistError, supplier_portal.get_rfq, rfq.name)
			self.assertRaises(frappe.DoesNotExistError, send_quote, rfq)

	def test_only_published_comments_are_shown(self):
		quotation = make_quotation(make_request_for_quotation(), SUPPLIER)
		for content, published in (("For the supplier", 1), ("Internal note", 0)):
			quotation.add_comment("Comment", content).db_set("published", published)

		with self.set_user(USER):
			comments = supplier_portal.get_portal_comments("Supplier Quotation", quotation.name)

		self.assertEqual([comment.content for comment in comments], ["For the supplier"])

	def test_cannot_comment_on_another_suppliers_document(self):
		quotation = make_quotation(make_request_for_quotation(), OTHER_SUPPLIER)

		with self.set_user(USER):
			self.assertRaises(
				frappe.DoesNotExistError,
				supplier_portal.add_portal_comment,
				"Supplier Quotation",
				quotation.name,
				"Hello",
			)

	def test_mentions_are_dropped_from_comments(self):
		quotation = make_quotation(make_request_for_quotation(), SUPPLIER)
		html = '<p>Hi <span class="mention" data-id="Administrator">@Administrator</span></p>'

		with self.set_user(USER):
			comment = supplier_portal.add_portal_comment("Supplier Quotation", quotation.name, html)

		content = frappe.db.get_value("Comment", comment["name"], "content")
		self.assertEqual(extract_mentions(content), [])
		self.assertIn("@Administrator", content)

	def test_quote_is_sent_and_revised_as_the_supplier(self):
		rfq = make_request_for_quotation()

		with self.set_user(USER):
			first = send_quote(rfq)
			revision = send_quote(rfq, rate=90)

		self.assertEqual(
			frappe.db.get_value("Supplier Quotation", first, ["docstatus", "owner", "modified_by"]),
			(2, USER, USER),
		)
		self.assertEqual(
			frappe.db.get_value("Supplier Quotation", revision, ["docstatus", "owner", "amended_from"]),
			(1, USER, first),
		)

	def test_frozen_supplier_cannot_quote(self):
		rfq = make_request_for_quotation()
		# a role allowed to post for frozen parties, which the supplier does not have
		frappe.db.set_value("Company", rfq.company, "role_allowed_for_frozen_entries", "Accounts Manager")
		self.addCleanup(frappe.clear_document_cache, "Company", rfq.company)
		set_supplier(is_frozen=1)

		with self.set_user(USER):
			self.assertRaises(PartyFrozen, send_quote, rfq)

	def test_disabled_supplier_cannot_quote(self):
		rfq = make_request_for_quotation()
		set_supplier(disabled=1)

		with self.set_user(USER):
			self.assertRaises(PartyDisabled, send_quote, rfq)

	def test_portal_is_closed_without_the_supplier_role(self):
		quotation = make_quotation(make_request_for_quotation(), SUPPLIER)
		# still listed under the supplier's portal users
		frappe.db.delete("Has Role", {"parent": USER, "role": "Supplier"})
		frappe.clear_cache(user=USER)

		with self.set_user(USER):
			self.assertRaises(frappe.DoesNotExistError, supplier_portal.get_quotation, quotation.name)
			self.assertEqual(supplier_portal.get_portal_context()["suppliers"], [])


def make_portal_user(email: str, supplier: str) -> None:
	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "Portal",
			"user_type": "Website User",
			"send_welcome_email": 0,
			"roles": [{"role": "Supplier"}],
		}
	).insert(ignore_permissions=True)
	frappe.new_doc(
		"Portal User", user=email, parent=supplier, parentfield="portal_users", parenttype="Supplier"
	).insert()


def make_quotation(rfq, supplier: str):
	quotation = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier)
	quotation.submit()
	return quotation


def send_quote(rfq, rate: float = 100) -> str:
	items = [{"name": row.name, "qty": row.qty, "rate": rate} for row in rfq.items]
	return supplier_portal.submit_rfq_quotation(rfq.name, items, valid_till=add_days(today(), 10))


def set_supplier(**values) -> None:
	frappe.db.set_value("Supplier", SUPPLIER, values)
	frappe.clear_document_cache("Supplier", SUPPLIER)
