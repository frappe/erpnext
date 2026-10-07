# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, now_datetime, random_string, today

from erpnext.crm.doctype.lead.mapper import make_customer
from erpnext.crm.doctype.lead.test_lead import make_lead
from erpnext.crm.doctype.opportunity.mapper import make_customer as make_customer_from_opportunity
from erpnext.crm.doctype.opportunity.mapper import (
	make_opportunity_from_communication,
	make_quotation,
	make_request_for_quotation,
)
from erpnext.crm.doctype.opportunity.opportunity import (
	auto_close_opportunity,
	get_item_details,
	set_multiple_status,
)
from erpnext.crm.utils import get_linked_communication_list
from erpnext.exceptions import PartyDisabled
from erpnext.selling.doctype.quotation.quotation import set_expired_status
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestOpportunity(ERPNextTestSuite):
	@classmethod
	def make_opportunities(cls):
		records = [
			{
				"doctype": "Opportunity",
				"name": "_Test Opportunity 1",
				"opportunity_from": "Lead",
				"enquiry_type": "Sales",
				"party_name": cls.leads[0].name,
				"company": cls.companies[0].name,
				"transaction_date": "2013-12-12",
				"items": [
					{"item_name": "Test Item", "description": "Some description", "qty": 5, "rate": 100}
				],
			}
		]
		cls.opportunities = []
		for x in records:
			if not frappe.db.exists("Opportunity", {"name": x.get("name")}):
				cls.opportunities.append(frappe.get_doc(x).insert())
			else:
				cls.opportunities.append(frappe.get_doc("Opportunity", {"party_name": x.get("party_name")}))

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

		# a closed opportunity whose inactive quotation expires stays closed
		closed = make_opportunity(with_items=0)
		quotation = submit_quotation(closed, transaction_date=add_days(today(), -5), valid_till=today())
		quotation.db_set({"is_active": 0, "valid_till": add_days(today(), -1)})
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

	def test_make_customer_refuses_duplicates(self):
		lead_opportunity = make_opportunity(opportunity_from="Lead", lead=make_lead().name)
		make_customer_from_opportunity(lead_opportunity.name).insert()
		self.assertRaises(frappe.ValidationError, make_customer_from_opportunity, lead_opportunity.name)

		customer_opportunity = make_opportunity(with_items=0)
		self.assertRaises(frappe.ValidationError, make_customer_from_opportunity, customer_opportunity.name)

	def test_make_new_lead_if_required(self):
		opp_doc = make_opportunity_from_lead("_Test Company")

		self.assertTrue(opp_doc.party_name)
		self.assertEqual(opp_doc.opportunity_from, "Lead")
		self.assertEqual(frappe.db.get_value("Lead", opp_doc.party_name, "email_id"), opp_doc.contact_email)

		# create new customer and create new contact against 'new.opportunity@example.com'
		customer = make_customer(opp_doc.party_name).insert(ignore_permissions=True)
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

	def test_foreign_currency_amounts(self):
		rates = {"USD": 83.0, "EUR": 90.0}
		with patch(
			"erpnext.crm.doctype.opportunity.opportunity.get_exchange_rate",
			side_effect=lambda from_currency, *args, **kwargs: rates[from_currency],
		):
			opp = make_opportunity(with_items=0, currency="USD", opportunity_amount=1000)
			self.assertEqual((opp.conversion_rate, opp.base_opportunity_amount), (83.0, 83000.0))

			opp.currency = "EUR"
			opp.save()
			self.assertEqual((opp.conversion_rate, opp.base_opportunity_amount), (90.0, 90000.0))

	def test_disabled_customer_not_allowed(self):
		frappe.db.set_value("Customer", "_Test Customer", "disabled", 1)

		self.assertRaises(PartyDisabled, make_opportunity, with_items=0)

		frappe.db.set_value("Customer", "_Test Customer", "disabled", 0)
		make_opportunity(with_items=0)

	def test_opportunity_from_must_be_a_party_doctype(self):
		opp = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"company": "_Test Company",
				"opportunity_from": "Supplier",
				"party_name": "_Test Supplier",
				"transaction_date": today(),
			}
		)
		self.assertRaisesRegex(frappe.ValidationError, "Opportunity From", opp.insert)

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

	@ERPNextTestSuite.change_settings("CRM Settings", {"carry_forward_communication_and_comments": 1})
	def test_carry_forward_from_prospect_and_lead_to_quotation(self):
		from erpnext.crm.doctype.prospect.test_prospect import make_prospect
		from erpnext.selling.doctype.quotation.test_quotation import make_quotation as make_quotation_for_lead

		prospect = make_prospect(company="_Test Company")
		prospect.add_comment("Comment", text="Prospect Comment")
		create_communication("Prospect", prospect.name, "prospect@example.com")
		opportunity = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"company": "_Test Company",
				"opportunity_from": "Prospect",
				"party_name": prospect.name,
				"transaction_date": today(),
			}
		).insert()

		lead = make_lead()
		lead.add_comment("Comment", text="Lead Comment")
		create_communication("Lead", lead.name, "lead@example.com")
		quotation = make_quotation_for_lead(party_name=lead.name, do_not_save=1)
		quotation.quotation_to = "Lead"
		quotation.insert()

		for doc in (opportunity, quotation):
			self.assertEqual(
				frappe.db.count("Comment", {"reference_doctype": doc.doctype, "reference_name": doc.name}), 1
			)
			self.assertEqual(len(get_linked_communication_list(doc.doctype, doc.name)), 1)

	def test_opportunity_from_communication_is_made_once(self):
		lead = make_lead()
		communication = create_communication("Lead", lead.name, lead.email_id, sent_or_received="Received")

		first = make_opportunity_from_communication(communication.name, "_Test Company")
		self.assertEqual(make_opportunity_from_communication(communication.name, "_Test Company"), first)

	def test_get_notification_email(self):
		admin_email = frappe.db.get_value("User", "Administrator", "email")
		opp = frappe.new_doc("Opportunity")
		opp.opportunity_owner = "Administrator"
		self.assertEqual(opp.get_notification_email(), admin_email)

		opp.opportunity_owner = None
		self.assertIsNone(opp.get_notification_email())

	def test_declare_enquiry_lost(self):
		lost_reason = _ensure_master("Opportunity Lost Reason", "lost_reason", "_Test Lost - Too Expensive")
		competitor = _ensure_master("Competitor", "competitor_name", "_Test Competitor")

		opp = make_opportunity(with_items=0)
		opp.declare_enquiry_lost(
			lost_reasons_list=[{"lost_reason": lost_reason}],
			competitors=[{"competitor": competitor}],
			detailed_reason="Budget too high",
		)

		opp.reload()
		self.assertEqual(opp.status, "Lost")
		self.assertEqual(opp.order_lost_reason, "Budget too high")
		self.assertEqual([d.lost_reason for d in opp.lost_reasons], [lost_reason])
		self.assertEqual([d.competitor for d in opp.competitors], [competitor])

	def test_declare_lost_blocked_when_quotation_active(self):
		opp = make_opportunity(with_items=0)
		quotation = make_quotation(opp.name)
		quotation.append("items", {"item_code": "_Test Item", "qty": 1})
		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		quotation.submit()

		# A submitted, still-active quotation exists, so the opportunity can't be marked lost
		opp.reload()
		self.assertRaises(frappe.ValidationError, opp.declare_enquiry_lost, [], [], "x")
		self.assertNotEqual(opp.status, "Lost")

	def test_status_set_by_hand_must_agree_with_quotations(self):
		lost_reason = _ensure_master("Opportunity Lost Reason", "lost_reason", "_Test Lost - Too Expensive")
		fresh = make_opportunity(with_items=0)
		self.assertRaises(frappe.ValidationError, set_multiple_status, [fresh.name], "Converted")
		self.assertRaises(frappe.ValidationError, fresh.declare_enquiry_lost, [], [])

		fresh.declare_enquiry_lost([{"lost_reason": lost_reason}], [], "price")
		fresh.status = "Open"
		fresh.save()
		self.assertEqual((fresh.lost_reasons, fresh.order_lost_reason), ([], None))

		quoted = make_opportunity(with_items=0)
		submit_quotation(quoted)
		self.assertRaises(frappe.ValidationError, set_multiple_status, [quoted.name], "Lost")
		self.assertEqual(frappe.db.get_value("Opportunity", quoted.name, "status"), "Quotation")

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
		frappe.get_doc(
			{"doctype": "User Permission", "user": user, "allow": "Customer", "for_value": "_Test Customer 1"}
		).insert()

		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user)
		opp.run_method("onload")
		self.assertNotIn(contact.name, [c.name for c in opp.get("__onload").contact_list])

	def test_contact_and_title_follow_the_party(self):
		frappe.db.set_value("Customer", "_Test Customer", "territory", "_Test Territory India")
		frappe.db.set_value("Customer", "_Test Customer 1", "territory", "_Test Territory Rest Of The World")
		other_contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "_Test Opportunity Other Buyer",
				"links": [{"link_doctype": "Customer", "link_name": "_Test Customer 1"}],
			}
		).insert()

		opp = make_opportunity(with_items=0)
		opp.contact_person = other_contact.name
		self.assertRaisesRegex(frappe.ValidationError, "is not linked to", opp.save)

		opp.reload()
		opp.party_name = "_Test Customer 1"
		opp.save()
		self.assertEqual(opp.title, frappe.db.get_value("Customer", "_Test Customer 1", "customer_name"))
		self.assertEqual(opp.territory, "_Test Territory Rest Of The World")

		opp.contact_person = other_contact.name
		opp.save()
		opp.party_name = "_Test Customer"
		self.assertRaisesRegex(frappe.ValidationError, "is not linked to", opp.save)

	def test_get_item_details(self):
		details = get_item_details("_Test Item")
		self.assertEqual(details["item_name"], frappe.db.get_value("Item", "_Test Item", "item_name"))
		self.assertEqual(details["uom"], frappe.db.get_value("Item", "_Test Item", "stock_uom"))

		# an unknown item returns blank fields rather than erroring
		self.assertEqual(get_item_details("_Non Existent Item XYZ")["item_name"], "")

		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Guest")
		self.assertRaises(frappe.PermissionError, get_item_details, "_Test Item")

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
		auto_close_opportunity()

		self.assertEqual(frappe.db.get_value("Opportunity", stale.name, "status"), "Closed")
		self.assertEqual(frappe.db.get_value("Opportunity", fresh.name, "status"), "Replied")

	def test_opportunity_synced_to_prospect(self):
		prospect_name = "_Test Prospect For Opportunity"
		if not frappe.db.exists("Prospect", prospect_name):
			frappe.get_doc(
				{"doctype": "Prospect", "company_name": prospect_name, "company": "_Test Company"}
			).insert(ignore_permissions=True)

		opp = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"company": "_Test Company",
				"opportunity_from": "Prospect",
				"party_name": prospect_name,
				"opportunity_type": "Sales",
				"sales_stage": "Prospecting",
				"transaction_date": today(),
			}
		).insert(ignore_permissions=True)

		prospect = frappe.get_doc("Prospect", prospect_name)
		linked = {d.opportunity: d for d in prospect.opportunities}
		self.assertIn(opp.name, linked)
		self.assertEqual(linked[opp.name].stage, "Prospecting")

		other_prospect = "_Test Other Prospect For Opportunity"
		if not frappe.db.exists("Prospect", other_prospect):
			frappe.get_doc(
				{"doctype": "Prospect", "company_name": other_prospect, "company": "_Test Company"}
			).insert(ignore_permissions=True)
		opp.party_name = other_prospect
		opp.save()
		self.assertNotIn(opp.name, get_prospect_opportunities(prospect_name))
		self.assertIn(opp.name, get_prospect_opportunities(other_prospect))

		# a row added by hand on another Prospect stays while the party is unchanged
		prospect.reload()
		prospect.append("opportunities", {"opportunity": opp.name})
		prospect.save(ignore_permissions=True)
		opp.save()
		self.assertIn(opp.name, get_prospect_opportunities(prospect_name))

		opp.delete()
		self.assertNotIn(opp.name, get_prospect_opportunities(other_prospect))


def get_prospect_opportunities(prospect):
	return frappe.get_all("Prospect Opportunity", {"parent": prospect}, pluck="opportunity")


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


def make_sales_user(email):
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Sales", "send_welcome_email": 0}
		)
		user.append("roles", {"role": "Sales User"})
		user.insert()
	return email


def make_opportunity_from_lead(company):
	new_lead_email_id = f"new{random_string(5)}@example.com"
	args = {
		"doctype": "Opportunity",
		"contact_email": new_lead_email_id,
		"opportunity_type": "Sales",
		"with_items": 0,
		"transaction_date": today(),
		"company": company,
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
			"currency": args.currency,
			"opportunity_amount": args.opportunity_amount,
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
	return communication
