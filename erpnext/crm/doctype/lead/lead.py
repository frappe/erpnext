# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import (cstr, validate_email_add, cint, comma_and, has_gravatar, now, getdate, nowdate)
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.selling_controller import SellingController
from frappe.contacts.address_and_contact import load_address_and_contact
from erpnext.accounting.party import set_taxes

sender_field = "email_id"

class Lead(SellingController):
	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), self.lead_name)

	def onload(self):
		customer = frappe.db.get_value("Customer", {"lead_name": self.name})
		self.get("__onload").is_customer = customer
		load_address_and_contact(self)

	def validate(self):
		self.set_lead_name()
		self._prev = frappe._dict({
			"contact_date": frappe.db.get_value("Lead", self.name, "contact_date") if \
				(not cint(self.get("__islocal"))) else None,
			"ends_on": frappe.db.get_value("Lead", self.name, "ends_on") if \
				(not cint(self.get("__islocal"))) else None,
			"contact_by": frappe.db.get_value("Lead", self.name, "contact_by") if \
				(not cint(self.get("__islocal"))) else None,
		})

		self.set_status()
		self.check_email_id_is_unique()

		if self.email_id:
			if not self.flags.ignore_email_validation:
				validate_email_add(self.email_id, True)

			if self.email_id == self.lead_owner:
				frappe.throw(_("Lead Owner cannot be same as the Lead"))

			if self.email_id == self.contact_by:
				frappe.throw(_("Next Contact By cannot be same as the Lead Email Address"))

			if self.is_new() or not self.image:
				self.image = has_gravatar(self.email_id)

		if self.contact_date and getdate(self.contact_date) < getdate(nowdate()):
			frappe.throw(_("Next Contact Date cannot be in the past"))

		if self.ends_on and self.contact_date and\
			(self.ends_on < self.contact_date):
			frappe.throw(_("Ends On date cannot be before Next Contact Date."))

	def on_update(self):
		self.add_calendar_event()

	def add_calendar_event(self, opts=None, force=False):
		super(Lead, self).add_calendar_event({
			"owner": self.lead_owner,
			"starts_on": self.contact_date,
			"ends_on": self.ends_on or "",
			"subject": ('Contact ' + cstr(self.lead_name)),
			"description": ('Contact ' + cstr(self.lead_name)) + \
				(self.contact_by and ('. By : ' + cstr(self.contact_by)) or '')
		}, force)

	def check_email_id_is_unique(self):
		if self.email_id:
			# validate email is unique
			duplicate_leads = frappe.db.sql_list("""select name from tabLead
				where email_id=%s and name!=%s""", (self.email_id, self.name))

			if duplicate_leads:
				frappe.throw(_("Email Address must be unique, already exists for {0}")
					.format(comma_and(duplicate_leads)), frappe.DuplicateEntryError)

	def on_trash(self):
		frappe.db.sql("""update `tabIssue` set lead='' where lead=%s""",
			self.name)

		self.delete_events()

	def has_customer(self):
		return frappe.db.get_value("Customer", {"lead_name": self.name})

	def has_opportunity(self):
		return frappe.db.get_value("Opportunity", {"lead": self.name, "status": ["!=", "Lost"]})

	def has_quotation(self):
		return frappe.db.get_value("Quotation", {
			"lead": self.name,
			"docstatus": 1,
			"status": ["!=", "Lost"]

		})

	def has_lost_quotation(self):
		return frappe.db.get_value("Quotation", {
			"lead": self.name,
			"docstatus": 1,
			"status": "Lost"
		})

	def set_lead_name(self):
		if not self.lead_name:
			frappe.db.set_value("Lead", self.name, "lead_name", self.company_name)

@frappe.whitelist()
def make_customer(source_name, target_doc=None):
	return _make_customer(source_name, target_doc)

def _make_customer(source_name, target_doc=None, ignore_permissions=False):
	def set_missing_values(source, target):
		if source.company_name:
			target.customer_type = "Company"
			target.customer_name = source.company_name
		else:
			target.customer_type = "Individual"
			target.customer_name = source.lead_name

		target.customer_group = frappe.db.get_default("Customer Group")

	doclist = get_mapped_doc("Lead", source_name,
		{"Lead": {
			"doctype": "Customer",
			"field_map": {
				"name": "lead_name",
				"company_name": "customer_name",
				"contact_no": "phone_1",
				"fax": "fax_1"
			}
		}}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

	return doclist

@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):
	target_doc = get_mapped_doc("Lead", source_name,
		{"Lead": {
			"doctype": "Opportunity",
			"field_map": {
				"campaign_name": "campaign",
				"doctype": "enquiry_from",
				"name": "lead",
				"lead_name": "contact_display",
				"company_name": "customer_name",
				"email_id": "contact_email",
				"mobile_no": "contact_mobile"
			}
		}}, target_doc)

	return target_doc

@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	target_doc = get_mapped_doc("Lead", source_name,
		{"Lead": {
			"doctype": "Quotation",
			"field_map": {
				"name": "lead"
			}
		}}, target_doc)
	target_doc.quotation_to = "Lead"
	target_doc.run_method("set_missing_values")
	target_doc.run_method("set_other_charges")
	target_doc.run_method("calculate_taxes_and_totals")

	return target_doc

@frappe.whitelist()
def get_lead_details(lead, posting_date=None, company=None):
	if not lead: return {}

	from erpnext.accounting.party import set_address_details
	out = frappe._dict()

	lead_doc = frappe.get_doc("Lead", lead)
	lead = lead_doc

	out.update({
		"territory": lead.territory,
		"customer_name": lead.company_name or lead.lead_name,
		"contact_display": lead.lead_name,
		"contact_email": lead.email_id,
		"contact_mobile": lead.mobile_no,
		"contact_phone": lead.phone,
	})

	set_address_details(out, lead, "Lead")

	taxes_and_charges = set_taxes(None, 'Lead', posting_date, company,
		billing_address=out.get('customer_address'), shipping_address=out.get('shipping_address_name'))
	if taxes_and_charges:
		out['taxes_and_charges'] = taxes_and_charges

	return out
