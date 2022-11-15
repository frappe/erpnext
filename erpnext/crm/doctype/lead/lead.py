# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import validate_email_address, cint, comma_and, has_gravatar, clean_whitespace
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.selling_controller import SellingController
from frappe.contacts.address_and_contact import load_address_and_contact
from erpnext.accounts.party import set_taxes
from frappe.email.inbox import link_communication_to_document

sender_field = "email_id"


class Lead(SellingController):
	def __init__(self, *args, **kwargs):
		super(Lead, self).__init__(*args, **kwargs)
		self.status_map = [
			["Lost Quotation", "has_lost_quotation"],
			["Opportunity", "has_opportunity"],
			["Quotation", "has_quotation"],
			["Converted", "eval:self.customer"],
		]

	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), self.lead_name)

	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		self.validate_lead_name()

		self.validate_organization_lead()
		self.validate_tax_id()
		self.validate_mobile_no()

		self.set_status()
		self.check_email_id_is_unique()

		if self.email_id:
			if not self.flags.ignore_email_validation:
				validate_email_address(self.email_id, True)

			if self.is_new() or not self.image:
				self.image = has_gravatar(self.email_id)

	def check_email_id_is_unique(self):
		if self.email_id:
			# validate email is unique
			duplicate_leads = frappe.db.sql_list("""select name from tabLead
				where email_id=%s and name!=%s""", (self.email_id, self.name))

			if duplicate_leads:
				frappe.throw(_("Email Address must be unique, already exists for {0}")
					.format(comma_and(duplicate_leads)), frappe.DuplicateEntryError)

	def on_trash(self):
		frappe.db.sql("update `tabIssue` set lead = '' where lead = %s", self.name)
		self.delete_events()

	def validate_tax_id(self):
		from erpnext.accounts.party import validate_ntn_cnic_strn
		validate_ntn_cnic_strn(self.get('tax_id'), self.get('tax_cnic'), self.get('tax_strn'))

	def validate_mobile_no(self):
		from erpnext.accounts.party import validate_mobile_pakistan

		if self.get('mobile_no_2') and not self.get('mobile_no'):
			self.mobile_no = self.mobile_no_2
			self.mobile_no_2 = ""

		validate_mobile_pakistan(self.get('mobile_no'))
		validate_mobile_pakistan(self.get('mobile_no_2'))

	def validate_organization_lead(self):
		if cint(self.organization_lead):
			self.lead_name = self.company_name
			self.gender = None
			self.salutation = None

	def update_customer_reference(self, customer, update_modified=True):
		self.db_set('customer', customer)

		status = 'Converted' if customer else 'Interested'
		self.set_status(status=status, update=True, update_modified=update_modified)

	def has_opportunity(self):
		return frappe.db.get_value("Opportunity", {"party_name": self.name, "status": ["!=", "Lost"]})

	def has_quotation(self):
		quotation = frappe.db.get_value("Quotation", {
			"quotation_to": "Lead",
			"party_name": self.name,
			"docstatus": 1,
			"status": ["!=", "Lost"]
		})

		vehicle_quotation = frappe.db.get_value("Vehicle Quotation", {
			"quotation_to": "Lead",
			"party_name": self.name,
			"docstatus": 1,
			"status": ["!=", "Lost"]
		})

		return quotation or vehicle_quotation

	def has_lost_quotation(self):
		quotation = frappe.db.get_value("Quotation", {
			"quotation_to": "Lead",
			"party_name": self.name,
			"docstatus": 1,
			"status": "Lost"
		})

		vehicle_quotation = frappe.db.get_value("Vehicle Quotation", {
			"quotation_to": "Lead",
			"party_name": self.name,
			"docstatus": 1,
			"status": "Lost"
		})

		return quotation or vehicle_quotation

	def validate_lead_name(self):
		self.lead_name = clean_whitespace(self.lead_name)
		self.company_name = clean_whitespace(self.company_name)

		if not self.lead_name:
			# Check for leads being created through data import
			if not self.company_name and not self.flags.ignore_mandatory:
				frappe.throw(_("A Lead requires either a person's name or an organization's name"))

			self.lead_name = self.company_name


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

	doclist = get_mapped_doc("Lead", source_name, {
		"Lead": {
			"doctype": "Customer",
			"field_map": {
				"name": "lead_name",
				"lead_name": "contact_first_name",
			}
		}
	}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

	return doclist


def get_customer_from_lead(lead, throw=False):
	if not lead:
		return None

	customer = frappe.db.get_value("Lead", lead, "customer")
	if not customer and throw:
		frappe.throw(_("Please convert Lead to Customer first"))

	return customer


@frappe.whitelist()
def set_customer_for_lead(lead, customer):
	lead_doc = frappe.get_doc("Lead", lead)

	lead_doc.update_customer_reference(customer)
	lead_doc.notify_update()

	if customer:
		frappe.msgprint(_("{0} converted to {1}")
			.format(frappe.get_desk_link("Lead", lead), frappe.get_desk_link("Customer", customer)),
			indicator="green")
	else:
		frappe.msgprint(_("{0} unlinked with Customer").format(frappe.get_desk_link("Lead", lead)))


@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.opportunity_from = 'Lead'
		target.run_method('set_missing_values')

	target_doc = get_mapped_doc("Lead", source_name, {
		"Lead": {
			"doctype": "Opportunity",
			"field_map": {
				"name": "party_name",
			}
		}
	}, target_doc, set_missing_values)

	return target_doc


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		add_sales_person_from_source(source, target)
		target.run_method("set_missing_values")
		target.run_method("reset_taxes_and_charges")
		target.run_method("calculate_taxes_and_totals")

	target_doc = get_mapped_doc("Lead", source_name, {
		"Lead": {
			"doctype": "Quotation",
			"field_map": {
				"name": "party_name",
				"doctype": "quotation_to",
			}
		}
	}, target_doc, set_missing_values)

	return target_doc


@frappe.whitelist()
def make_vehicle_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		add_sales_person_from_source(source, target)
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	target_doc = get_mapped_doc("Lead", source_name, {
		"Lead": {
			"doctype": "Vehicle Quotation",
			"field_map": {
				"name": "party_name",
				"doctype": "quotation_to",
			}
		}
	}, target_doc, set_missing_values)

	return target_doc


def add_sales_person_from_source(source, target):
	if target.meta.has_field('sales_team') and source.get('sales_person') and not target.get('sales_team'):
		target.append('sales_team', {
			'sales_person': source.sales_person,
			'allocated_percentage': 100,
		})


@frappe.whitelist()
def get_lead_details(lead, posting_date=None, company=None):
	if not lead: return frappe._dict()

	from erpnext.accounts.party import set_address_details
	out = frappe._dict()

	lead_doc = frappe.get_doc("Lead", lead)
	lead = lead_doc

	out["customer_name"] = lead.company_name or lead.lead_name
	out["territory"] = lead.territory

	out.update(_get_lead_contact_details(lead))

	set_address_details(out, lead, "Lead")

	taxes_and_charges = set_taxes(None, 'Lead', posting_date, company,
		billing_address=out.get('customer_address'), shipping_address=out.get('shipping_address_name'))
	if taxes_and_charges:
		out['taxes_and_charges'] = taxes_and_charges

	return out


@frappe.whitelist()
def get_lead_contact_details(lead):
	if not lead:
		return frappe._dict()

	lead_doc = frappe.get_doc("Lead", lead)
	return _get_lead_contact_details(lead_doc)


def _get_lead_contact_details(lead):
	out = frappe._dict({
		"contact_email": lead.get('email_id'),
		"contact_mobile": lead.get('mobile_no'),
		"contact_mobile_2": lead.get('mobile_no_2'),
		"contact_phone": lead.get('phone'),
	})

	if cint(lead.organization_lead):
		out["contact_display"] = ""
		out["contact_designation"] = ""
	else:
		out["contact_display"] = " ".join(filter(None, [lead.salutation, lead.lead_name]))
		out["contact_designation"] = lead.get('designation')

	return out


def get_lead_address_details(lead):
	if not lead:
		lead = frappe._dict()

	lead_address_fields = ['address_line1', 'address_line2', 'city', 'state', 'country']
	if isinstance(lead, str):
		lead_address_details = frappe.db.get_value('Lead', lead,
			fieldname=lead_address_fields,
			as_dict=1)
	else:
		lead_address_details = frappe._dict()
		for f in lead_address_fields:
			lead_address_details[f] = lead.get(f)

	if not lead_address_details.get('address_line1'):
		lead_address_details = frappe._dict()

	return lead_address_details


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
