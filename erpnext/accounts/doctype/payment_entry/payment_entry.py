# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _, scrub
from frappe.utils import flt
from erpnext.accounts.utils import get_outstanding_invoices, get_account_currency, get_balance_on
from erpnext.accounts.party import get_party_account
from erpnext.accounts.doctype.journal_entry.journal_entry import get_average_exchange_rate
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.general_ledger import make_gl_entries

from erpnext.controllers.accounts_controller import AccountsController


class PaymentEntry(AccountsController):
	def validate(self):
		self.set_missing_values()
		self.validate_party_details()
		self.validate_allocated_amounts()
		self.set_exchange_rate()
		self.set_amounts()
		self.validate_mandatory()
		self.set_write_off_amount()
		
	def on_submit(self):
		self.make_gl_entries()
		self.update_advance_paid()
		
	def on_cancel(self):
		self.make_gl_entries()
		self.update_advance_paid()
				
	def set_missing_values(self):
		if self.payment_type == "Receive":
			self.paid_from = self.paid_from_account_currency = self.paid_from_account_balance = None
		elif self.payment_type == "Pay":
			self.paid_to = self.paid_to_account_currency = self.paid_to_account_balance = None
		elif self.payment_type == "Internal Transfer":
			self.party = self.party_account = self.party_account_currency = self.party_balance = None
		
		if self.party:
			if self.party_account:				
				if not self.party_account_currency:
					self.party_account_currency = get_account_currency(self.party_account)
				
				if not self.party_balance:
					self.party_balance = get_balance_on(party_type=self.party_type,
						party=self.party, date=self.posting_date)
			else:
				self.party_account = get_party_account(self.party_type, self.party, self.company)
				
		if self.paid_from:
			acc = get_account_currency_and_balance(self.paid_from, self.posting_date)
			self.paid_from_account_currency = acc.account_currency
			self.paid_from_account_balance = acc.account_balance
				
		if self.paid_to:
			acc = get_account_currency_and_balance(self.paid_to, self.posting_date)
			self.paid_to_account_currency = acc.account_currency
			self.paid_to_account_balance = acc.account_balance
							
	def validate_party_details(self):
		if self.party:
			if not frappe.db.exists(self.party_type, self.party):
				frappe.throw(_("Invalid {0}: {1}").format(self.party_type, self.party))
				
			if self.party_account:
				account_type = frappe.db.get_value("Account", self.party_account, "account_type")
				
				if self.party_type == "Customer" and account_type != "Receivable":
					frappe.throw(_("Account Type must be Receivable for {0}").format(self.party_account))
					
				if self.party_type == "Supplier" and account_type != "Payable":
					frappe.throw(_("Account Type must be Payable for {0}").format(self.party_account))
				
	def validate_allocated_amounts(self):
		if self.payment_type == "Internal Transfer":
			self.references = []
			self.total_allocated_amount = 0
			return
			
		self.total_allocated_amount, self.base_total_allocated_amount = 0, 0
		for d in self.get("references"):
			if d.allocated_amount:
				self.total_allocated_amount += flt(d.allocated_amount)
				self.base_total_allocated_amount += flt(flt(d.allocated_amount) * flt(d.exchange_rate), 
					self.precision("base_paid_amount"))

		party_amount_field = "received_amount" if self.payment_type == "Pay" else "paid_amount"
			
		if self.total_allocated_amount != self.get(party_amount_field):
			frappe.throw(_("Total Allocated Amount must be equal to {0} ({1})")
				.format(self.get(party_amount_field), self.meta.get_label(party_amount_field)))
				
	def set_exchange_rate(self):
		if self.paid_from:
			if self.paid_from_account_currency != self.company_currency:
				self.source_exchange_rate = get_average_exchange_rate(self.paid_from)
			else:
				self.source_exchange_rate = 1
				
		if self.paid_to:
			self.target_exchange_rate = get_exchange_rate(self.paid_to_account_currency, 
				self.company_currency)
		
	def set_amounts(self):
		self.base_paid_amount, self.base_received_amount, self.difference_amount = 0, 0, 0
		if self.paid_amount:
			if self.paid_from:
				self.base_paid_amount = flt(flt(self.paid_amount) * flt(self.source_exchange_rate), 
					self.precision("base_paid_amount"))
			else:
				self.base_paid_amount = self.base_total_allocated_amount
				
		if self.received_amount:
			if self.paid_to:
				self.base_received_amount = flt(flt(self.received_amount) * flt(self.target_exchange_rate), 
					self.precision("base_received_amount"))
			else:
				self.base_received_amount = self.base_total_allocated_amount
		
		self.difference_amount = self.base_paid_amount - self.base_received_amount
		
	def validate_mandatory(self):
		mandatory_fields = ["paid_amount", "received_amount", "base_paid_amount", "base_received_amount", 
			"reference_no", "reference_date"]
		if self.payment_type == "Receive":
			mandatory_fields += ["party_type", "party", "party_account", "party_account_currency", 
				"paid_to", "paid_to_account_currency", "references", "total_allocated_amount"]
		elif self.payment_type == "Pay":
			mandatory_fields += ["party_type", "party", "party_account", "party_account_currency", 
				"paid_from", "paid_from_account_currency", "references", "total_allocated_amount"]
		else:
			mandatory_fields += ["paid_from", "paid_from_account_currency",
				"paid_to", "paid_to_account_currency"]
				
		if self.paid_from:
			mandatory_fields.append("source_exchange_rate")
		if self.paid_to:
			mandatory_fields.append("target_exchange_rate")

		for field in mandatory_fields:
			if not self.get(field):
				frappe.throw(_("{0} is mandatory").format(self.meta.get_label(field)))

	def set_write_off_amount(self):
		if self.payment_type in ("Receive", "Pay"):
			bank_account_currency = self.paid_from_account_currency \
				if self.paid_from else self.paid_to_account_currency
				
			if self.party_account_currency == bank_account_currency and self.difference_amount:
				self.write_off_amount = self.difference_amount
				
	def make_gl_entries(self):
		gl_entries = []
		self.add_party_gl_entries(gl_entries)
		self.add_bank_gl_entries(gl_entries)
		self.add_write_off_gl_entries(gl_entries)
		self.add_deductions_gl_entries(gl_entries)
		
		make_gl_entries(gl_entries, cancel = (self.docstatus==2))
		
		
	def add_party_gl_entries(self, gl_entries):
		if self.party_account:
			party_gl_dict = self.get_gl_dict({
				"account": self.party_account,
				"party_type": self.party_type,
				"party": self.party,
				"against": self.paid_from or self.paid_to,
				"account_currency": self.party_account_currency
			})
			
			for d in self.get("references"):
				party_gl_dict.update({
					"against_voucher_type": d.reference_doctype,
					"against_voucher": d.reference_name
				})
				
				allocated_amount_in_company_currency = flt(flt(d.allocated_amount) * flt(d.exchange_rate), 
					self.precision("paid_amount"))
					
				if self.payment_type == "Receive":
					party_gl_dict.update({
						"credit_in_account_currency": d.allocated_amount,
						"credit": allocated_amount_in_company_currency
					})
				elif self.payment_type == "Pay":
					party_gl_dict.update({
						"debit_in_account_currency": d.allocated_amount,
						"debit": allocated_amount_in_company_currency
					})
				
				gl_entries.append(party_gl_dict)
				
	def add_bank_gl_entries(self, gl_entries):
		if self.paid_from and self.paid_amount:
			gl_entries.append(
				self.get_gl_dict({
					"account": self.paid_from,
					"account_currency": self.paid_from_account_currency,
					"against": self.party_account,
					"credit_in_account_currency": self.paid_amount,
					"credit": self.base_paid_amount
				})
			)
		if self.paid_to and self.received_amount:
			gl_entries.append(
				self.get_gl_dict({
					"account": self.paid_to,
					"account_currency": self.paid_to_account_currency,
					"against": self.party,
					"debit_in_account_currency": self.received_amount,
					"debit": self.base_received_amount
				})
			)
			
	def add_write_off_gl_entries(self, gl_entries):
		if self.write_off_account and self.write_off_amount:
			write_off_account_currency = get_account_currency(self.write_off_account)
			if self.write_off_account_currency != self.company_currency:
				frappe.throw(_("Write Off Account currency must be same as {0}")
					.format(self.company_currency))

			gl_entries.append(
				self.get_gl_dict({
					"account": self.write_off_account,
					"against": self.party,
					"debit_in_account_currency": self.write_off_amount,
					"debit": self.write_off_amount,
					"cost_center": self.write_off_cost_center
				}, write_off_account_currency)
			)
		
	def add_deductions_gl_entries(self, gl_entries):
		pass

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
def get_write_off_account_and_cost_center(company):
	return frappe.db.get_value("Company", company, ["write_off_account", "cost_center"], as_dict=1)
	