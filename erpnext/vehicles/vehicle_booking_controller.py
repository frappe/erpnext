# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, add_days
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact
from erpnext.crm.doctype.lead.lead import get_lead_contact_details
from erpnext.stock.get_item_details import get_default_warehouse, get_item_price, get_default_supplier, get_default_terms
from erpnext.setup.doctype.item_default_rule.item_default_rule import get_item_default_values
from erpnext.vehicles.doctype.vehicle_allocation_period.vehicle_allocation_period import get_delivery_period
from erpnext.vehicles.doctype.vehicle_withholding_tax_rule.vehicle_withholding_tax_rule import get_withholding_tax_amount
from erpnext.vehicles.utils import validate_vehicle_item
from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_and_conditions
from erpnext.controllers.accounts_controller import AccountsController
from six import string_types
import json


address_fields = ['address_line1', 'address_line2', 'city', 'state']

force_fields = [
	'customer_name', 'financer_name', 'lessee_name', 'customer_category',
	'item_name', 'item_group', 'brand', 'variant_of', 'variant_of_name', 'vehicle_allocation_required',
	'customer_address',
	'address_display', 'contact_display', 'financer_contact_display',
	'contact_email', 'contact_mobile', 'contact_phone', 'contact_designation',
	'father_name', 'husband_name',
	'tax_id', 'tax_cnic', 'tax_strn', 'tax_status', 'tax_overseas_cnic', 'passport_no',
	'withholding_tax_amount', 'exempt_from_vehicle_withholding_tax'
]
force_fields += address_fields

dont_update_if_missing = ['quotation_validity_days', 'valid_till', 'tc_name', 'image', 'fni_amount']


class VehicleBookingController(AccountsController):
	def validate(self):
		if self.get("_action") != "update_after_submit":
			self.set_missing_values(for_validate=True)

		self.validate_date_with_fiscal_year()
		self.validate_customer()
		self.validate_vehicle_item()
		self.validate_vehicle()

		self.validate_lead_time()
		self.validate_delivery_date()

		self.calculate_taxes_and_totals()
		self.validate_amounts()

		self.validate_payment_schedule()

		self.clean_remarks()

	def before_update_after_submit(self):
		self.calculate_sales_team_contribution(self.get('grand_total') or self.get('invoice_total'))

	def onload(self):
		super(VehicleBookingController, self).onload()

		if self.docstatus == 0:
			self.calculate_taxes_and_totals()

	def set_missing_values(self, for_validate=False):
		customer_details = get_customer_details(self.as_dict(), get_withholding_tax=False)
		for k, v in customer_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields) and k not in dont_update_if_missing:
				self.set(k, v)

		if self.get('item_code'):
			item_details = get_item_details(self.as_dict())
			for k, v in item_details.items():
				if self.meta.has_field(k) and (not self.get(k) or k in force_fields) and k not in dont_update_if_missing:
					self.set(k, v)

			if cint(item_details.get('lead_time_days')) > 0:
				if item_details.get('delivery_date'):
					self.delivery_date = item_details.get('delivery_date')
				if item_details.get('delivery_period'):
					self.delivery_period = item_details.get('delivery_period')

		self.set_vehicle_details()

	def set_vehicle_details(self, update=False):
		if self.get('vehicle'):
			values = get_fetch_values(self.doctype, "vehicle", self.vehicle)
		else:
			values = {}
			for df in self.meta.get_fields_to_fetch('vehicle'):
				if df.read_only:
					values[df.fieldname] = None

		changed = False
		for k, v in values.items():
			if self.get(k) != v:
				changed = True
				break

		for k, v in values.items():
			self.set(k, v)

		if update and changed:
			self.db_set(values)

		return changed

	def validate_customer(self):
		if not self.get('customer') and not self.get('customer_is_company') and not self.get('party_name'):
			frappe.throw(_("Customer is mandatory"))

		self.validate_party()

		if self.get('financer') and not self.get('finance_type'):
			frappe.throw(_("Finance Type is mandatory if Financer is set"))
		if not self.get('financer') and self.meta.has_field('finance_type'):
			self.finance_type = ""

		if self.get('finance_type') and self.get('finance_type') not in ['Financed', 'Leased']:
			frappe.throw(_("Finance Type must be either 'Financed' or 'Leased'"))

		customer = (self.get('quotation_to') == "Customer" and self.get('party_name')) or self.get('customer')
		if customer and self.financer and customer == self.financer:
			frappe.throw(_("Customer and Financer cannot be the same"))

	def validate_vehicle_item(self):
		item = frappe.get_cached_doc("Item", self.item_code)
		validate_vehicle_item(item)

	def validate_vehicle(self):
		if self.get('vehicle'):
			vehicle_item_code = frappe.db.get_value("Vehicle", self.vehicle, "item_code")
			if vehicle_item_code != self.item_code:
				frappe.throw(_("Vehicle {0} is not {1}").format(self.vehicle, frappe.bold(self.item_name or self.item_code)))

	def validate_lead_time(self):
		if self.lead_time_days < 0:
			frappe.throw(_("Delivery Lead Time cannot be negative"))

		min_lead_time_days = cint(frappe.get_cached_value("Vehicles Settings", None, "minimum_lead_time_days"))
		if self.lead_time_days and min_lead_time_days and self.lead_time_days < min_lead_time_days:
			frappe.throw(_("Delivery Lead Time cannot be less than {0} days").format(min_lead_time_days))

	def validate_delivery_date(self):
		delivery_date = getdate(self.delivery_date)

		if delivery_date < getdate(self.transaction_date):
			frappe.throw(_("Delivery Due Date cannot be before Booking Date"))

		if self.delivery_period and self.delivery_date:
			from_date, to_date = frappe.get_cached_value("Vehicle Allocation Period", self.delivery_period,
				['from_date', 'to_date'])

			if delivery_date > getdate(to_date) or delivery_date < getdate(from_date):
				frappe.throw(_("Delivery Due Date must be within Delivery Period {0} if Delivery Period is selected")
					.format(self.delivery_period))

	def validate_delivery_period_mandatory(self):
		if not self.delivery_period:
			frappe.throw(_("Delivery Period is mandatory before submission"))

	def calculate_taxes_and_totals(self):
		self.round_floats_in(self, ['vehicle_amount', 'fni_amount', 'withholding_tax_amount'])

		self.invoice_total = flt(self.vehicle_amount + self.fni_amount + self.withholding_tax_amount,
			self.precision('invoice_total'))

		self.set_total_in_words()

		if self.meta.has_field('qty'):
			self.calculate_grand_total()

		self.calculate_sales_team_contribution(self.get('grand_total') or self.get('invoice_total'))

	def calculate_grand_total(self):
		self.total_vehicle_amount = flt(flt(self.vehicle_amount) * cint(self.qty),
			self.precision('total_vehicle_amount'))
		self.total_fni_amount = flt(flt(self.fni_amount) * cint(self.qty),
			self.precision('total_fni_amount'))
		self.total_withholding_tax_amount = flt(flt(self.withholding_tax_amount) * cint(self.qty),
			self.precision('total_withholding_tax_amount'))

		self.total_before_discount = flt(self.total_vehicle_amount + self.total_fni_amount
			+ self.total_withholding_tax_amount, self.precision('total_before_discount'))

		self.total_discount = flt(self.total_discount, self.precision('total_discount'))
		self.grand_total = flt(self.total_before_discount - self.total_discount,
			self.precision('grand_total'))

		self.set_grand_total_in_words()

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		self.in_words = money_in_words(self.invoice_total, self.company_currency)

	def set_grand_total_in_words(self):
		from frappe.utils import money_in_words
		self.total_in_words = money_in_words(self.grand_total, self.company_currency)

	def get_withholding_tax_amount(self, tax_status):
		return get_withholding_tax_amount(self.delivery_date or self.transaction_date, self.item_code, tax_status, self.company)

	def get_party_tax_status(self):
		party_type, customer, financer = get_party_doc(self.as_dict())
		return get_party_tax_status(self.as_dict(), customer, financer)

	def validate_amounts(self):
		for field in ['vehicle_amount', 'invoice_total']:
			self.validate_value(field, '>', 0)
		for field in ['fni_amount', 'withholding_tax_amount']:
			self.validate_value(field, '>=', 0)

		if self.meta.has_field('qty'):
			self.validate_value('qty', '>', 0)
		if self.meta.has_field('total_discount'):
			self.validate_value('total_discount', '>=', 0)

	def validate_payment_schedule(self):
		self.set_payment_schedule()
		self.validate_payment_schedule_dates()
		self.set_due_date()
		self.validate_payment_schedule_amount()
		self.validate_due_date()

	def get_terms_and_conditions(self):
		if self.get('tc_name'):
			doc = self.as_dict()
			self.terms = get_terms_and_conditions(self.tc_name, doc)

@frappe.whitelist()
def get_customer_details(args, get_withholding_tax=True):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	args.customer_is_company = cint(args.customer_is_company)

	out = frappe._dict()

	if args.customer_is_company:
		out.customer = None

	# Determine company or customer and financer
	validate_party_args(args)
	party_type, party, financer = get_party_doc(args)
	is_leased = financer and args.finance_type == "Leased"

	# Customer and Financer Name
	out.update(get_party_name_and_category(args, party, financer))

	# Tax IDs
	out.update(get_party_tax_ids(args, party, financer))
	out.tax_status = get_party_tax_status(args, party, financer)

	# Additional information from custom fields
	out.father_name = party.get('father_name')
	out.husband_name = party.get('husband_name')

	# Address
	out.customer_address = args.customer_address
	if not out.customer_address:
		out.customer_address = get_default_address("Customer", financer.name) if is_leased else get_default_address(party_type, party.name)
	out.update(get_address_details(out.customer_address))

	# Contact
	out.contact_person = args.contact_person or get_default_contact(party_type, party.name)
	out.financer_contact_person = args.financer_contact_person or (get_default_contact("Customer", financer.name) if financer else None)
	out.update(get_customer_contact_details(args, out.contact_person, out.financer_contact_person))

	# Withholding Tax
	if cint(get_withholding_tax) and args.item_code:
		tax_status = out.tax_status
		if args.doctype == "Vehicle Quotation":
			tax_status = tax_status or 'Filer'

		out.exempt_from_vehicle_withholding_tax = cint(frappe.get_cached_value("Item", args.item_code, "exempt_from_vehicle_withholding_tax"))
		if not cint(args.do_not_apply_withholding_tax):
			out.withholding_tax_amount = get_withholding_tax_amount(args.delivery_date or args.transaction_date,
				args.item_code, tax_status, args.company)
		else:
			out.withholding_tax_amount = 0

	return out


def validate_party_args(args):
	if not args.company:
		frappe.throw(_("Company is mandatory"))
	if not args.customer and not args.customer_is_company and not args.party_name:
		frappe.throw(_("Customer is mandatory"))

	customer = (args.quotation_to == "Customer" and args.party_name) or args.customer
	if customer and args.financer and customer == args.financer:
		frappe.throw(_("Customer and Financer cannot be the same"))


def get_party_doc(args):
	if args.customer_is_company:
		party_type = "Company"
		party_name = args.company
	elif args.quotation_to and args.party_name:
		if args.quotation_to not in ('Customer', 'Lead'):
			frappe.throw(_("Quotation To must be either Customer or Lead"))

		party_type = args.quotation_to
		party_name = args.party_name
	else:
		party_type = "Customer"
		party_name = args.customer

	party = frappe.get_cached_doc(party_type, party_name)
	financer = frappe.get_cached_doc("Customer", args.financer) if args.financer else frappe._dict()

	args.finance_type = args.finance_type or 'Financed' if financer else None

	return party_type, party, financer


def get_party_name_and_category(args, party, financer):
	out = frappe._dict()

	if party.doctype == "Company":
		out.customer_name = args.company
	elif party.doctype == "Lead":
		out.customer_name = party.company_name or party.lead_name
	else:
		out.customer_name = party.customer_name

	if financer:
		out.financer_name = financer.customer_name
		out.lessee_name = out.customer_name

		if args.finance_type == 'Financed':
			out.customer_name = "{0} HPA {1}".format(out.customer_name, financer.customer_name)
		elif args.finance_type == 'Leased':
			out.customer_name = financer.customer_name
	else:
		out.lessee_name = None
		out.financer_name = None

	# Territory
	out.territory = args.territory or party.territory

	# Customer Category
	is_individual = False
	if party.doctype == "Lead":
		is_individual = not party.company_name
	elif party.doctype == "Customer":
		is_individual = party.get('customer_type') == "Individual"

	if is_individual:
		if args.financer:
			out.customer_category = "Lease" if args.finance_type == "Leased" else "Finance"
		else:
			out.customer_category = "Individual"
	else:
		if args.financer:
			out.customer_category = "Corporate Lease" if args.finance_type == "Leased" else "Finance"
		else:
			out.customer_category = "Corporate"

	return out


def get_party_tax_ids(args, party, financer):
	out = frappe._dict()

	out.tax_id = financer.get('tax_id') if financer else party.get('tax_id')
	out.tax_strn = financer.get('tax_strn') if financer else party.get('tax_strn')

	out.tax_cnic = party.get('tax_cnic')
	out.tax_overseas_cnic = party.get('tax_overseas_cnic')
	out.passport_no = party.get('passport_no')

	return out


def get_party_tax_status(args, party, financer):
	is_leased = financer and args.finance_type == "Leased"
	return financer.get('tax_status') if is_leased else party.get('tax_status')


@frappe.whitelist()
def get_customer_contact_details(args, customer_contact=None, financer_contact=None):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	customer_contact = get_contact_details(customer_contact) if customer_contact else frappe._dict()
	financer_contact = get_contact_details(financer_contact) if financer_contact else frappe._dict()

	lead_contact = frappe._dict()
	if args.quotation_to == "Lead" and args.party_name and not customer_contact:
		lead_contact = get_lead_contact_details(args.party_name)
		customer_contact = lead_contact

	is_leased = args.financer and args.finance_type == "Leased"

	out.contact_display = customer_contact.get('contact_display')
	out.financer_contact_display = financer_contact.get('contact_display')

	out.contact_email = customer_contact.get('contact_email')
	out.contact_mobile = customer_contact.get('contact_mobile') or financer_contact.get('contact_mobile')
	out.contact_phone = financer_contact.get('contact_phone') if is_leased else customer_contact.get('contact_phone')
	out.contact_designation = customer_contact.get('contact_designation')

	return out

@frappe.whitelist()
def get_address_details(address):
	out = frappe._dict()

	address_dict = frappe.db.get_value("Address", address, "*", as_dict=True, cache=True) or {}

	out.address_display = get_address_display(address_dict)
	for f in address_fields:
		out[f] = address_dict.get(f)

	return out


@frappe.whitelist()
def get_item_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.company:
		frappe.throw(_("Company is mandatory"))
	if not args.item_code:
		frappe.throw(_("Variant Item Code is mandatory"))

	out = frappe._dict()

	item = frappe.get_cached_doc("Item", args.item_code)
	validate_vehicle_item(item)

	out.item_name = item.item_name
	out.description = item.description
	out.item_group = item.item_group
	out.brand = item.brand
	out.image = item.image

	out.variant_of = item.variant_of
	out.variant_of_name = frappe.get_cached_value("Item", item.variant_of, "item_name") if item.variant_of else None

	if not args.supplier:
		out.supplier = get_default_supplier(item, args)

	if not args.warehouse:
		out.warehouse = get_default_warehouse(item, args)

	out.vehicle_price_list = args.vehicle_price_list or get_default_price_list(item, args)

	fni_price_list_settings = frappe.get_cached_value("Vehicles Settings", None, "fni_price_list")
	if fni_price_list_settings:
		out.fni_price_list = fni_price_list_settings

	if args.customer or (args.quotation_to and args.party_name):
		party_type, party, financer = get_party_doc(args)
		args.tax_status = get_party_tax_status(args, party, financer)

	if args.doctype == "Vehicle Quotation":
		if not cint(args.quotation_validity_days) and cint(item.quotation_validity_days):
			out.quotation_validity_days = cint(item.quotation_validity_days)
			if out.quotation_validity_days:
				out.valid_till = add_days(getdate(args.transaction_date), out.quotation_validity_days - 1)

	if args.doctype and frappe.get_meta(args.doctype).has_field('lead_time_days'):
		out.lead_time_days = cint(args.lead_time_days) if 'lead_time_days' in args else cint(item.lead_time_days)

		if out.lead_time_days:
			out.delivery_date = add_days(getdate(args.transaction_date), cint(out.lead_time_days))
			out.delivery_period = get_delivery_period(out.delivery_date)

	tax_status = args.tax_status
	if args.doctype == "Vehicle Quotation":
		tax_status = tax_status or 'Filer'

	out.exempt_from_vehicle_withholding_tax = cint(item.exempt_from_vehicle_withholding_tax)

	if out.vehicle_price_list:
		out.update(get_vehicle_price(args.company, item.name,
			vehicle_price_list=out.vehicle_price_list, fni_price_list=out.fni_price_list,
			transaction_date=args.transaction_date, delivery_date=out.delivery_date or args.delivery_date,
			tax_status=tax_status, do_not_apply_withholding_tax=cint(args.do_not_apply_withholding_tax)))

	if not args.payment_terms_template:
		out.payment_terms_template = item.default_payment_terms
		if not out.payment_terms_template:
			out.payment_terms_template = frappe.get_cached_value("Vehicles Settings", None, "default_payment_terms")

	if not args.tc_name:
		if args.doctype == "Vehicle Quotation":
			out.tc_name = item.default_quotation_terms
			if not out.tc_name:
				out.tc_name = frappe.get_cached_value("Vehicles Settings", None, "default_quotation_terms")
		else:
			out.tc_name = get_default_terms(item, args)
			if not out.tc_name:
				out.tc_name = frappe.get_cached_value("Vehicles Settings", None, "default_booking_terms")

	out.vehicle_allocation_required = get_vehicle_allocation_required(item.name,
		delivery_period=out.delivery_period or args.delivery_period)

	return out


@frappe.whitelist()
def get_delivery_period_details(delivery_period, item_code=None):
	out = frappe._dict()
	out.delivery_date = frappe.get_cached_value("Vehicle Allocation Period", delivery_period, 'to_date')
	out.vehicle_allocation_required = get_vehicle_allocation_required(item_code, delivery_period)
	return out


@frappe.whitelist()
def get_delivery_period_details_from_date(delivery_date, item_code=None):
	out = frappe._dict()
	out.delivery_period = get_delivery_period(delivery_date)
	out.vehicle_allocation_required = get_vehicle_allocation_required(item_code, out.delivery_period)
	return out


@frappe.whitelist()
def get_vehicle_allocation_required(item_code, delivery_period=None):
	if not item_code:
		return 0

	item = frappe.get_cached_doc("Item", item_code)
	if not cint(item.vehicle_allocation_required):
		return 0

	if item.vehicle_allocation_required_from_delivery_period:
		if not delivery_period:
			return 0

		transaction_delivery_period_date = frappe.get_cached_value("Vehicle Allocation Period",
			delivery_period, 'from_date')
		item_delivery_period_date = frappe.get_cached_value("Vehicle Allocation Period",
			item.vehicle_allocation_required_from_delivery_period, 'from_date')

		if getdate(transaction_delivery_period_date) < getdate(item_delivery_period_date):
			return 0

	return 1


@frappe.whitelist()
def get_vehicle_default_supplier(item_code, company):
	if not company:
		frappe.throw(_("Company is mandatory"))
	if not item_code:
		frappe.throw(_("Variant Item Code is mandatory"))

	item = frappe.get_cached_doc("Item", item_code)

	default_supplier = get_default_supplier(item, {"company": company})

	return default_supplier


@frappe.whitelist()
def get_vehicle_price(company, item_code, vehicle_price_list, fni_price_list=None,
		transaction_date=None, delivery_date=None, tax_status=None, do_not_apply_withholding_tax=False):
	if not item_code:
		frappe.throw(_("Variant Item Code is mandatory"))
	if not vehicle_price_list:
		frappe.throw(_("Vehicle Price List is mandatory for Vehicle Price"))
	if not company:
		frappe.throw(_("Company is mandatory"))

	price_date = getdate(delivery_date or transaction_date)
	item = frappe.get_cached_doc("Item", item_code)

	out = frappe._dict()
	vehicle_price_args = {
		"price_list": vehicle_price_list,
		"transaction_date": price_date,
		"uom": item.stock_uom
	}

	vehicle_item_price = get_item_price(vehicle_price_args, item_code, ignore_party=True)
	vehicle_item_price = vehicle_item_price[0][1] if vehicle_item_price else 0
	out.vehicle_amount = flt(vehicle_item_price)

	if not cint(do_not_apply_withholding_tax):
		out.withholding_tax_amount = get_withholding_tax_amount(price_date, item_code, tax_status, company)
	else:
		out.withholding_tax_amount = 0

	if fni_price_list:
		fni_price_args = vehicle_price_args.copy()
		fni_price_args['price_list'] = fni_price_list
		fni_item_price = get_item_price(fni_price_args, item_code, ignore_party=True)
		fni_item_price = fni_item_price[0][1] if fni_item_price else 0
		out.fni_amount = flt(fni_item_price)
	else:
		out.fni_amount = 0

	return out


def get_default_price_list(item, args):
	default_values = get_item_default_values(item, args)
	price_list = default_values.get('default_price_list') or args.get('price_list')

	if not price_list:
		price_list = frappe.get_cached_value("Vehicles Settings", None, "vehicle_price_list")
	if not price_list:
		price_list = frappe.get_cached_value("Buying Settings", None, "buying_price_list")
	if not price_list:
		price_list = frappe.get_cached_value("Selling Settings", None, "selling_price_list")

	return price_list
