# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.email.inbox import link_communication_to_document
from frappe.contacts.doctype.address.address import get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from erpnext.setup.utils import get_exchange_rate
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import get_contact_details, get_address_display, get_party_account_currency
from erpnext.crm.doctype.lead.lead import get_customer_from_lead, add_sales_person_from_source
from six import string_types
import json


subject_field = "title"
sender_field = "contact_email"

force_party_fields = [
	'customer_name', 'tax_id', 'tax_cnic', 'tax_strn', 'customer_group', 'territory',
	'address_display', 'contact_display', 'contact_email', 'contact_mobile', 'contact_phone'
]

force_item_fields = ("item_group", "brand")


class Opportunity(TransactionBase):
	def __init__(self, *args, **kwargs):
		super(Opportunity, self).__init__(*args, **kwargs)
		self.status_map = [
			["Open", None],
			["Lost", "eval:self.status=='Lost'"],
			["Lost", "has_lost_quotation"],
			["Quotation", "has_active_quotation"],
			["Converted", "is_converted"],
			["Closed", "eval:self.status=='Closed'"]
		]

	def get_feed(self):
		return _("From {0}").format(self.get("customer_name") or self.get('party_name'))

	def onload(self):
		if self.opportunity_from == "Customer":
			self.set_onload('customer', self.party_name)
		elif self.opportunity_from == "Lead":
			self.set_onload('customer', get_customer_from_lead(self.party_name))

	def validate(self):
		self.set_missing_values()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_financer()
		self.set_title()

	def after_insert(self):
		self.update_lead_status()

	def on_trash(self):
		self.delete_events()

	def set_title(self):
		self.title = self.customer_name

	def set_missing_values(self):
		self.set_customer_details()
		self.set_item_details()

	def set_customer_details(self):
		customer_details = get_customer_details(self.as_dict())
		for k, v in customer_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_party_fields):
				self.set(k, v)

	def set_item_details(self):
		for d in self.items:
			if not d.item_code:
				continue

			item_details = get_item_details(d.item_code)
			for k, v in item_details.items():
				if d.meta.has_field(k) and (not d.get(k) or k in force_party_fields):
					d.set(k, v)

	def validate_financer(self):
		if self.get('financer'):
			if self.get('opportunity_from') == "Customer" and self.get('party_name') == self.get('financer'):
				frappe.throw(_("Customer and Financer cannot be the same"))

		elif self.meta.has_field('financer'):
			self.financer_name = None
			self.finance_type = None

	@frappe.whitelist()
	def declare_enquiry_lost(self, lost_reasons_list, detailed_reason=None):
		if not self.has_active_quotation():
			frappe.db.set(self, 'status', 'Lost')

			if detailed_reason:
				frappe.db.set(self, 'order_lost_reason', detailed_reason)

			for reason in lost_reasons_list:
				self.append('lost_reasons', reason)

			self.save()

		else:
			frappe.throw(_("Cannot declare as lost, because Quotation has been made."))

	def update_lead_status(self):
		if self.opportunity_from == "Lead" and self.party_name:
			doc = frappe.get_doc("Lead", self.party_name)
			doc.set_status(update=True)
			doc.notify_update()

	def has_active_quotation(self):
		vehicle_quotation = frappe.db.get_value("Vehicle Quotation", {
			"opportunity": self.name,
			"docstatus": 1,
			"status": ("not in", ['Lost', 'Closed'])
		})

		quotation = frappe.get_all('Quotation', {
			'opportunity': self.name,
			'status': ("not in", ['Lost', 'Closed']),
			'docstatus': 1
		}, 'name')

		return quotation or vehicle_quotation

	def is_converted(self):
		if self.has_ordered_quotation():
			return True

		vehicle_booking_order = frappe.db.get_value("Vehicle Booking Order", {
			"opportunity": self.name,
			"docstatus": 1,
		})

		if vehicle_booking_order:
			return True

		return False

	def has_ordered_quotation(self):
		quotation = frappe.db.get_value("Quotation", {
			"opportunity": self.name,
			"docstatus": 1,
			"status": "Ordered",
		})

		return quotation

	def has_lost_quotation(self):
		lost_vehicle_quotation = frappe.db.get_value("Vehicle Quotation", {
			"opportunity": self.name,
			"docstatus": 1,
			"status": 'Lost'
		})

		lost_quotation = frappe.db.get_value("Quotation", {
			"opportunity": self.name,
			"docstatus": 1,
			"status": 'Lost'
		})

		if lost_quotation or lost_vehicle_quotation:
			if self.has_active_quotation():
				return False
			return True


@frappe.whitelist()
def get_customer_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	if not args.opportunity_from or not args.party_name:
		frappe.throw(_("Party is mandatory"))

	if args.opportunity_from not in ['Customer', 'Lead']:
		frappe.throw(_("Opportunity From must be either Customer or Lead"))

	party = frappe.get_cached_doc(args.opportunity_from, args.party_name)

	# Customer Name
	if party.doctype == "Lead":
		out.customer_name = party.company_name or party.lead_name
	else:
		out.customer_name = party.customer_name

	# Tax IDs
	out.tax_id = party.get('tax_id')
	out.tax_cnic = party.get('tax_cnic')
	out.tax_strn = party.get('tax_strn')

	lead = party if party.doctype == "Lead" else None

	# Address
	out.customer_address = args.customer_address or get_default_address(party.doctype, party.name)
	out.address_display = get_address_display(out.customer_address, lead=lead)

	# Contact
	out.contact_person = args.contact_person or get_default_contact(party.doctype, party.name)
	out.update(get_contact_details(out.contact_person, lead=lead))

	return out


@frappe.whitelist()
def get_item_details(item_code):
	item_details = frappe.get_cached_doc("Item", item_code) if item_code else frappe._dict()

	return {
		'item_name': item_details.item_name,
		'description': item_details.description,
		'uom': item_details.stock_uom,
		'image': item_details.image,
		'item_group': item_details.item_group,
		'brand': item_details.brand,
	}


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		company_currency = frappe.get_cached_value('Company',  target.company,  "default_currency")

		if target.quotation_to == 'Customer' and target.party_name:
			party_account_currency = get_party_account_currency("Customer", target.party_name, target.company)
		else:
			party_account_currency = company_currency

		target.currency = party_account_currency or company_currency

		if company_currency == target.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(target.currency, company_currency,
				target.transaction_date, args="for_selling")

		target.conversion_rate = exchange_rate

		target.run_method("set_missing_values")
		target.run_method("reset_taxes_and_charges")
		target.run_method("calculate_taxes_and_totals")

	doclist = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Quotation",
			"field_map": {
				"opportunity_from": "quotation_to",
				"opportunity_type": "order_type",
				"name": "opportunity",
			}
		},
		"Opportunity Item": {
			"doctype": "Quotation Item",
			"field_map": {
				"parent": "prevdoc_docname",
				"parenttype": "prevdoc_doctype",
				"uom": "stock_uom"
			},
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Request for Quotation"
		},
		"Opportunity Item": {
			"doctype": "Request for Quotation Item",
			"field_map": [
				["name", "opportunity_item"],
				["parent", "opportunity"],
				["uom", "uom"]
			]
		}
	}, target_doc)

	return doclist


@frappe.whitelist()
def make_vehicle_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		set_vehicle_item_from_opportunity(source, target)
		add_sales_person_from_source(source, target)

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	target_doc = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Vehicle Quotation",
			"field_map": {
				"name": "opportunity",
				'delivery_period': 'delivery_period',
				'opportunity_from': 'quotation_to',
				'party_name': 'party_name',
			}
		}
	}, target_doc, set_missing_values)

	return target_doc


@frappe.whitelist()
def make_vehicle_booking_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		customer = get_customer_from_opportunity(source)
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

		set_vehicle_item_from_opportunity(source, target)
		add_sales_person_from_source(source, target)

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_payment_schedule")
		target.run_method("set_due_date")

	target_doc = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Vehicle Booking Order",
			"field_map": {
				"name": "opportunity",
				"remarks": "remarks",
				"delivery_period": "delivery_period",
				"delivery_date": "delivery_date",
				"vehicle": "vehicle",
			}
		},
	}, target_doc, set_missing_values)

	return target_doc


def set_vehicle_item_from_opportunity(source, target):
	for d in source.items:
		item = frappe.get_cached_doc("Item", d.item_code) if d.item_code else frappe._dict()
		if item.is_vehicle:
			target.item_code = item.name
			target.opportunity_item = d.name
			if target.meta.has_field('color'):
				target.color = d.vehicle_color
			elif target.meta.has_field('color_1'):
				target.color_1 = d.vehicle_color
			return


@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Supplier Quotation",
			"field_map": {
				"name": "opportunity"
			}
		},
		"Opportunity Item": {
			"doctype": "Supplier Quotation Item",
			"field_map": {
				"uom": "stock_uom"
			}
		}
	}, target_doc)

	return doclist


@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		opp = frappe.get_doc("Opportunity", name)
		opp.status = status
		opp.save()


def auto_close_opportunity():
	""" auto close the `Replied` Opportunities after 7 days """
	auto_close_after_days = frappe.db.get_single_value("Selling Settings", "close_opportunity_after_days") or 15

	opportunities = frappe.db.sql(""" select name from tabOpportunity where status='Replied' and
		modified<DATE_SUB(CURDATE(), INTERVAL %s DAY) """, (auto_close_after_days), as_dict=True)

	for opportunity in opportunities:
		doc = frappe.get_doc("Opportunity", opportunity.get("name"))
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

	opportunity = frappe.get_doc({
		"doctype": "Opportunity",
		"company": company,
		"opportunity_from": opportunity_from,
		"party_name": lead
	}).insert(ignore_permissions=True)

	link_communication_to_document(doc, "Opportunity", opportunity.name, ignore_communication_links)

	return opportunity.name


def get_customer_from_opportunity(source):
	if source and source.get('party_name'):
		if source.get('opportunity_from') == 'Lead':
			customer = get_customer_from_lead(source.get('party_name'), throw=True)
			return frappe.get_cached_doc('Customer', customer)

		elif source.get('opportunity_from') == 'Customer':
			return frappe.get_cached_doc('Customer', source.get('party_name'))
