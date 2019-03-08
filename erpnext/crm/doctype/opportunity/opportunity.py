# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils import cstr, cint, get_fullname
from frappe import msgprint, _
from frappe.model.mapper import get_mapped_doc
from erpnext.setup.utils import get_exchange_rate
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import get_party_account_currency

subject_field = "title"
sender_field = "contact_email"

class Opportunity(TransactionBase):
	def after_insert(self):
		if self.lead:
			frappe.get_doc("Lead", self.lead).set_status(update=True)

	def validate(self):
		self._prev = frappe._dict({
			"contact_date": frappe.db.get_value("Opportunity", self.name, "contact_date") if \
				(not cint(self.get("__islocal"))) else None,
			"contact_by": frappe.db.get_value("Opportunity", self.name, "contact_by") if \
				(not cint(self.get("__islocal"))) else None,
		})

		self.make_new_lead_if_required()

		if not self.enquiry_from:
			frappe.throw(_("Opportunity From field is mandatory"))

		self.validate_item_details()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_lead_cust()
		self.validate_cust_name()

		if not self.title:
			self.title = self.customer_name

		if not self.with_items:
			self.items = []

	def make_new_lead_if_required(self):
		"""Set lead against new opportunity"""
		if not (self.lead or self.customer) and self.contact_email:
			# check if customer is already created agains the self.contact_email
			customer = frappe.db.sql("""select
				distinct `tabDynamic Link`.link_name as customer
				from
					`tabContact`,
					`tabDynamic Link`
				where `tabContact`.email_id='{0}'
				and
					`tabContact`.name=`tabDynamic Link`.parent
				and
					ifnull(`tabDynamic Link`.link_name, '')<>''
				and
					`tabDynamic Link`.link_doctype='Customer'
			""".format(self.contact_email), as_dict=True)
			if customer and customer[0].customer:
				self.customer = customer[0].customer
				self.enquiry_from = "Customer"
				return

			lead_name = frappe.db.get_value("Lead", {"email_id": self.contact_email})
			if not lead_name:
				sender_name = get_fullname(self.contact_email)
				if sender_name == self.contact_email:
					sender_name = None

				if not sender_name and ('@' in self.contact_email):
					email_name = self.contact_email.split('@')[0]

					email_split = email_name.split('.')
					sender_name = ''
					for s in email_split:
						sender_name += s.capitalize() + ' '

				lead = frappe.get_doc({
					"doctype": "Lead",
					"email_id": self.contact_email,
					"lead_name": sender_name or 'Unknown'
				})

				lead.flags.ignore_email_validation = True
				lead.insert(ignore_permissions=True)
				lead_name = lead.name

			self.enquiry_from = "Lead"
			self.lead = lead_name

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

	def on_trash(self):
		self.delete_events()

	def has_active_quotation(self):
		if not self.with_items:
			return frappe.get_all('Quotation',
				{
					'opportunity': self.name,
					'status': ("not in", ['Lost', 'Closed']),
					'docstatus': 1
				}, 'name')
		else:
			return frappe.db.sql("""
				select q.name
				from `tabQuotation` q, `tabQuotation Item` qi
				where q.name = qi.parent and q.docstatus=1 and qi.prevdoc_docname =%s
				and q.status not in ('Lost', 'Closed')""", self.name)

	def has_ordered_quotation(self):
		return frappe.db.sql("""
			select q.name
			from `tabQuotation` q, `tabQuotation Item` qi
			where q.name = qi.parent and q.docstatus=1 and qi.prevdoc_docname =%s
			and q.status = 'Ordered'""", self.name)

	def has_lost_quotation(self):
		lost_quotation = frappe.db.sql("""
			select q.name
			from `tabQuotation` q, `tabQuotation Item` qi
			where q.name = qi.parent and q.docstatus=1
				and qi.prevdoc_docname =%s and q.status = 'Lost'
			""", self.name)
		if lost_quotation:
			if self.has_active_quotation():
				return False
			return True

	def validate_cust_name(self):
		if self.customer:
			self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")
		elif self.lead:
			lead_name, company_name = frappe.db.get_value("Lead", self.lead, ["lead_name", "company_name"])
			self.customer_name = company_name or lead_name

	def on_update(self):
		self.add_calendar_event()

	def add_calendar_event(self, opts=None, force=False):
		if not opts:
			opts = frappe._dict()

		opts.description = ""
		opts.contact_date = self.contact_date

		if self.customer:
			if self.contact_person:
				opts.description = 'Contact '+cstr(self.contact_person)
			else:
				opts.description = 'Contact customer '+cstr(self.customer)
		elif self.lead:
			if self.contact_display:
				opts.description = 'Contact '+cstr(self.contact_display)
			else:
				opts.description = 'Contact lead '+cstr(self.lead)

		opts.subject = opts.description
		opts.description += '. By : ' + cstr(self.contact_by)

		if self.to_discuss:
			opts.description += ' To Discuss : ' + cstr(self.to_discuss)

		super(Opportunity, self).add_calendar_event(opts, force)

	def validate_item_details(self):
		if not self.get('items'):
			return

		# set missing values
		item_fields = ("item_name", "description", "item_group", "brand")

		for d in self.items:
			if not d.item_code:
				continue

			item = frappe.db.get_value("Item", d.item_code, item_fields, as_dict=True)
			for key in item_fields:
				if not d.get(key): d.set(key, item.get(key))

	def validate_lead_cust(self):
		if self.enquiry_from == 'Lead':
			if not self.lead:
				frappe.throw(_("Lead must be set if Opportunity is made from Lead"))
			else:
				self.customer = None
		elif self.enquiry_from == 'Customer':
			if not self.customer:
				msgprint(_("Customer is mandatory if 'Opportunity From' is selected as Customer"), raise_exception=1)
			else:
				self.lead = None

@frappe.whitelist()
def get_item_details(item_code):
	item = frappe.db.sql("""select item_name, stock_uom, image, description, item_group, brand
		from `tabItem` where name = %s""", item_code, as_dict=1)
	return {
		'item_name': item and item[0]['item_name'] or '',
		'uom': item and item[0]['stock_uom'] or '',
		'description': item and item[0]['description'] or '',
		'image': item and item[0]['image'] or '',
		'item_group': item and item[0]['item_group'] or '',
		'brand': item and item[0]['brand'] or ''
	}

@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
		quotation = frappe.get_doc(target)

		company_currency = frappe.get_cached_value('Company',  quotation.company,  "default_currency")
		party_account_currency = get_party_account_currency("Customer", quotation.customer,
			quotation.company) if quotation.customer else company_currency

		quotation.currency = party_account_currency or company_currency

		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(quotation.currency, company_currency,
				quotation.transaction_date, args="for_selling")

		quotation.conversion_rate = exchange_rate

		# get default taxes
		taxes = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=quotation.company)
		if taxes.get('taxes'):
			quotation.update(taxes)

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		if not source.with_items:
			quotation.opportunity = source.name

	doclist = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Quotation",
			"field_map": {
				"enquiry_from": "quotation_to",
				"opportunity_type": "order_type",
				"name": "enq_no",
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
	auto_close_after_days = frappe.db.get_value("Support Settings", "Support Settings", "close_opportunity_after_days") or 15

	opportunities = frappe.db.sql(""" select name from tabOpportunity where status='Replied' and
		modified<DATE_SUB(CURDATE(), INTERVAL %s DAY) """, (auto_close_after_days), as_dict=True)

	for opportunity in opportunities:
		doc = frappe.get_doc("Opportunity", opportunity.get("name"))
		doc.status = "Closed"
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()
