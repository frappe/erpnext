# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from erpnext.accounts.party import set_taxes
from erpnext.controllers.selling_controller import SellingController
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.email.inbox import link_communication_to_document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, comma_and, cstr, getdate, has_gravatar, nowdate, validate_email_address

class Lead(SellingController):
	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), self.lead_name)

	def onload(self):
		customer = frappe.db.get_value("Customer", {"lead_name": self.name})
		self.get("__onload").is_customer = customer
		load_address_and_contact(self)

	def before_insert(self):
		if self.address_title and self.address_type:
			self.address_doc = self.create_address()
		self.contact_doc = self.create_contact()

	def after_insert(self):
		self.update_links()

	def validate(self):
		self.set_lead_name()
		self.set_title()
		self._prev = frappe._dict({
			"contact_date": frappe.db.get_value("Lead", self.name, "contact_date") if (not cint(self.is_new())) else None,
			"ends_on": frappe.db.get_value("Lead", self.name, "ends_on") if (not cint(self.is_new())) else None,
			"contact_by": frappe.db.get_value("Lead", self.name, "contact_by") if (not cint(self.is_new())) else None,
		})

		self.set_status()
		self.check_email_id_is_unique()

		if self.email_id:
			if not self.flags.ignore_email_validation:
				validate_email_address(self.email_id, throw=True)

			if self.email_id == self.lead_owner:
				frappe.throw(_("Lead Owner cannot be same as the Lead"))

			if self.email_id == self.contact_by:
				frappe.throw(_("Next Contact By cannot be same as the Lead Email Address"))

			if self.is_new() or not self.image:
				self.image = has_gravatar(self.email_id)

		if self.contact_date and getdate(self.contact_date) < getdate(nowdate()):
			frappe.throw(_("Next Contact Date cannot be in the past"))

		if (self.ends_on and self.contact_date and
			(getdate(self.ends_on) < getdate(self.contact_date))):
			frappe.throw(_("Ends On date cannot be before Next Contact Date."))

	def on_update(self):
		self.add_calendar_event()

	def add_calendar_event(self, opts=None, force=False):
		super(Lead, self).add_calendar_event({
			"owner": self.lead_owner,
			"starts_on": self.contact_date,
			"ends_on": self.ends_on or "",
			"subject": ('Contact ' + cstr(self.lead_name)),
			"description": ('Contact ' + cstr(self.lead_name)) + (self.contact_by and ('. By : ' + cstr(self.contact_by)) or '')
		}, force)

	def check_email_id_is_unique(self):
		if self.email_id:
			# validate email is unique
			duplicate_leads = frappe.get_all("Lead", filters={"email_id": self.email_id, "name": ["!=", self.name]})
			duplicate_leads = [lead.name for lead in duplicate_leads]

			if duplicate_leads:
				frappe.throw(_("Email Address must be unique, already exists for {0}")
					.format(comma_and(duplicate_leads)), frappe.DuplicateEntryError)

	def on_trash(self):
		frappe.db.sql("""update `tabIssue` set lead='' where lead=%s""", self.name)

		self.delete_events()

	def has_customer(self):
		return frappe.db.get_value("Customer", {"lead_name": self.name})

	def has_opportunity(self):
		return frappe.db.get_value("Opportunity", {"party_name": self.name, "status": ["!=", "Lost"]})

	def has_quotation(self):
		return frappe.db.get_value("Quotation", {
			"party_name": self.name,
			"docstatus": 1,
			"status": ["!=", "Lost"]

		})

	def has_lost_quotation(self):
		return frappe.db.get_value("Quotation", {
			"party_name": self.name,
			"docstatus": 1,
			"status": "Lost"
		})

	def set_lead_name(self):
		if not self.lead_name:
			# Check for leads being created through data import
			if not self.company_name and not self.email_id and not self.flags.ignore_mandatory:
				frappe.throw(_("A Lead requires either a person's name or an organization's name"))
			elif self.company_name:
				self.lead_name = self.company_name
			else:
				self.lead_name = self.email_id.split("@")[0]

	def set_title(self):
		if self.organization_lead:
			self.title = self.company_name
		else:
			self.title = self.lead_name

	def create_address(self):
		address_fields = ["address_type", "address_title", "address_line1", "address_line2",
			"city", "county", "state", "country", "pincode"]
		info_fields = ["email_id", "phone", "fax"]

		# do not create an address if no fields are available,
		# skipping country since the system auto-sets it from system defaults
		address = frappe.new_doc("Address")

		address.update({addr_field: self.get(addr_field) for addr_field in address_fields})
		address.update({info_field: self.get(info_field) for info_field in info_fields})
		address.insert()

		return address

	def create_contact(self):
		if not self.lead_name:
			self.set_lead_name()

		names = self.lead_name.strip().split(" ")
		if len(names) > 1:
			first_name, last_name = names[0], " ".join(names[1:])
		else:
			first_name, last_name = self.lead_name, None

		contact = frappe.new_doc("Contact")
		contact.update({
			"first_name": first_name,
			"last_name": last_name,
			"salutation": self.salutation,
			"gender": self.gender,
			"designation": self.designation,
		})

		if self.email_id:
			contact.append("email_ids", {
				"email_id": self.email_id,
				"is_primary": 1
			})

		if self.phone:
			contact.append("phone_nos", {
				"phone": self.phone,
				"is_primary": 1
			})

		if self.mobile_no:
			contact.append("phone_nos", {
				"phone": self.mobile_no
			})

		contact.insert(ignore_permissions=True)

		return contact

	def update_links(self):
		# update address links
		if hasattr(self, 'address_doc'):
			self.address_doc.append("links", {
				"link_doctype": "Lead",
				"link_name": self.name,
				"link_title": self.lead_name
			})
			self.address_doc.save()

		# update contact links
		if self.contact_doc:
			self.contact_doc.append("links", {
				"link_doctype": "Lead",
				"link_name": self.name,
				"link_title": self.lead_name
			})
			self.contact_doc.save()

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
	def set_missing_values(source, target):
		_set_missing_values(source, target)

	target_doc = get_mapped_doc("Lead", source_name,
		{"Lead": {
			"doctype": "Opportunity",
			"field_map": {
				"campaign_name": "campaign",
				"doctype": "opportunity_from",
				"name": "party_name",
				"lead_name": "contact_display",
				"company_name": "customer_name",
				"email_id": "contact_email",
				"mobile_no": "contact_mobile"
			}
		}}, target_doc, set_missing_values)

	return target_doc


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		_set_missing_values(source, target)

	target_doc = get_mapped_doc("Lead", source_name,
		{"Lead": {
			"doctype": "Quotation",
			"field_map": {
				"name": "party_name"
			}
		}}, target_doc, set_missing_values)

	target_doc.quotation_to = "Lead"
	target_doc.run_method("set_missing_values")
	target_doc.run_method("set_other_charges")
	target_doc.run_method("calculate_taxes_and_totals")

	return target_doc

def _set_missing_values(source, target):
	address = frappe.get_all('Dynamic Link', {
			'link_doctype': source.doctype,
			'link_name': source.name,
			'parenttype': 'Address',
		}, ['parent'], limit=1)

	contact = frappe.get_all('Dynamic Link', {
			'link_doctype': source.doctype,
			'link_name': source.name,
			'parenttype': 'Contact',
		}, ['parent'], limit=1)

	if address:
		target.customer_address = address[0].parent

	if contact:
		target.contact_person = contact[0].parent

@frappe.whitelist()
def get_lead_details(lead, posting_date=None, company=None):
	if not lead:
		return {}

	from erpnext.accounts.party import set_address_details
	out = frappe._dict()

	lead_doc = frappe.get_doc("Lead", lead)
	lead = lead_doc

	out.update({
		"territory": lead.territory,
		"customer_name": lead.company_name or lead.lead_name,
		"contact_display": " ".join(filter(None, [lead.salutation, lead.lead_name])),
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


@frappe.whitelist()
def make_lead_from_communication(communication, ignore_communication_links=False):
	""" raise a issue from email """

	doc = frappe.get_doc("Communication", communication)
	lead_name = None
	if doc.sender:
		lead_name = frappe.db.get_value("Lead", {"email_id": doc.sender})
	if not lead_name and doc.phone_no:
		lead_name = frappe.db.get_value("Lead", {"mobile_no": doc.phone_no})
	if not lead_name:
		lead = frappe.get_doc({
			"doctype": "Lead",
			"lead_name": doc.sender_full_name,
			"email_id": doc.sender,
			"mobile_no": doc.phone_no
		})
		lead.flags.ignore_mandatory = True
		lead.flags.ignore_permissions = True
		lead.insert()

		lead_name = lead.name

	link_communication_to_document(doc, "Lead", lead_name, ignore_communication_links)
	return lead_name

def get_lead_with_phone_number(number):
	if not number: return

	leads = frappe.get_all('Lead', or_filters={
		'phone': ['like', '%{}'.format(number)],
		'mobile_no': ['like', '%{}'.format(number)]
	}, limit=1)

	lead = leads[0].name if leads else None

	return lead

def daily_open_lead():
	leads = frappe.get_all("Lead", filters = [["contact_date", "Between", [nowdate(), nowdate()]]])
	for lead in leads:
		frappe.db.set_value("Lead", lead.name, "status", "Open")