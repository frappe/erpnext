# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from erpnext.accounts.party import set_contact_details
from erpnext.stock.get_item_details import get_item_warehouse, get_item_price, get_default_supplier
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_source.item_source import get_item_source_defaults
from erpnext.accounts.doctype.transaction_type.transaction_type import get_transaction_type_defaults
from erpnext.controllers.accounts_controller import AccountsController
from six import string_types
import json

force_fields = ['customer_name', 'item_name', 'item_group', 'brand', 'address_display',
	'contact_display', 'contact_email', 'contact_mobile', 'contact_phone']

class VehicleBookingOrder(AccountsController):
	def validate(self):
		if self.get("_action") != "update_after_submit":
			self.set_missing_values(for_validate=True)

		self.ensure_supplier_is_not_blocked()
		self.validate_date_with_fiscal_year()

		self.validate_customer()
		self.validate_vehicle_item()

		self.set_title()
		self.clean_remarks()

		self.calculate_taxes_and_totals()
		self.validate_amounts()
		self.set_total_in_words()

		self.validate_payment_schedule()

	def on_submit(self):
		pass

	def on_cancel(self):
		pass

	def set_title(self):
		self.title = self.company if self.customer_is_company else self.customer_name

	def validate_customer(self):
		if not self.customer and not self.customer_is_company:
			frappe.throw(_("Customer is mandatory"))

		if self.customer:
			self.validate_party()

	def validate_vehicle_item(self):
		item = frappe.get_cached_doc("Item", self.item_code)
		validate_vehicle_item(item)

	def set_missing_values(self, for_validate=False):
		customer_details = get_customer_details(self.as_dict())
		for k, v in customer_details.items():
			if not self.get(k) or k in force_fields:
				self.set(k, v)

		item_details = get_item_details(self.as_dict())
		for k, v in item_details.items():
			if not self.get(k) or k in force_fields:
				self.set(k, v)

	def calculate_taxes_and_totals(self):
		self.round_floats_in(self, ['vehicle_amount', 'fni_amount'])

		self.invoice_total = flt(self.vehicle_amount + self.fni_amount,
			self.precision('invoice_total'))

		self.customer_outstanding = self.invoice_total - flt(self.customer_advance)
		self.supplier_outstanding = self.invoice_total - flt(self.supplier_advance)

	def validate_amounts(self):
		for field in ['vehicle_amount', 'invoice_total']:
			self.validate_value(field, '>', 0)
		for field in ['fni_amount', 'registration_amount', 'margin_amount', 'discount_amount']:
			self.validate_value(field, '>=', 0)

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		self.in_words = money_in_words(self.invoice_total, self.company_currency)

	def validate_payment_schedule(self):
		self.validate_payment_schedule_dates()
		self.set_due_date()
		self.set_payment_schedule()
		self.validate_payment_schedule_amount()
		self.validate_due_date()


@frappe.whitelist()
def get_customer_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	args.customer_is_company = cint(args.customer_is_company)

	if not args.company:
		frappe.throw(_("Company is mandatory"))
	if not args.customer and not args.customer_is_company:
		frappe.throw(_("Customer is mandatory"))

	out = frappe._dict()

	if args.customer_is_company:
		out.customer = None
		out.customer_name = args.company

	party_type = "Company" if args.customer_is_company else "Customer"
	party_name = args.company if args.customer_is_company else args.customer
	party = frappe.get_cached_doc(party_type, party_name)

	if party_type == "Customer":
		out.customer_name = party.customer_name

	out.tax_id = party.get('tax_id')
	out.tax_cnic = party.get('tax_cnic')
	out.tax_strn = party.get('tax_strn')
	out.tax_status = party.get('tax_status')
	out.tax_overseas_cnic = party.get('tax_overseas_cnic')
	out.passport_no = party.get('passport_no')

	out.customer_address = args.customer_address or get_default_address(party_type, party_name)
	out.address_display = get_address_display(out.customer_address) if out.customer_address else None

	set_contact_details(out, party, party_type)

	return out


@frappe.whitelist()
def get_item_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.company:
		frappe.throw(_("Company is mandatory"))
	if not args.item_code:
		frappe.throw(_("Vehicle Item Code is mandatory"))

	out = frappe._dict()

	item = frappe.get_cached_doc("Item", args.item_code)
	validate_vehicle_item(item)

	out.item_name = item.item_name
	out.item_group = item.item_group
	out.brand = item.brand

	item_defaults = get_item_defaults(item.name, args.company)
	item_group_defaults = get_item_group_defaults(item.name, args.company)
	brand_defaults = get_brand_defaults(item.name, args.company)
	item_source_defaults = get_item_source_defaults(item.name, args.company)
	transaction_type = args.buying_transaction_type or args.selling_transaction_type
	transaction_type_defaults = get_transaction_type_defaults(transaction_type, args.company)

	if not args.supplier:
		out.supplier = get_default_supplier(args, item_defaults, item_group_defaults, brand_defaults, item_source_defaults,
			transaction_type_defaults)

	out.warehouse = get_item_warehouse(item, args, overwrite_warehouse=True, item_defaults=item_defaults, item_group_defaults=item_group_defaults,
		brand_defaults=brand_defaults, item_source_defaults=item_source_defaults, transaction_type_defaults=transaction_type_defaults)

	out.price_list = get_default_price_list(item, args, item_defaults=item_defaults, item_group_defaults=item_group_defaults,
		brand_defaults=brand_defaults, item_source_defaults=item_source_defaults, transaction_type_defaults=transaction_type_defaults)

	if out.price_list:
		out.update(get_vehicle_price(item.name, out.price_list, args.transaction_date))

	return out


@frappe.whitelist()
def get_vehicle_price(item_code, price_list, transaction_date):
	if not item_code:
		frappe.throw(_("Vehicle Item Code is mandatory"))
	if not price_list:
		frappe.throw(_("Price List is mandatory for Vehicle Price"))

	transaction_date = getdate(transaction_date)
	item = frappe.get_cached_doc("Item", item_code)

	out = frappe._dict()
	item_price_args = {
		"price_list": price_list,
		"transaction_date": transaction_date,
		"uom": item.stock_uom
	}

	vehicle_item_price = get_item_price(item_price_args, item_code, ignore_party=True)
	vehicle_item_price = vehicle_item_price[0][1] if vehicle_item_price else 0
	out.vehicle_amount = flt(vehicle_item_price)

	out.fni_item_code = item.fni_item_code
	if out.fni_item_code:
		fni_item_price = get_item_price(item_price_args, item.fni_item_code, ignore_party=True)
		fni_item_price = fni_item_price[0][1] if fni_item_price else 0
		out.fni_amount = flt(fni_item_price)
	else:
		out.fni_amount = 0

	return out


def get_default_price_list(item, args, item_defaults, item_group_defaults, brand_defaults, item_source_defaults,
			transaction_type_defaults):
		price_list = (transaction_type_defaults.get('default_price_list')
			or item_defaults.get('default_price_list')
			or item_source_defaults.get('default_price_list')
			or brand_defaults.get('default_price_list')
			or item_group_defaults.get('default_price_list')
			or args.get('price_list')
		)

		if not price_list:
			price_list = frappe.get_cached_value("Vehicles Settings", None, "booking_price_list")
		if not price_list:
			price_list = frappe.get_cached_value("Buying Settings", None, "buying_price_list")
		if not price_list:
			price_list = frappe.get_cached_value("Selling Settings", None, "selling_price_list")

		return price_list


def validate_vehicle_item(item):
	from erpnext.stock.doctype.item.item import validate_end_of_life
	validate_end_of_life(item.name, item.end_of_life, item.disabled)

	if not item.is_vehicle:
		frappe.throw(_("{0} is not a Vehicle Item").format(item.item_name))
	if not item.include_item_in_vehicle_booking:
		frappe.throw(_("Vehicle Item {0} is not allowed for Vehicle Booking").format(item.item_name))