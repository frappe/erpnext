# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext.tests.utils import ERPNextTestSuite

PORTAL_USER = "portal-signature@example.com"
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def _blank_pdf() -> bytes:
	# File checks that a PDF parses, so a stub needs to be a real one
	from io import BytesIO

	from pypdf import PdfWriter

	writer = PdfWriter()
	writer.add_blank_page(width=10, height=10)
	buffer = BytesIO()
	writer.write(buffer)
	return buffer.getvalue()


class TestCustomerPortal(ERPNextTestSuite):
	def _quotation_for_portal_user(self, **args):
		"""A submitted quotation whose customer lists PORTAL_USER as a portal user."""
		from erpnext.selling.doctype.quotation.test_quotation import make_quotation

		if not frappe.db.exists("User", PORTAL_USER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": PORTAL_USER,
					"first_name": "Portal",
					"user_type": "Website User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		customer = frappe.get_doc("Customer", "_Test Customer")
		if not any(row.user == PORTAL_USER for row in customer.portal_users):
			customer.append("portal_users", {"user": PORTAL_USER})
			customer.save(ignore_permissions=True)

		quotation = make_quotation(**args)
		self.addCleanup(frappe.set_user, "Administrator")
		return quotation

	def test_portal_signature_is_write_once(self):
		# the signature is the customer's evidence that they accepted: nobody, including a
		# System Manager in Desk, may change or clear it once the portal has written it, and
		# the customer cannot answer the same quotation twice.
		from erpnext.portal.customer_portal import submit_quotation_response

		quotation = self._quotation_for_portal_user()
		frappe.set_user(PORTAL_USER)
		with patch("erpnext.portal.customer_portal.attach_signed_copy"):
			submit_quotation_response(quotation.name, "accept", signature=PNG)
			self.assertRaisesRegex(
				frappe.ValidationError,
				"already answered",
				submit_quotation_response,
				quotation.name,
				"accept",
				signature=PNG,
			)

		frappe.set_user("Administrator")
		signed = frappe.get_doc("Quotation", quotation.name)
		self.assertTrue(signed.customer_signature)

		for attempt in ("", PNG.replace("iVBOR", "iVBOQ")):
			signed.customer_signature = attempt
			self.assertRaises(frappe.PermissionError, signed.save)
			signed.reload()

	def test_portal_signature_must_be_an_image_payload(self):
		# the stored value is rendered as an <img src> by the print format, which the server
		# itself loads when building the PDF -- a URL there would make the server fetch it.
		from erpnext.portal.customer_portal import submit_quotation_response

		quotation = self._quotation_for_portal_user()
		frappe.set_user(PORTAL_USER)

		oversized = PNG + "A" * (512 * 1024)
		for rejected in ("https://example.com/pixel.png", "javascript:alert(1)", oversized):
			self.assertRaisesRegex(
				frappe.ValidationError,
				"not a valid signature",
				submit_quotation_response,
				quotation.name,
				"accept",
				signature=rejected,
			)

		self.assertFalse(frappe.db.get_value("Quotation", quotation.name, "customer_signature"))

	def test_only_an_open_quotation_can_be_answered(self):
		# ERPNext cannot make an order from a lost, expired or replaced quotation, so an
		# answer to one would leave the customer waiting for an order that never comes
		from erpnext.portal.customer_portal import submit_quotation_response

		# lapsed but still Open: the daily job that marks it Expired has not run yet
		lapsed = {"valid_till": add_days(today(), -1)}
		for closed in ({"status": "Expired"}, {"status": "Lost"}, {"is_active": 0}, lapsed):
			quotation = self._quotation_for_portal_user()
			quotation.db_set(closed)
			frappe.set_user(PORTAL_USER)
			self.assertRaisesRegex(
				frappe.ValidationError,
				"can no longer be answered",
				submit_quotation_response,
				quotation.name,
				"reject",
			)
			frappe.set_user("Administrator")
			self.assertFalse(frappe.db.get_value("Quotation", quotation.name, "portal_response"))

	def test_an_answer_needs_a_signature_or_a_message(self):
		# an accept with no signature would be recorded with no signed copy and could be answered
		# again, and an empty change request tells the sales team nothing
		from erpnext.portal.customer_portal import submit_quotation_response

		quotation = self._quotation_for_portal_user()
		frappe.set_user(PORTAL_USER)

		for signature in (None, ""):
			self.assertRaisesRegex(
				frappe.ValidationError,
				"sign the quotation",
				submit_quotation_response,
				quotation.name,
				"accept",
				signature=signature,
			)
		for message in (None, "", "   "):
			self.assertRaisesRegex(
				frappe.ValidationError,
				"what should change",
				submit_quotation_response,
				quotation.name,
				"changes",
				message,
			)

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value("Quotation", quotation.name, "portal_response"))

	def test_a_change_request_keeps_the_quotation_open_and_a_rejection_ends_it(self):
		from erpnext.portal.customer_portal import get_portal_comments, submit_quotation_response

		quotation = self._quotation_for_portal_user()
		frappe.set_user(PORTAL_USER)

		submit_quotation_response(quotation.name, "changes", "Ten more, please")
		self.assertEqual(
			frappe.db.get_value("Quotation", quotation.name, "portal_response"), "Changes Requested"
		)
		submit_quotation_response(quotation.name, "reject", "Too late now")
		self.assertEqual(frappe.db.get_value("Quotation", quotation.name, "portal_response"), "Rejected")
		self.assertRaisesRegex(
			frappe.ValidationError,
			"already answered",
			submit_quotation_response,
			quotation.name,
			"changes",
			"Hi",
		)

		thread = " ".join(comment.content for comment in get_portal_comments("Quotation", quotation.name))
		self.assertIn("Ten more, please", thread)
		self.assertIn("Too late now", thread)

	def test_only_the_portal_writes_the_customers_answer(self):
		# both fields are read-only in Desk, but the REST API would take them from a Sales User,
		# skipping the portal's own checks
		quotation = self._quotation_for_portal_user()

		for field, value in (("portal_response", "Accepted"), ("customer_signature", PNG)):
			quotation.reload()
			quotation.set(field, value)
			self.assertRaises(frappe.PermissionError, quotation.save)
			self.assertFalse(frappe.db.get_value("Quotation", quotation.name, field))

	def test_signed_copy_shows_as_an_attachment_and_dates_the_signature(self):
		from erpnext.portal.customer_portal import (
			get_portal_comments,
			get_quotation,
			submit_quotation_response,
		)

		quotation = self._quotation_for_portal_user()
		frappe.set_user(PORTAL_USER)
		with patch("frappe.get_print", return_value=_blank_pdf()):
			sent = submit_quotation_response(quotation.name, "accept", signature=PNG)
		self.assertFalse(sent["pending"])

		# Desk shows the file as a link in the comment; the portal moves it to an attachment chip
		frappe.set_user("Administrator")
		self.assertIn("-signed.pdf</a>", frappe.db.get_value("Comment", sent["comment"], "content"))
		frappe.set_user(PORTAL_USER)
		comment = next(
			c for c in get_portal_comments("Quotation", quotation.name) if c.name == sent["comment"]
		)
		self.assertNotIn("signed.pdf", comment.content)
		self.assertEqual([a["file_name"] for a in comment.attachments], [f"{quotation.name}-signed.pdf"])

		reply = get_quotation(quotation.name)
		self.assertTrue(reply["signed"])
		self.assertTrue(reply["signed_on"])

	def test_portal_user_cannot_reach_a_draft(self):
		# the portal only ever shows submitted documents; the action endpoints have to agree,
		# or a draft could be read and signed by name.
		from erpnext.portal.customer_portal import get_quotation, submit_quotation_response

		draft = self._quotation_for_portal_user(do_not_submit=True)
		frappe.set_user(PORTAL_USER)

		self.assertRaises(frappe.DoesNotExistError, get_quotation, draft.name)
		self.assertRaises(
			frappe.DoesNotExistError,
			submit_quotation_response,
			draft.name,
			"accept",
			None,
			PNG,
		)

	def test_portal_brand_never_points_at_a_private_logo(self):
		# a website user gets a 403 on /private files, so the sidebar would show a broken image
		from erpnext.portal.customer_portal import get_portal_context

		self._quotation_for_portal_user()
		frappe.set_user(PORTAL_USER)
		company = get_portal_context()["company"]["name"]
		self.assertTrue(company)

		frappe.set_user("Administrator")
		original = frappe.db.get_value("Company", company, "company_logo")
		self.addCleanup(frappe.db.set_value, "Company", company, "company_logo", original)

		for logo, expected in (("/files/brand.png", "/files/brand.png"), ("/private/files/brand.png", "")):
			frappe.db.set_value("Company", company, "company_logo", logo)
			frappe.set_user(PORTAL_USER)
			self.assertEqual(get_portal_context()["company"]["logo"], expected)
			frappe.set_user("Administrator")

	def test_item_photos_follow_the_default_print_format(self):
		# the seller chooses photos by choosing a print format that has them, and a private
		# photo stays private: the customer could not load it anyway
		from erpnext.portal.customer_portal import get_quotation

		quotation = self._quotation_for_portal_user()
		line = quotation.items[0]
		meta = frappe.get_meta("Quotation")
		frappe.set_user(PORTAL_USER)

		def photo(image, print_format):
			line.db_set("image", image)
			with patch.object(meta, "default_print_format", print_format):
				return get_quotation(quotation.name)["items"][0]["image"]

		self.assertEqual(photo("/files/mug.png", "Quotation Modern with Images"), "/files/mug.png")
		self.assertEqual(photo("/private/files/mug.png", "Quotation Modern with Images"), "")
		self.assertEqual(photo("/files/mug.png", "Quotation Modern"), "")
		self.assertEqual(photo("/files/mug.png", None), "")
		self.assertEqual(photo("/files/mug.png", "No Such Print Format"), "")

	def test_list_page_walks_every_document_once(self):
		# paging must neither skip nor repeat a document, and the tab counts must agree with it
		from erpnext.portal import customer_portal

		made = {self._quotation_for_portal_user().name for _ in range(3)}
		# inside its last week, so it comes first: the urgent half of the paging is walked too
		urgent = self._quotation_for_portal_user()
		urgent.db_set("valid_till", today())
		other = self._quotation_for_portal_user(party_name="_Test Customer 1").name
		frappe.set_user(PORTAL_USER)

		seen = []
		with patch.object(customer_portal, "LIST_PAGE_LENGTH", 2):
			while True:
				page = customer_portal.get_list_page("quotations", "All", start=len(seen))
				if not page["rows"]:
					break
				self.assertLessEqual(len(page["rows"]), 2)
				seen += [row.name for row in page["rows"]]

		self.assertEqual(len(seen), len(set(seen)))
		self.assertEqual(len(seen), page["total"])
		self.assertEqual(page["counts"]["All"], page["total"])
		self.assertTrue(made <= set(seen))
		self.assertEqual(seen[0], urgent.name)
		# another customer's quotation is neither listed nor counted
		self.assertNotIn(other, seen)
		self.assertRaises(frappe.ValidationError, customer_portal.get_list_page, "users")

		# only the offered sizes are served: anything else, however large, gets the default
		for asked, served in ((50, 50), (100_000, customer_portal.LIST_PAGE_LENGTH)):
			page = customer_portal.get_list_page("quotations", "All", page_length=asked)
			self.assertEqual(page["page_length"], served)
			self.assertLessEqual(len(page["rows"]), served)
			self.assertEqual(tuple(page["page_lengths"]), customer_portal.LIST_PAGE_LENGTHS)

	def test_quotation_reply_holds_only_its_chosen_fields(self):
		# a customer receives what the page shows and nothing else, and the totals column
		# (discount, rounding) cannot lose a field it reads without this failing
		from erpnext.portal.customer_portal import (
			ITEM_FIELDS,
			QUOTATION_FIELDS,
			TAX_FIELDS,
			get_quotation,
		)

		quotation = self._quotation_for_portal_user()
		frappe.set_user(PORTAL_USER)
		reply = get_quotation(quotation.name)

		self.assertEqual(
			set(reply), {*QUOTATION_FIELDS, "items", "taxes", "signed", "signed_on", "revised_to", "orders"}
		)
		totals_fields = {"rounded_total", "rounding_adjustment", "discount_amount", "apply_discount_on"}
		self.assertTrue(totals_fields <= set(reply))
		for row in reply["items"]:
			self.assertEqual(set(row), {*ITEM_FIELDS, "image"})
		for row in reply["taxes"]:
			self.assertEqual(set(row), set(TAX_FIELDS))

	def test_invoice_reply_names_the_currency_of_what_is_owed(self):
		# outstanding_amount and the payments are kept in the party account's currency, which the
		# invoice's own can differ from, so the page needs both to label them
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.portal.customer_portal import get_invoice

		self._quotation_for_portal_user()
		# billed in USD to a customer whose receivable is kept in INR
		with self.change_settings(
			"Accounts Settings", allow_multi_currency_invoices_against_single_party_account=1
		):
			invoice = create_sales_invoice(customer="_Test Customer", currency="USD", conversion_rate=50)
		frappe.set_user(PORTAL_USER)
		reply = get_invoice(invoice.name)

		self.assertEqual(reply["currency"], "USD")
		self.assertEqual(reply["party_account_currency"], "INR")
		self.assertEqual(reply["party_total"], invoice.base_rounded_total or invoice.base_grand_total)
		self.assertEqual(reply["outstanding_amount"], reply["party_total"])

	def test_home_and_the_overdue_tab_count_overdue_invoices_alike(self):
		# by status, which ERPNext sets once any instalment is late; due_date is only the last one's
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.portal.customer_portal import get_home, get_list_page

		self._quotation_for_portal_user()
		create_sales_invoice(customer="_Test Customer")
		late = create_sales_invoice(
			customer="_Test Customer", posting_date=add_days(today(), -40), due_date=add_days(today(), -10)
		)
		self.assertEqual(late.status, "Overdue")
		frappe.set_user(PORTAL_USER)

		page = get_list_page("invoices", "Outstanding")
		self.assertEqual(page["rows"][0].name, late.name)
		self.assertEqual(get_home()["summary"]["invoices"]["overdue"], page["counts"]["Overdue"])

	def test_portal_user_cannot_reach_another_customers_address(self):
		# the address book is the caller's own: another customer's address can be neither
		# listed nor changed, and a new address is linked to the caller whatever they send
		from erpnext.portal.customer_portal import get_portal_addresses, save_portal_address

		self._quotation_for_portal_user()
		other = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "Other Customer",
				"address_type": "Billing",
				"address_line1": "1 Other Road",
				"city": "Pune",
				"country": "India",
				"links": [{"link_doctype": "Customer", "link_name": "_Test Customer 1"}],
			}
		).insert()
		frappe.set_user(PORTAL_USER)

		listed = [address.name for address in get_portal_addresses()]
		self.assertNotIn(other.name, listed)
		self.assertRaises(frappe.DoesNotExistError, save_portal_address, {"city": "Elsewhere"}, other.name)

		claimed = save_portal_address(
			{
				"address_title": "Claimed",
				"address_type": "Billing",
				"address_line1": "2 Claim Road",
				"city": "Pune",
				"country": "India",
				"customer": "_Test Customer 1",
			}
		)

		self.assertIn(claimed, [address.name for address in get_portal_addresses()])

		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Address", other.name, "city"), "Pune")
		self.assertEqual(
			frappe.db.get_value("Dynamic Link", {"parent": claimed, "parenttype": "Address"}, "link_name"),
			"_Test Customer",
		)

	def test_portal_user_can_only_comment_on_their_own_documents(self):
		# the comment endpoints write with ignore_permissions, so the scope check is all
		# that keeps one customer off another's thread, and off documents with no page
		from erpnext.portal.customer_portal import add_portal_comment, get_portal_comments

		own = self._quotation_for_portal_user()
		other = self._quotation_for_portal_user(party_name="_Test Customer 1")
		frappe.set_user(PORTAL_USER)

		for doctype, name in (("Quotation", other.name), ("Payment Entry", own.name)):
			self.assertRaises(frappe.DoesNotExistError, get_portal_comments, doctype, name)
			self.assertRaises(frappe.DoesNotExistError, add_portal_comment, doctype, name, "Hello")

		add_portal_comment("Quotation", own.name, "Hello")
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Comment", {"reference_name": other.name, "content": "Hello"}))

	def test_team_cannot_rewrite_a_customers_comment(self):
		from erpnext.portal.customer_portal import add_portal_comment

		quotation = self._quotation_for_portal_user()
		frappe.set_user(PORTAL_USER)
		name = add_portal_comment("Quotation", quotation.name, "Please deliver by Friday")["name"]

		frappe.set_user("Administrator")
		comment = frappe.get_doc("Comment", name)
		comment.content = "Please deliver by Monday"
		self.assertRaises(frappe.PermissionError, comment.save)

	def test_team_can_still_edit_a_team_comment(self):
		quotation = self._quotation_for_portal_user()
		comment = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Quotation",
				"reference_name": quotation.name,
				"published": 1,
				"content": "Prices include delivery",
			}
		).insert(ignore_permissions=True)
		comment.content = "Prices include delivery and insurance"
		comment.save()

	def test_customer_hears_of_a_comment_once_and_only_on_a_document_they_can_open(self):
		def comment_on(quotation, published):
			return frappe.get_doc(
				{
					"doctype": "Comment",
					"comment_type": "Comment",
					"reference_doctype": "Quotation",
					"reference_name": quotation.name,
					"published": published,
					"content": "Prices include delivery",
				}
			).insert(ignore_permissions=True)

		def notified(quotation):
			return frappe.db.count(
				"Notification Log", {"for_user": PORTAL_USER, "document_name": quotation.name}
			)

		quotation = self._quotation_for_portal_user()
		comment = comment_on(quotation, published=0)
		self.assertEqual(notified(quotation), 0)
		# published later: news once, however often it is saved after that
		comment.published = 1
		comment.save()
		comment.save()
		self.assertEqual(notified(quotation), 1)

		draft = self._quotation_for_portal_user(do_not_submit=True)
		comment_on(draft, published=1)
		self.assertEqual(notified(draft), 0)

	def test_customer_sees_team_comments_without_their_emails(self):
		# a team comment notifies the customer and shows its author's name, not their login;
		# the customer's own comment notifies nobody on their side
		from erpnext.portal.customer_portal import add_portal_comment, get_portal_comments

		quotation = self._quotation_for_portal_user()
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Quotation",
				"reference_name": quotation.name,
				"published": 1,
				"content": "Prices include delivery",
			}
		).insert(ignore_permissions=True)
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": PORTAL_USER, "document_name": quotation.name})
		)

		frappe.set_user(PORTAL_USER)
		add_portal_comment("Quotation", quotation.name, "Thanks")
		thread = get_portal_comments("Quotation", quotation.name)

		emails = {c.content: c.comment_email for c in thread}
		self.assertEqual(emails["Thanks"], PORTAL_USER)
		self.assertTrue(all(email == "" for content, email in emails.items() if content != "Thanks"))
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.count("Notification Log", {"for_user": PORTAL_USER, "document_name": quotation.name}), 1
		)
