# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.controllers.selling_controller import SellingController
from frappe.utils import cint, flt, add_months, today, date_diff, getdate, add_days, cstr, nowdate
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.accounts.doctype.loyalty_program.loyalty_program import \
	get_loyalty_program_details_with_points, validate_loyalty_points
from erpnext.selling.doctype.pos_invoice.pos import update_multi_mode_option

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice, set_account_for_mode_of_payment

from six import iteritems

class POSInvoice(SalesInvoice):
	def __init__(self, *args, **kwargs):
		super(POSInvoice, self).__init__(*args, **kwargs)
	
	def validate(self):
		# run on validate method of selling controller
		super(SalesInvoice, self).validate()
		self.validate_auto_set_posting_time()
		self.validate_pos_paid_amount()
		self.validate_pos_return()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_debit_to_acc()
		self.validate_write_off_account()
		self.validate_account_for_change_amount()
		self.validate_item_cost_centers()
		self.set_status()
		if cint(self.is_pos):
			self.validate_pos()
			if not self.is_return:
				self.verify_payment_amount_is_positive()
			if self.is_return:
				self.verify_payment_amount_is_negative()
		
		if self.redeem_loyalty_points:
			lp = frappe.get_doc('Loyalty Program', self.loyalty_program)
			self.loyalty_redemption_account = lp.expense_account if not self.loyalty_redemption_account else self.loyalty_redemption_account
			self.loyalty_redemption_cost_center = lp.cost_center if not self.loyalty_redemption_cost_center else self.loyalty_redemption_cost_center

		if self.redeem_loyalty_points and self.loyalty_program and self.loyalty_points:
			validate_loyalty_points(self, self.loyalty_points)
	
	def before_save(self):
		set_account_for_mode_of_payment(self)

	def on_submit(self):
		# create the loyalty point ledger entry if the customer is enrolled in any loyalty program
		if self.loyalty_program:
			self.make_loyalty_point_entry()

		if self.redeem_loyalty_points and self.loyalty_points:
			self.apply_loyalty_points()
	
	def on_cancel(self):
		# run on cancel method of selling controller
		super(SalesInvoice, self).on_cancel()
		if self.loyalty_program:
			self.delete_loyalty_point_entry()
	
	def on_update(self):
		# return process?
		pass

	def validate_pos_paid_amount(self):
		if len(self.payments) == 0 and self.is_pos:
			frappe.throw(_("At least one mode of payment is required for POS invoice."))
	
	def validate_account_for_change_amount(self):
		if flt(self.change_amount) and not self.account_for_change_amount:
			msgprint(_("Please enter Account for Change Amount"), raise_exception=1)

	def verify_payment_amount_is_positive(self):
		for entry in self.payments:
			if entry.amount < 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be positive").format(entry.idx))

	def verify_payment_amount_is_negative(self):
		for entry in self.payments:
			if entry.amount > 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be negative").format(entry.idx))
	
	def validate_pos_return(self):
		if self.is_pos and self.is_return:
			total_amount_in_payments = 0
			for payment in self.payments:
				total_amount_in_payments += payment.amount
			invoice_total = self.rounded_total or self.grand_total
			if total_amount_in_payments < invoice_total:
				frappe.throw(_("Total payments amount can't be greater than {}".format(-invoice_total)))
	
	def set_pos_fields(self, for_validate=False):
		"""Set retail related fields from POS Profiles"""
		from erpnext.stock.get_item_details import get_pos_profile_item_details, get_pos_profile
		if not self.pos_profile:
			pos_profile = get_pos_profile(self.company) or {}
			self.pos_profile = pos_profile.get('name')

		pos = {}
		if self.pos_profile:
			pos = frappe.get_doc('POS Profile', self.pos_profile)

		if not self.get('payments') and not for_validate:
			update_multi_mode_option(self, pos)

		if not self.account_for_change_amount:
			self.account_for_change_amount = frappe.get_cached_value('Company',  self.company,  'default_cash_account')

		if pos:
			self.allow_print_before_pay = pos.allow_print_before_pay

			if not for_validate and not self.customer:
				self.customer = pos.customer

			self.ignore_pricing_rule = pos.ignore_pricing_rule
			if pos.get('account_for_change_amount'):
				self.account_for_change_amount = pos.get('account_for_change_amount')

			for fieldname in ('territory', 'naming_series', 'currency', 'letter_head', 'tc_name',
				'company', 'select_print_heading', 'cash_bank_account', 'write_off_account', 'taxes_and_charges',
				'write_off_cost_center', 'apply_discount_on', 'cost_center'):
					if (not for_validate) or (for_validate and not self.get(fieldname)):
						self.set(fieldname, pos.get(fieldname))

			customer_price_list = frappe.get_value("Customer", self.customer, 'default_price_list')

			if pos.get("company_address"):
				self.company_address = pos.get("company_address")

			if not customer_price_list:
				self.set('selling_price_list', pos.get('selling_price_list'))

			if not for_validate:
				self.update_stock = cint(pos.get("update_stock"))

			# set pos values in items
			for item in self.get("items"):
				if item.get('item_code'):
					profile_details = get_pos_profile_item_details(pos, frappe._dict(item.as_dict()), pos)
					for fname, val in iteritems(profile_details):
						if (not for_validate) or (for_validate and not item.get(fname)):
							item.set(fname, val)

			# fetch terms
			if self.tc_name and not self.terms:
				self.terms = frappe.db.get_value("Terms and Conditions", self.tc_name, "terms")

			# fetch charges
			if self.taxes_and_charges and not len(self.get("taxes")):
				self.set_taxes()

		return pos

	def set_missing_values(self, for_validate=False):
		pos = self.set_pos_fields(for_validate)

		if not self.debit_to:
			self.debit_to = get_party_account("Customer", self.customer, self.company)
			self.party_account_currency = frappe.db.get_value("Account", self.debit_to, "account_currency", cache=True)
		if not self.due_date and self.customer:
			self.due_date = get_due_date(self.posting_date, "Customer", self.customer, self.company)

		super(POSInvoice, self).set_missing_values(for_validate)

		print_format = pos.get("print_format_for_online") if pos else None
		if not print_format and not cint(frappe.db.get_value('Print Format', 'POS Invoice', 'disabled')):
			print_format = 'POS Invoice'

		if pos:
			return {
				"print_format": print_format,
				"allow_edit_rate": pos.get("allow_user_to_edit_rate"),
				"allow_edit_discount": pos.get("allow_user_to_edit_discount"),
				"campaign": pos.get("campaign"),
				"allow_print_before_pay": pos.get("allow_print_before_pay")
			}

	def set_account_for_mode_of_payment(self):
		for data in self.payments:
			if not data.account:
				data.account = get_bank_cash_account(data.mode_of_payment, self.company).get("account")

def process_merging_into_sales_invoice():
	filters = {
		'consolidated_invoice': [ 'in', [ '', None ]]
	}
	pos_invoices = frappe.db.get_all('POS Invoice', filters=filters,
		fields=['name', 'posting_date', 'grand_total', 'customer'])

	# pos_invoice_customer_map = { 'Customer 1': [{}, {}, {}], 'Custoemr 2' : [{}] }
	pos_invoice_customer_map = {}

	for invoice in pos_invoices:
		customer = invoice['customer']
		pos_invoice_customer_map.setdefault(customer, [])
		pos_invoice_customer_map[customer].append(invoice)
	
	create_sales_invoices(pos_invoice_customer_map)
	create_merge_logs(pos_invoice_customer_map)

def create_sales_invoices(pos_invoice_customer_map):
	for customer, invoices in iteritems(pos_invoice_customer_map):
		sales_invoice = frappe.new_doc('Sales Invoice')
		sales_invoice.customer = customer
		sales_invoice.is_pos = 1
		sales_invoice.posting_date = getdate(nowdate())

		for d in invoices:
			d.consolidated_invoice = sales_invoice.name
			doc = frappe.get_doc('POS Invoice', d.name)
			sales_invoice = get_mapped_doc("POS Invoice", d.name, {
				"POS Invoice": {
					"doctype": "Sales Invoice",
					"validation": {
						"docstatus": ["=", 1]
					}
				},
				"POS Invoice Item": {
					"doctype": "Sales Invoice Item",
				}
			}, sales_invoice)

		sales_invoice.save()
		sales_invoice.submit()
		doc.update({'consolidated_invoice': sales_invoice.name})
		doc.save()


def create_merge_logs(pos_invoice_customer_map):	
	for customer, invoices in iteritems(pos_invoice_customer_map):
		merge_log = frappe.new_doc('POS Invoice Merge Log')
		merge_log.posting_date = getdate(nowdate())
		merge_log.customer = customer

		refs = []
		for d in invoices:
			refs.append({
				'pos_invoice': d.name,
				'date': d.posting_date,
				'amount': d.grand_total
			})
			merge_log.consolidated_invoice = d.consolidated_invoice

		merge_log.set('pos_invoices', refs)
		merge_log.save()
		merge_log.submit()
