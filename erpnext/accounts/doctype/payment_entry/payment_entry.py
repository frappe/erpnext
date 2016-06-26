# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _, scrub
from frappe.utils import flt, comma_or
from erpnext.accounts.utils import get_outstanding_invoices, get_account_currency, get_balance_on
from erpnext.accounts.party import get_party_account
from erpnext.accounts.doctype.journal_entry.journal_entry import get_average_exchange_rate
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.general_ledger import make_gl_entries

from erpnext.controllers.accounts_controller import AccountsController


class PaymentEntry(AccountsController):
	def validate(self):
		self.define_party_account_field()
		self.set_missing_values()
		self.validate_party_details()
		self.validate_bank_accounts()
		self.set_exchange_rate()
		self.set_amounts_in_company_currency()
		self.validate_reference_documents()
		self.set_total_allocated_amount()
		self.set_unallocated_amount()
		self.set_difference_amount()
		self.clear_unallocated_reference_document_rows()
		self.set_title()
		
	def on_submit(self):
		self.make_gl_entries()
		self.update_advance_paid()
		
	def on_cancel(self):
		self.make_gl_entries()
		self.update_advance_paid()
		
	def define_party_account_field(self):
		self.party_account_field = None
		
		if self.payment_type == "Receive":
			self.party_account_field = "paid_from"
		elif self.payment_type == "Pay":
			self.party_account_field = "paid_to"
					
	def set_missing_values(self):
		if self.payment_type == "Internal Transfer":
			for field in ("party", "party_balance", "total_allocated_amount", 
				"base_total_allocated_amount", "unallocated_amount"):
					self.set(field, None)
			self.references = []
		else:
			if not self.party_type:
				frappe.throw(_("Party Type is mandatory"))
				
			if not self.party:
				frappe.throw(_("Party is mandatory"))
		
		if self.party:
			if not self.party_balance:
				self.party_balance = get_balance_on(party_type=self.party_type,
					party=self.party, date=self.posting_date)
			
			if not self.get(self.party_account_field):
				party_account = get_party_account(self.party_type, self.party, self.company)
				self.set(self.party_account_field, party_account)
				
			self.party_account = self.get(self.party_account_field)
				
		if self.paid_from and not (self.paid_from_account_currency or self.paid_from_account_balance):
			acc = get_account_currency_and_balance(self.paid_from, self.posting_date)
			self.paid_from_account_currency = acc.account_currency
			self.paid_from_account_balance = acc.account_balance
				
		if self.paid_to and not (self.paid_to_account_currency or self.paid_to_account_balance):
			acc = get_account_currency_and_balance(self.paid_to, self.posting_date)
			self.paid_to_account_currency = acc.account_currency
			self.paid_to_account_balance = acc.account_balance
							
	def validate_party_details(self):
		if self.party:
			if not frappe.db.exists(self.party_type, self.party):
				frappe.throw(_("Invalid {0}: {1}").format(self.party_type, self.party))
			
			if self.party_account:
				party_account_type = "Receivable" if self.party_type=="Customer" else "Payable"
				self.validate_account_type(self.party_account, [party_account_type])
					
	def validate_bank_accounts(self):
		if self.payment_type in ("Pay", "Internal Transfer"):
			self.validate_account_type(self.paid_from, ["Bank", "Cash"])
			
		if self.payment_type in ("Receive", "Internal Transfer"):
			self.validate_account_type(self.paid_to, ["Bank", "Cash"])
			
	def validate_account_type(self, account, account_types):
		account_type = frappe.db.get_value("Account", account, "account_type")
		if account_type not in account_types:
			frappe.throw(_("Account Type for {0} must be {1}").format(comma_or(account_types)))
				
	def set_exchange_rate(self):
		if self.paid_from:
			if self.paid_from_account_currency == self.company_currency:
				self.source_exchange_rate = 1
			elif self.payment_type in ("Pay", "Internal Transfer"):
				self.source_exchange_rate = get_average_exchange_rate(self.paid_from)
			else:
				self.source_exchange_rate = get_exchange_rate(self.paid_from_account_currency, 
					self.company_currency)
		
		if self.paid_to:
			self.target_exchange_rate = get_exchange_rate(self.paid_to_account_currency, 
				self.company_currency)
		
	def set_amounts_in_company_currency(self):
		self.base_paid_amount, self.base_received_amount, self.difference_amount = 0, 0, 0
		if self.paid_amount:
			self.base_paid_amount = flt(flt(self.paid_amount) * flt(self.source_exchange_rate), 
				self.precision("base_paid_amount"))
				
		if self.received_amount:
			self.base_received_amount = flt(flt(self.received_amount) * flt(self.target_exchange_rate), 
				self.precision("base_received_amount"))
				
	def validate_reference_documents(self):
		if self.party_type == "Customer":
			valid_reference_doctypes = ("Sales Order", "Sales Invoice", "Journal Entry")
		else:
			valid_reference_doctypes = ("Purchase Order", "Purchase Invoice", "Journal Entry")
			
		for d in self.get("references"):
			if d.reference_doctype not in valid_reference_doctypes:
				frappe.throw(_("Reference Doctype must be one of {0}")
					.format(comma_or(valid_reference_doctypes)))
				
			elif d.reference_name:
				if not frappe.db.exists(d.reference_doctype, d.reference_name):
					frappe.throw(_("{0} {1} does not exist").format(d.reference_doctype, d.reference_name))
				else:
					ref_doc = frappe.get_doc(d.reference_doctype, d.reference_name)

					if d.reference_doctype != "Journal Entry" \
							and self.party != ref_doc.get(scrub(self.party_type)):
						frappe.throw(_("{0} {1} does not associated with {2} {3}")
							.format(d.reference_doctype, d.reference_name, self.party_type, self.party))
					
					if ref_doc.docstatus != 1:
						frappe.throw(_("{0} {1} must be submitted")
							.format(d.reference_doctype, d.reference_name))
				
	def set_total_allocated_amount(self):
		if self.payment_type == "Internal Transfer":
			return
			
		self.total_allocated_amount, self.base_total_allocated_amount = 0, 0
		for d in self.get("references"):
			if d.allocated_amount:
				if d.allocated_amount > d.outstanding_amount:
					frappe.throw(_("Row #{0}: Allocated amount cannot be greater than outstanding amount")
						.format(d.idx))
				
				self.total_allocated_amount += flt(d.allocated_amount)
				self.base_total_allocated_amount += flt(flt(d.allocated_amount) * flt(d.exchange_rate), 
					self.precision("base_paid_amount"))
	
	def set_unallocated_amount(self):
		self.unallocated_amount = 0;
		if self.party:
			party_amount = self.paid_amount if self.payment_type=="Receive" else self.received_amount
			
			if self.total_allocated_amount < party_amount:
				self.unallocated_amount = party_amount - self.total_allocated_amount
				
	def set_difference_amount(self):
		base_unallocated_amount = self.unallocated_amount * \
			(self.source_exchange_rate if self.payment_type=="Receive" else self.target_exchange_rate)
			
		base_party_amount = self.base_total_allocated_amount + base_unallocated_amount
		
		if self.payment_type == "Receive":
			self.difference_amount = base_party_amount - self.base_received_amount
		elif self.payment_type == "Pay":
			self.difference_amount = self.base_paid_amount - base_party_amount
		else:
			self.difference_amount = self.base_paid_amount - flt(self.base_received_amount)
			
		for d in self.get("deductions"):
			if d.amount:
				self.difference_amount -= flt(d.amount)
				
	def clear_unallocated_reference_document_rows(self):
		self.set("references", self.get("references", {"allocated_amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tabPayment Entry Reference` 
			where parent = %s and allocated_amount = 0""", self.name)
			
	def set_title(self):
		if self.payment_type in ("Receive", "Pay"):
			self.title = self.party
		else:
			self.title = self.paid_from + " - " + self.paid_to
				
	def make_gl_entries(self):
		gl_entries = []
		self.add_party_gl_entries(gl_entries)
		self.add_bank_gl_entries(gl_entries)
		self.add_deductions_gl_entries(gl_entries)
		
		make_gl_entries(gl_entries, cancel = (self.docstatus==2))
		
	def add_party_gl_entries(self, gl_entries):
		if self.party_account:
			if self.payment_type=="Receive":
				party_account_currency = self.paid_from_account_currency
				against_account = self.paid_to
			else:
				 party_account_currency = self.paid_to_account_currency
				 against_account = self.paid_from
			
				
			party_gl_dict = self.get_gl_dict({
				"account": self.party_account,
				"party_type": self.party_type,
				"party": self.party,
				"against": against_account,
				"account_currency": party_account_currency
			})
			
			for d in self.get("references"):
				gle = party_gl_dict.copy()
				gle.update({
					"against_voucher_type": d.reference_doctype,
					"against_voucher": d.reference_name
				})
				
				allocated_amount_in_company_currency = flt(flt(d.allocated_amount) * flt(d.exchange_rate), 
					self.precision("paid_amount"))	
				
				if self.payment_type == "Receive":
					gle.update({
						"credit_in_account_currency": d.allocated_amount,
						"credit": allocated_amount_in_company_currency
					})
				elif self.payment_type == "Pay":
					gle.update({
						"debit_in_account_currency": d.allocated_amount,
						"debit": allocated_amount_in_company_currency
					})
				
				gl_entries.append(gle)
				
			if self.unallocated_amount:
				base_unallocated_amount = base_unallocated_amount = self.unallocated_amount * \
					(self.source_exchange_rate if self.payment_type=="Receive" else self.target_exchange_rate)
					
				gle = party_gl_dict.copy()
				if self.payment_type == "Receive":
					gle.update({
						"credit_in_account_currency": self.unallocated_amount,
						"credit": base_unallocated_amount
					})
				elif self.payment_type == "Pay":
					gle.update({
						"debit_in_account_currency": self.unallocated_amount,
						"debit": base_unallocated_amount
					})
				
				gl_entries.append(gle)
				
				
	def add_bank_gl_entries(self, gl_entries):
		if self.payment_type in ("Pay", "Internal Transfer"):
			gl_entries.append(
				self.get_gl_dict({
					"account": self.paid_from,
					"account_currency": self.paid_from_account_currency,
					"against": self.party if self.payment_type=="Pay" else self.paid_to,
					"credit_in_account_currency": self.paid_amount,
					"credit": self.base_paid_amount
				})
			)
		if self.payment_type in ("Receive", "Internal Transfer"):
			gl_entries.append(
				self.get_gl_dict({
					"account": self.paid_to,
					"account_currency": self.paid_to_account_currency,
					"against": self.party if self.payment_type=="Receive" else self.paid_from,
					"debit_in_account_currency": self.received_amount,
					"debit": self.base_received_amount
				})
			)
			
	def add_deductions_gl_entries(self, gl_entries):
		for d in self.get("deductions"):
			if d.amount:
				account_currency = get_account_currency(d.account)
				if account_currency != self.company_currency:
					frappe.throw(_("Currency for {0} must be {1}").format(d.account, self.company_currency))
					
				gl_entries.append(
					self.get_gl_dict({
						"account": d.account,
						"account_currency": account_currency,
						"against": self.party or self.paid_from,
						"debit_in_account_currency": d.amount,
						"debit": d.amount,
						"cost_center": d.cost_center
					})
				)
				
	def update_advance_paid(self):
		if self.payment_type in ("Receive", "Pay") and self.party:
			for d in self.get("references"):
				if d.allocated_amount and d.reference_doctype in ("Sales Order", "Purchase Order"):
					frappe.get_doc(d.reference_doctype, d.reference_name).set_total_advance_paid()

@frappe.whitelist()
def get_outstanding_reference_documents(args):
	args = json.loads(args)

	party_account_currency = get_account_currency(args.get("party_account"))
	company_currency = frappe.db.get_value("Company", args.get("company"), "default_currency")

	if ((args.get("party_type") == "Customer" and args.get("payment_type") == "Pay")
		or (args.get("party_type") == "Supplier" and args.get("payment_type") == "Received")):

		frappe.throw(_("Please enter the Reference Documents manually"))

	# Get all outstanding sales /purchase invoices
	outstanding_invoices = get_outstanding_invoices(args.get("party_type"), args.get("party"), 
		args.get("party_account"))
	
	# Get all SO / PO which are not fully billed or aginst which full advance not paid
	orders_to_be_billed =  get_orders_to_be_billed(args.get("party_type"), args.get("party"), 
		party_account_currency, company_currency)
	
	return outstanding_invoices + orders_to_be_billed
	
def get_orders_to_be_billed(party_type, party, party_account_currency, company_currency):
	voucher_type = 'Sales Order' if party_type == "Customer" else 'Purchase Order'

	ref_field = "base_grand_total" if party_account_currency == company_currency else "grand_total"

	orders = frappe.db.sql("""
		select
			name as voucher_no,
			{ref_field} as invoice_amount,
			({ref_field} - advance_paid) as outstanding_amount,
			transaction_date as posting_date
		from
			`tab{voucher_type}`
		where
			{party_type} = %s
			and docstatus = 1
			and ifnull(status, "") != "Closed"
			and {ref_field} > advance_paid
			and abs(100 - per_billed) > 0.01
		order by
			transaction_date, name
		""".format(**{
			"ref_field": ref_field,
			"voucher_type": voucher_type,
			"party_type": scrub(party_type)
		}), party, as_dict = True)

	order_list = []
	for d in orders:
		d["voucher_type"] = voucher_type
		d["exchange_rate"] = get_exchange_rate(party_account_currency, company_currency)
		order_list.append(d)

	return order_list
	
@frappe.whitelist()
def get_party_details(company, party_type, party, date):
	party_account = get_party_account(party_type, party, company)
	
	account_currency = get_account_currency(party_account)
	account_balance = get_balance_on(party_account, date)
	party_balance = get_balance_on(party_type=party_type, party=party)
	
	return {
		"party_account": party_account,
		"party_account_currency": account_currency,
		"party_balance": party_balance,
		"account_balance": account_balance
	}

@frappe.whitelist()	
def get_account_currency_and_balance(account, date):
	return frappe._dict({
		"account_currency": get_account_currency(account),
		"account_balance": get_balance_on(account, date)
	})
	
@frappe.whitelist()
def get_company_defaults(company):
	fields = ["write_off_account", "exchange_gain_loss_account", "cost_center"]
	ret = frappe.db.get_value("Company", company, fields, as_dict=1)
	
	for fieldname in fields:
		if not ret[fieldname]:
			frappe.throw(_("Please set default {0} in Company {1}")
				.format(frappe.get_meta("Company").get_label(fieldname), company))
	
	return ret