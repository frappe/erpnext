# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.email.inbox import link_communication_to_document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import DocType, Interval
from frappe.query_builder.functions import Now
from frappe.utils import flt, get_fullname

from erpnext.crm.utils import (
	CRMNote,
	copy_comments,
	link_communications,
	link_open_events,
	link_open_tasks,
)
from erpnext.setup.utils import get_exchange_rate
from erpnext.utilities.transaction_base import TransactionBase


class Opportunity(TransactionBase, CRMNote):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.crm.doctype.competitor_detail.competitor_detail import CompetitorDetail
		from erpnext.crm.doctype.crm_note.crm_note import CRMNote
		from erpnext.crm.doctype.opportunity_item.opportunity_item import OpportunityItem
		from erpnext.crm.doctype.opportunity_lost_reason_detail.opportunity_lost_reason_detail import (
			OpportunityLostReasonDetail,
		)

		address_display: DF.SmallText | None
		amended_from: DF.Link | None
		annual_revenue: DF.Currency
		base_opportunity_amount: DF.Currency
		base_total: DF.Currency
		campaign: DF.Link | None
		city: DF.Data | None
		company: DF.Link
		competitors: DF.TableMultiSelect[CompetitorDetail]
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.Data | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		country: DF.Link | None
		currency: DF.Link | None
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		expected_closing: DF.Date | None
		first_response_time: DF.Duration | None
		industry: DF.Link | None
		items: DF.Table[OpportunityItem]
		job_title: DF.Data | None
		language: DF.Link | None
		lost_reasons: DF.TableMultiSelect[OpportunityLostReasonDetail]
		market_segment: DF.Link | None
		naming_series: DF.Literal["CRM-OPP-.YYYY.-"]
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		notes: DF.Table[CRMNote]
		opportunity_amount: DF.Currency
		opportunity_from: DF.Link
		opportunity_owner: DF.Link | None
		opportunity_type: DF.Link | None
		order_lost_reason: DF.SmallText | None
		party_name: DF.DynamicLink
		phone: DF.Data | None
		phone_ext: DF.Data | None
		probability: DF.Percent
		sales_stage: DF.Link | None
		source: DF.Link | None
		state: DF.Data | None
		status: DF.Literal["Open", "Quotation", "Converted", "Lost", "Replied", "Closed"]
		territory: DF.Link | None
		title: DF.Data | None
		total: DF.Currency
		transaction_date: DF.Date
		website: DF.Data | None
		whatsapp: DF.Data | None
	# end: auto-generated types

	def onload(self):
		ref_doc = frappe.get_doc(self.opportunity_from, self.party_name)
		load_address_and_contact(ref_doc)
		self.set("__onload", ref_doc.get("__onload"))

	def after_insert(self):
		if self.opportunity_from == "Lead":
			frappe.get_doc("Lead", self.party_name).set_status(update=True)

			link_open_tasks(self.opportunity_from, self.party_name, self)
			link_open_events(self.opportunity_from, self.party_name, self)
			if frappe.db.get_single_value("CRM Settings", "carry_forward_communication_and_comments"):
				copy_comments(self.opportunity_from, self.party_name, self)
				link_communications(self.opportunity_from, self.party_name, self)

	def validate(self):
		self.make_new_lead_if_required()
		self.validate_item_details()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_cust_name()
		self.map_fields()
		self.set_exchange_rate()

		if not self.title:
			self.title = self.customer_name

		self.calculate_totals()

	def on_update(self):
		self.update_prospect()

	def map_fields(self):
		for field in self.meta.get_valid_columns():
			if not self.get(field) and frappe.db.field_exists(self.opportunity_from, field):
				try:
					value = frappe.db.get_value(self.opportunity_from, self.party_name, field)
					self.set(field, value)
				except Exception:
					continue

	def set_exchange_rate(self):
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if self.currency == company_currency:
			self.conversion_rate = 1.0
			return

		if not self.conversion_rate or self.conversion_rate == 1.0:
			self.conversion_rate = get_exchange_rate(self.currency, company_currency, self.transaction_date)

	def calculate_totals(self):
		total = base_total = 0
		for item in self.get("items"):
			item.amount = flt(item.rate) * flt(item.qty)
			item.base_rate = flt(self.conversion_rate) * flt(item.rate)
			item.base_amount = flt(self.conversion_rate) * flt(item.amount)
			total += item.amount
			base_total += item.base_amount

		self.total = flt(total)
		self.base_total = flt(base_total)

	def update_prospect(self):
		prospect_name = None
		if self.opportunity_from == "Prospect" and self.party_name:
			prospect_name = self.party_name
		elif self.opportunity_from == "Lead":
			prospect_name = frappe.db.get_value("Prospect Lead", {"lead": self.party_name}, "parent")

		if prospect_name:
			prospect = frappe.get_doc("Prospect", prospect_name)

			opportunity_values = {
				"opportunity": self.name,
				"amount": self.opportunity_amount,
				"stage": self.sales_stage,
				"deal_owner": self.opportunity_owner,
				"probability": self.probability,
				"expected_closing": self.expected_closing,
				"currency": self.currency,
				"contact_person": self.contact_person,
			}

			opportunity_already_added = False
			for d in prospect.get("opportunities", []):
				if d.opportunity == self.name:
					opportunity_already_added = True
					d.update(opportunity_values)
					d.db_update()

			if not opportunity_already_added:
				prospect.append("opportunities", opportunity_values)
				prospect.flags.ignore_permissions = True
				prospect.flags.ignore_mandatory = True
				prospect.save()

	def make_new_lead_if_required(self):
		"""Set lead against new opportunity"""
		if (not self.get("party_name")) and self.contact_email:
			# check if customer is already created agains the self.contact_email
			dynamic_link, contact = DocType("Dynamic Link"), DocType("Contact")
			customer = (
				frappe.qb.from_(dynamic_link)
				.join(contact)
				.on(
					(contact.name == dynamic_link.parent)
					& (dynamic_link.link_doctype == "Customer")
					& (contact.email_id == self.contact_email)
				)
				.select(dynamic_link.link_name)
				.distinct()
				.run(as_dict=True)
			)

			if customer and customer[0].link_name:
				self.party_name = customer[0].link_name
				self.opportunity_from = "Customer"
				return

			lead_name = frappe.db.get_value("Lead", {"email_id": self.contact_email})
			if not lead_name:
				sender_name = get_fullname(self.contact_email)
				if sender_name == self.contact_email:
					sender_name = None

				if not sender_name and ("@" in self.contact_email):
					email_name = self.contact_email.split("@")[0]

					email_split = email_name.split(".")
					sender_name = ""
					for s in email_split:
						sender_name += s.capitalize() + " "

				lead = frappe.get_doc(
					{"doctype": "Lead", "email_id": self.contact_email, "lead_name": sender_name or "Unknown"}
				)

				lead.flags.ignore_email_validation = True
				lead.insert(ignore_permissions=True)
				lead_name = lead.name

			self.opportunity_from = "Lead"
			self.party_name = lead_name

	@frappe.whitelist()
	def declare_enquiry_lost(self, lost_reasons_list, competitors, detailed_reason=None):
		if not self.has_active_quotation():
			self.status = "Lost"
			self.lost_reasons = []
			self.competitors = []

			if detailed_reason:
				self.order_lost_reason = detailed_reason

			for reason in lost_reasons_list:
				self.append("lost_reasons", reason)

			for competitor in competitors:
				self.append("competitors", competitor)

			self.save()

		else:
			frappe.throw(_("Cannot declare as lost, because Quotation has been made."))

	def has_active_quotation(self):
		if not self.get("items", []):
			return frappe.get_all(
				"Quotation",
				{"opportunity": self.name, "status": ("not in", ["Lost", "Closed"]), "docstatus": 1},
				"name",
			)
		else:
			return frappe.db.sql(
				"""
				select q.name
				from `tabQuotation` q, `tabQuotation Item` qi
				where q.name = qi.parent and q.docstatus=1 and qi.prevdoc_docname =%s
				and q.status not in ('Lost', 'Closed')""",
				self.name,
			)

	def has_ordered_quotation(self):
		if not self.get("items", []):
			return frappe.get_all(
				"Quotation", {"opportunity": self.name, "status": "Ordered", "docstatus": 1}, "name"
			)
		else:
			return frappe.db.sql(
				"""
				select q.name
				from `tabQuotation` q, `tabQuotation Item` qi
				where q.name = qi.parent and q.docstatus=1 and qi.prevdoc_docname =%s
				and q.status = 'Ordered'""",
				self.name,
			)

	def has_lost_quotation(self):
		lost_quotation = frappe.db.sql(
			"""
			select name
			from `tabQuotation`
			where docstatus=1
				and opportunity =%s and status = 'Lost'
			""",
			self.name,
		)
		if lost_quotation:
			if self.has_active_quotation():
				return False
			return True

	def validate_cust_name(self):
		if self.party_name:
			if self.opportunity_from == "Customer":
				self.customer_name = frappe.db.get_value("Customer", self.party_name, "customer_name")
			elif self.opportunity_from == "Lead":
				customer_name = frappe.db.get_value("Prospect Lead", {"lead": self.party_name}, "parent")
				if not customer_name:
					lead_name, company_name = frappe.db.get_value(
						"Lead", self.party_name, ["lead_name", "company_name"]
					)
					customer_name = company_name or lead_name

				self.customer_name = customer_name
			elif self.opportunity_from == "Prospect":
				self.customer_name = self.party_name

	def validate_item_details(self):
		if not self.get("items"):
			return

		# set missing values
		item_fields = ("item_name", "description", "item_group", "brand")

		for d in self.items:
			if not d.item_code:
				continue

			item = frappe.db.get_value("Item", d.item_code, item_fields, as_dict=True)
			for key in item_fields:
				if not d.get(key):
					d.set(key, item.get(key))


@frappe.whitelist()
def get_item_details(item_code):
	item = frappe.db.sql(
		"""select item_name, stock_uom, image, description, item_group, brand
		from `tabItem` where name = %s""",
		item_code,
		as_dict=1,
	)
	return {
		"item_name": item and item[0]["item_name"] or "",
		"uom": item and item[0]["stock_uom"] or "",
		"description": item and item[0]["description"] or "",
		"image": item and item[0]["image"] or "",
		"item_group": item and item[0]["item_group"] or "",
		"brand": item and item[0]["brand"] or "",
	}


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges

		quotation = frappe.get_doc(target)

		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")

		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)

		quotation.conversion_rate = exchange_rate

		# get default taxes
		taxes = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=quotation.company)
		if taxes.get("taxes"):
			quotation.update(taxes)

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		if not source.get("items", []):
			quotation.opportunity = source.name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Quotation",
				"field_map": {"opportunity_from": "quotation_to", "name": "enq_no"},
			},
			"Opportunity Item": {
				"doctype": "Quotation Item",
				"field_map": {
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"uom": "stock_uom",
				},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.conversion_factor = 1.0

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {"doctype": "Request for Quotation"},
			"Opportunity Item": {
				"doctype": "Request for Quotation Item",
				"field_map": [["name", "opportunity_item"], ["parent", "opportunity"], ["uom", "uom"]],
				"postprocess": update_item,
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_customer(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.opportunity_name = source.name

		if source.opportunity_from == "Lead":
			target.lead_name = source.party_name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Customer",
				"field_map": {"currency": "default_currency", "customer_name": "customer_name"},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {"doctype": "Supplier Quotation", "field_map": {"name": "opportunity"}},
			"Opportunity Item": {"doctype": "Supplier Quotation Item", "field_map": {"uom": "stock_uom"}},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		opp = frappe.get_doc("Opportunity", name)
		opp.status = status
		opp.save()


def auto_close_opportunity():
	"""auto close the `Replied` Opportunities after 7 days"""
	auto_close_after_days = frappe.db.get_single_value("CRM Settings", "close_opportunity_after_days") or 15

	table = frappe.qb.DocType("Opportunity")
	opportunities = (
		frappe.qb.from_(table)
		.select(table.name)
		.where(
			(table.modified < (Now() - Interval(days=auto_close_after_days))) & (table.status == "Replied")
		)
	).run(pluck=True)

	for opportunity in opportunities:
		doc = frappe.get_doc("Opportunity", opportunity)
		doc.status = "Closed"
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()


@frappe.whitelist()
def make_opportunity_from_communication(communication, company, ignore_communication_links=False):
	from erpnext.crm.doctype.lead.lead import make_lead_from_communication

	doc = frappe.get_doc("Communication", communication)

	lead = doc.reference_name if doc.reference_doctype == "Lead" else None
	if not lead:
		lead = make_lead_from_communication(communication, ignore_communication_links=True)

	opportunity_from = "Lead"

	opportunity = frappe.get_doc(
		{
			"doctype": "Opportunity",
			"company": company,
			"opportunity_from": opportunity_from,
			"party_name": lead,
		}
	).insert(ignore_permissions=True)

	link_communication_to_document(doc, "Opportunity", opportunity.name, ignore_communication_links)

	return opportunity.name
