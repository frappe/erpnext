# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import json
import unittest

import frappe
from frappe.utils import add_days, getdate, now_datetime, random_string, today

from erpnext.crm.doctype.lead.lead import make_customer
from erpnext.crm.doctype.lead.test_lead import make_lead
from erpnext.crm.doctype.opportunity.opportunity import (
	auto_close_opportunity,
	make_quotation,
	make_request_for_quotation,
	set_multiple_status,
)
from erpnext.crm.utils import get_linked_communication_list
from erpnext.exceptions import PartyDisabled
from erpnext.selling.doctype.quotation.quotation import set_expired_status
from erpnext.stock.doctype.item.test_item import make_item

test_records = frappe.get_test_records("Opportunity")


class TestOpportunity(unittest.TestCase):
	def test_opportunity_status(self):
		doc = make_opportunity(with_items=0)
		quotation = make_quotation(doc.name)
		quotation.append("items", {"item_code": "_Test Item", "qty": 1})

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		quotation.submit()

		doc = frappe.get_doc("Opportunity", doc.name)
		self.assertEqual(doc.status, "Quotation")

	def test_expired_quotation_reopens_opportunity(self):
		opp = make_opportunity(with_items=0)
		submit_quotation(opp, transaction_date=add_days(today(), -5), valid_till=add_days(today(), -1))
		self.assertEqual(frappe.db.get_value("Opportunity", opp.name, "status"), "Quotation")

		set_expired_status()
		opp.reload()
		self.assertEqual(opp.status, "Open")
		opp.db_set("status", "Quotation")
		opp.set_status(update=True)
		self.assertEqual(opp.status, "Open")

		# a closed opportunity whose quotation expires stays closed
		closed = make_opportunity(with_items=0)
		quotation = submit_quotation(closed, transaction_date=add_days(today(), -5), valid_till=today())
		quotation.db_set("valid_till", add_days(today(), -1))
		closed.reload()
		closed.status = "Closed"
		closed.save()

		set_expired_status()
		self.assertEqual(frappe.db.get_value("Quotation", quotation.name, "status"), "Expired")
		self.assertEqual(frappe.db.get_value("Opportunity", closed.name, "status"), "Closed")

	def test_quotation_found_after_items_are_added_to_opportunity(self):
		opp = make_opportunity(with_items=0)
		submit_quotation(opp)
		opp.reload()
		opp.append("items", {"item_code": "_Test Item", "qty": 1, "rate": 100, "uom": "_Test UOM"})
		opp.save()

		self.assertTrue(opp.has_active_quotation())
		self.assertRaises(frappe.ValidationError, opp.declare_enquiry_lost, [], [])

	def test_request_for_quotation_keeps_the_uom_conversion_factor(self):
		item = make_item(
			"_Test Opportunity Boxed Item",
			{"stock_uom": "_Test UOM", "uoms": [{"uom": "_Test UOM 1", "conversion_factor": 12}]},
		)
		opp = make_opportunity(with_items=1, item_code=item.name, qty=5)
		opp.items[0].uom = "_Test UOM 1"
		opp.save()

		rfq_item = make_request_for_quotation(opp.name).items[0]
		self.assertEqual((rfq_item.uom, rfq_item.conversion_factor), ("_Test UOM 1", 12))

	def test_make_new_lead_if_required(self):
		opp_doc = make_opportunity_from_lead()

		self.assertTrue(opp_doc.party_name)
		self.assertEqual(opp_doc.opportunity_from, "Lead")
		self.assertEqual(frappe.db.get_value("Lead", opp_doc.party_name, "email_id"), opp_doc.contact_email)

		# create new customer and create new contact against 'new.opportunity@example.com'
		customer = make_customer(opp_doc.party_name)
		customer.customer_group = "Individual"
		customer.insert(ignore_permissions=True)
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "_Test Opportunity Customer",
				"links": [{"link_doctype": "Customer", "link_name": customer.name}],
			}
		)
		contact.add_email(opp_doc.contact_email, is_primary=True)
		contact.insert(ignore_permissions=True)

	def test_opportunity_item(self):
		opportunity_doc = make_opportunity(with_items=1, rate=1100, qty=2)
		self.assertEqual(opportunity_doc.total, 2200)

	def test_disabled_customer_not_allowed(self):
		frappe.db.set_value("Customer", "_Test Customer", "disabled", 1)

		self.assertRaises(PartyDisabled, make_opportunity, with_items=0)

		frappe.db.set_value("Customer", "_Test Customer", "disabled", 0)
		make_opportunity(with_items=0)

	def test_disabled_lead_not_blocked(self):
		# Lead.disabled isn't enforced anywhere else (e.g. the Lead picker query only
		# excludes Converted leads), so it shouldn't block Opportunity creation either.
		lead_doc = make_lead()
		frappe.db.set_value("Lead", lead_doc.name, "disabled", 1)

		opp_doc = make_opportunity(opportunity_from="Lead", lead=lead_doc.name)
		self.assertEqual(opp_doc.party_name, lead_doc.name)

	def test_carry_forward_of_email_and_comments(self):
		frappe.db.set_single_value("CRM Settings", "carry_forward_communication_and_comments", 1)
		lead_doc = make_lead()
		lead_doc.add_comment("Comment", text="Test Comment 1")
		lead_doc.add_comment("Comment", text="Test Comment 2")
		create_communication(lead_doc.doctype, lead_doc.name, lead_doc.email_id)
		create_communication(lead_doc.doctype, lead_doc.name, lead_doc.email_id)

		opp_doc = make_opportunity(opportunity_from="Lead", lead=lead_doc.name)
		opportunity_comment_count = frappe.db.count(
			"Comment", {"reference_doctype": opp_doc.doctype, "reference_name": opp_doc.name}
		)
		opportunity_communication_count = len(get_linked_communication_list(opp_doc.doctype, opp_doc.name))
		self.assertEqual(opportunity_comment_count, 2)
		self.assertEqual(opportunity_communication_count, 2)

		opp_doc.add_comment("Comment", text="Test Comment 3")
		opp_doc.add_comment("Comment", text="Test Comment 4")
		create_communication(opp_doc.doctype, opp_doc.name, opp_doc.contact_email)
		create_communication(opp_doc.doctype, opp_doc.name, opp_doc.contact_email)

	def test_status_set_by_hand_must_agree_with_quotations(self):
		lost_reason = _ensure_master("Opportunity Lost Reason", "lost_reason", "_Test Lost - Too Expensive")
		fresh = make_opportunity(with_items=0)
		self.assertRaises(frappe.ValidationError, set_multiple_status, json.dumps([fresh.name]), "Converted")
		self.assertRaises(frappe.ValidationError, fresh.declare_enquiry_lost, [], [])

		fresh.declare_enquiry_lost([{"lost_reason": lost_reason}], [], "price")
		fresh.status = "Open"
		fresh.save()
		self.assertEqual((fresh.lost_reasons, fresh.order_lost_reason), ([], None))

		quoted = make_opportunity(with_items=0)
		submit_quotation(quoted)
		self.assertRaises(frappe.ValidationError, set_multiple_status, json.dumps([quoted.name]), "Lost")
		quoted.reload()
		quoted.status = "Lost"
		self.assertRaises(frappe.ValidationError, quoted.save)
		self.assertEqual(frappe.db.get_value("Opportunity", quoted.name, "status"), "Quotation")

	def test_status_can_be_changed_by_hand_while_a_quotation_is_open(self):
		opportunity = make_opportunity(with_items=0)
		submit_quotation(opportunity)

		for status in ("Replied", "Open", "Closed"):
			set_multiple_status(json.dumps([opportunity.name]), status)
			self.assertEqual(frappe.db.get_value("Opportunity", opportunity.name, "status"), status)

		self.assertRaises(frappe.ValidationError, set_multiple_status, json.dumps([opportunity.name]), "Converted")
		set_multiple_status(json.dumps([opportunity.name]), "Quotation")
		self.assertEqual(frappe.db.get_value("Opportunity", opportunity.name, "status"), "Quotation")

	def test_converted_opportunity_keeps_its_status_while_ordered(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		opportunity = make_opportunity(with_items=0)
		quotation = submit_quotation(opportunity)
		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = today()
		sales_order.submit()
		self.assertEqual(frappe.db.get_value("Opportunity", opportunity.name, "status"), "Converted")

		for status in ("Open", "Closed", "Quotation", "Lost"):
			self.assertRaises(frappe.ValidationError, set_multiple_status, json.dumps([opportunity.name]), status)
		self.assertEqual(frappe.db.get_value("Opportunity", opportunity.name, "status"), "Converted")

	def test_lost_on_follows_the_lost_status(self):
		lost_reason = _ensure_master("Opportunity Lost Reason", "lost_reason", "_Test Lost - Too Expensive")
		opportunity = make_opportunity(with_items=0)
		opportunity.declare_enquiry_lost([{"lost_reason": lost_reason}], [])
		self.assertEqual(str(opportunity.lost_on), today())

		opportunity.status = "Open"
		opportunity.save()
		self.assertIsNone(frappe.db.get_value("Opportunity", opportunity.name, "lost_on"))

		quoted = make_opportunity(with_items=0)
		quotation = submit_quotation(quoted)
		quotation_lost_reason = _ensure_master(
			"Quotation Lost Reason", "order_lost_reason", "_Test Quotation Lost Reason"
		)
		quotation.declare_enquiry_lost([{"lost_reason": quotation_lost_reason}], [])
		self.assertEqual(
			frappe.db.get_value("Opportunity", quoted.name, ["status", "lost_on"]), ("Lost", getdate())
		)

		quotation.reload()
		quotation.cancel()
		self.assertEqual(
			frappe.db.get_value("Opportunity", quoted.name, ["status", "lost_on"]), ("Open", None)
		)

	def test_lost_on_patch_ignores_a_lost_date_followed_by_a_reopening(self):
		from erpnext.patches.v15_0.set_lost_on_in_opportunity import execute

		# Lost from a quotation in January, reopened in February, declared lost directly in March
		reopened = make_opportunity(with_items=0)
		add_status_comment(reopened, "Lost", "2026-01-10 10:00:00")
		add_status_comment(reopened, "Open", "2026-02-10 10:00:00")
		set_lost_without_date(reopened, "2026-03-10 10:00:00")

		lost_once = make_opportunity(with_items=0)
		add_status_comment(lost_once, "Lost", "2026-01-10 10:00:00")
		set_lost_without_date(lost_once, "2026-03-10 10:00:00")

		execute()
		self.assertEqual(frappe.db.get_value("Opportunity", reopened.name, "lost_on"), getdate("2026-03-10"))
		self.assertEqual(frappe.db.get_value("Opportunity", lost_once.name, "lost_on"), getdate("2026-01-10"))

	def test_form_hides_contacts_of_a_customer_the_user_cannot_read(self):
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "_Test Opportunity Hidden Buyer",
				"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
			}
		).insert()
		opp = make_opportunity(with_items=0)
		user = make_sales_user("_test_opportunity_sales_user@example.com")
		user_permission = frappe.get_doc(
			{"doctype": "User Permission", "user": user, "allow": "Customer", "for_value": "_Test Customer 1"}
		).insert()
		self.addCleanup(user_permission.delete)

		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user)
		opp.run_method("onload")
		self.assertNotIn(contact.name, [c.name for c in opp.get("__onload").contact_list])

	def test_auto_close_replied_opportunity(self):
		days = frappe.db.get_single_value("CRM Settings", "close_opportunity_after_days") or 15

		stale = make_opportunity(with_items=0)
		fresh = make_opportunity(with_items=0)
		for opp in (stale, fresh):
			frappe.db.set_value("Opportunity", opp.name, "status", "Replied", update_modified=False)
		# age only the stale opportunity past the threshold
		frappe.db.set_value(
			"Opportunity",
			stale.name,
			"modified",
			add_days(now_datetime(), -(days + 1)),
			update_modified=False,
		)

		# a party that fails validation since must not stop the job
		frappe.db.set_value("Customer", "_Test Customer", "disabled", 1)
		self.addCleanup(frappe.db.set_value, "Customer", "_Test Customer", "disabled", 0)
		auto_close_opportunity()

		self.assertEqual(frappe.db.get_value("Opportunity", stale.name, "status"), "Closed")
		self.assertEqual(frappe.db.get_value("Opportunity", fresh.name, "status"), "Replied")


def _ensure_master(doctype, fieldname, value):
	if not frappe.db.exists(doctype, value):
		frappe.get_doc({"doctype": doctype, fieldname: value}).insert(ignore_permissions=True)
	return value


def submit_quotation(opportunity, **args):
	quotation = make_quotation(opportunity.name)
	quotation.update(args)
	quotation.append("items", {"item_code": "_Test Item", "qty": 1})
	quotation.run_method("set_missing_values")
	quotation.run_method("calculate_taxes_and_totals")
	return quotation.submit()


def add_status_comment(opportunity, status, creation):
	comment = opportunity.add_comment("Label", status)
	frappe.db.set_value("Comment", comment.name, "creation", creation, update_modified=False)


def set_lost_without_date(opportunity, modified):
	frappe.db.set_value(
		"Opportunity",
		opportunity.name,
		{"status": "Lost", "lost_on": None, "modified": modified},
		update_modified=False,
	)


def make_sales_user(email):
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Sales", "send_welcome_email": 0}
		)
		user.append("roles", {"role": "Sales User"})
		user.insert()
	return email


def make_opportunity_from_lead():
	new_lead_email_id = f"new{random_string(5)}@example.com"
	args = {
		"doctype": "Opportunity",
		"contact_email": new_lead_email_id,
		"opportunity_type": "Sales",
		"with_items": 0,
		"transaction_date": today(),
	}
	# new lead should be created against the new.opportunity@example.com
	opp_doc = frappe.get_doc(args).insert(ignore_permissions=True)

	return opp_doc


def make_opportunity(**args):
	args = frappe._dict(args)

	opp_doc = frappe.get_doc(
		{
			"doctype": "Opportunity",
			"company": args.company or "_Test Company",
			"opportunity_from": args.opportunity_from or "Customer",
			"opportunity_type": "Sales",
			"conversion_rate": 1.0,
			"transaction_date": today(),
		}
	)

	if opp_doc.opportunity_from == "Customer":
		opp_doc.party_name = args.customer or "_Test Customer"

	if opp_doc.opportunity_from == "Lead":
		opp_doc.party_name = args.lead or "_T-Lead-00001"

	if args.with_items:
		opp_doc.append(
			"items",
			{
				"item_code": args.item_code or "_Test Item",
				"qty": args.qty or 1,
				"rate": args.rate or 1000,
				"uom": "_Test UOM",
			},
		)

	opp_doc.insert()
	return opp_doc


def create_communication(reference_doctype, reference_name, sender, sent_or_received=None, creation=None):
	communication = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": sent_or_received or "Sent",
			"email_status": "Open",
			"subject": "Test Subject",
			"sender": sender,
			"content": "Test",
			"status": "Linked",
			"reference_doctype": reference_doctype,
			"creation": creation or now_datetime(),
			"reference_name": reference_name,
		}
	)
	communication.save()
