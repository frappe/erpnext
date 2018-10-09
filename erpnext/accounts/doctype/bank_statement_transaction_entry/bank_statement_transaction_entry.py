# -*- coding: utf-8 -*-
# Copyright (c) 2017, sathishpy@gmail.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.utils import get_outstanding_invoices
from frappe.utils import nowdate
from datetime import datetime
import csv, os, re, io
import difflib
import copy

class BankStatementTransactionEntry(Document):
	def autoname(self):
		self.name = self.bank_account + "-" + self.from_date + "-" + self.to_date
		mapper_name = self.bank + "-Statement-Settings"
		if not frappe.db.exists("Bank Statement Settings", mapper_name):
			self.create_settings(self.bank)
		self.bank_settings = mapper_name

	def create_settings(self, bank):
		mapper = frappe.new_doc("Bank Statement Settings")
		mapper.bank = bank
		mapper.date_format = "%Y-%m-%d"
		mapper.bank_account = self.bank_account
		for header in ["Date", "Particulars", "Withdrawals", "Deposits", "Balance"]:
			header_item = mapper.append("header_items", {})
			header_item.mapped_header = header_item.stmt_header = header
		mapper.save()

	def on_update(self):
		if (not self.bank_statement):
			self.reconciled_transaction_items = self.new_transaction_items = []
			return

		if len(self.new_transaction_items + self.reconciled_transaction_items) == 0:
			self.populate_payment_entries()
		else:
			self.match_invoice_to_payment()

	def validate(self):
		if not self.new_transaction_items:
			self.populate_payment_entries()

	def get_statement_headers(self):
		if not self.bank_settings:
			frappe.throw("Bank Data mapper doesn't exist")
		mapper_doc = frappe.get_doc("Bank Statement Settings", self.bank_settings)
		headers = {entry.mapped_header:entry.stmt_header for entry in mapper_doc.header_items}
		return headers

	def populate_payment_entries(self):
		if self.bank_statement is None: return
		filename = self.bank_statement.split("/")[-1]
		if (len(self.new_transaction_items + self.reconciled_transaction_items) > 0):
			frappe.throw("Transactions already retreived from the statement")

		date_format = frappe.get_value("Bank Statement Settings", self.bank_settings, "date_format")
		if (date_format is None):
			date_format = '%Y-%m-%d'
		if self.bank_settings:
			mapped_items = frappe.get_doc("Bank Statement Settings", self.bank_settings).mapped_items
		statement_headers = self.get_statement_headers()
		transactions = get_transaction_entries(filename, statement_headers)
		for entry in transactions:
			date = entry[statement_headers["Date"]].strip()
			#print("Processing entry DESC:{0}-W:{1}-D:{2}-DT:{3}".format(entry["Particulars"], entry["Withdrawals"], entry["Deposits"], entry["Date"]))
			if (not date): continue
			transaction_date = datetime.strptime(date, date_format).date()
			if (self.from_date and transaction_date < datetime.strptime(self.from_date, '%Y-%m-%d').date()): continue
			if (self.to_date and transaction_date > datetime.strptime(self.to_date, '%Y-%m-%d').date()): continue
			bank_entry = self.append('new_transaction_items', {})
			bank_entry.transaction_date = transaction_date
			bank_entry.description = entry[statement_headers["Particulars"]]

			mapped_item = next((entry for entry in mapped_items if entry.mapping_type == "Transaction" and frappe.safe_decode(entry.bank_data.lower()) in frappe.safe_decode(bank_entry.description.lower())), None)
			if (mapped_item is not None):
				bank_entry.party_type = mapped_item.mapped_data_type
				bank_entry.party = mapped_item.mapped_data
			else:
				bank_entry.party_type = "Supplier" if not entry[statement_headers["Deposits"]].strip() else "Customer"
				party_list = frappe.get_all(bank_entry.party_type, fields=["name"])
				parties = [party.name for party in party_list]
				matches = difflib.get_close_matches(frappe.safe_decode(bank_entry.description.lower()), parties, 1, 0.4)
				if len(matches) > 0: bank_entry.party = matches[0]
			bank_entry.amount = -float(entry[statement_headers["Withdrawals"]]) if not entry[statement_headers["Deposits"]].strip() else float(entry[statement_headers["Deposits"]])
		self.map_unknown_transactions()
		self.map_transactions_on_journal_entry()

	def map_transactions_on_journal_entry(self):
		for entry in self.new_transaction_items:
			vouchers = frappe.db.sql("""select name, posting_date from `tabJournal Entry`
										where posting_date='{0}' and total_credit={1} and cheque_no='{2}' and docstatus != 2
									""".format(entry.transaction_date, abs(entry.amount), frappe.safe_decode(entry.description)), as_dict=True)
			if (len(vouchers) == 1):
				entry.reference_name = vouchers[0].name

	def populate_matching_invoices(self):
		self.payment_invoice_items = []
		self.map_unknown_transactions()
		added_invoices = []
		for entry in self.new_transaction_items:
			if (not entry.party or entry.party_type == "Account"): continue
			account = self.receivable_account if entry.party_type == "Customer" else self.payable_account
			invoices = get_outstanding_invoices(entry.party_type, entry.party, account)
			transaction_date = datetime.strptime(entry.transaction_date, "%Y-%m-%d").date()
			outstanding_invoices = [invoice for invoice in invoices if invoice.posting_date <= transaction_date]
			amount = abs(entry.amount)
			matching_invoices = [invoice for invoice in outstanding_invoices if invoice.outstanding_amount == amount]
			sorted(outstanding_invoices, key=lambda k: k['posting_date'])
			for e in (matching_invoices + outstanding_invoices):
				added = next((inv for inv in added_invoices if inv == e.get('voucher_no')), None)
				if (added is not None): continue
				ent = self.append('payment_invoice_items', {})
				ent.transaction_date = entry.transaction_date
				ent.payment_description = frappe.safe_decode(entry.description)
				ent.party_type = entry.party_type
				ent.party = entry.party
				ent.invoice = e.get('voucher_no')
				added_invoices += [ent.invoice]
				ent.invoice_type = "Sales Invoice" if entry.party_type == "Customer" else "Purchase Invoice"
				ent.invoice_date = e.get('posting_date')
				ent.outstanding_amount = e.get('outstanding_amount')
				ent.allocated_amount = min(float(e.get('outstanding_amount')), amount)
				amount -= float(e.get('outstanding_amount'))
				if (amount <= 5): break
		self.match_invoice_to_payment()
		self.populate_matching_vouchers()
		self.map_transactions_on_journal_entry()

	def match_invoice_to_payment(self):
		added_payments = []
		for entry in self.new_transaction_items:
			if (not entry.party or entry.party_type == "Account"): continue
			entry.account = self.receivable_account if entry.party_type == "Customer" else self.payable_account
			amount = abs(entry.amount)
			payment, matching_invoices = None, []
			for inv_entry in self.payment_invoice_items:
				if (inv_entry.payment_description != frappe.safe_decode(entry.description) or inv_entry.transaction_date != entry.transaction_date): continue
				if (inv_entry.party != entry.party): continue
				matching_invoices += [inv_entry.invoice_type + "|" + inv_entry.invoice]
				payment = get_payments_matching_invoice(inv_entry.invoice, entry.amount, entry.transaction_date)
				doc = frappe.get_doc(inv_entry.invoice_type, inv_entry.invoice)
				inv_entry.invoice_date = doc.posting_date
				inv_entry.outstanding_amount = doc.outstanding_amount
				inv_entry.allocated_amount = min(float(doc.outstanding_amount), amount)
				amount -= inv_entry.allocated_amount
				if (amount < 0): break

			amount = abs(entry.amount)
			if (payment is None):
				order_doctype = "Sales Order" if entry.party_type=="Customer" else "Purchase Order"
				from erpnext.controllers.accounts_controller import get_advance_payment_entries
				payment_entries = get_advance_payment_entries(entry.party_type, entry.party, entry.account, order_doctype, against_all_orders=True)
				payment_entries += self.get_matching_payments(entry.party, amount, entry.transaction_date)
				payment = next((payment for payment in payment_entries if payment.amount == amount and payment not in added_payments), None)
				if (payment is None):
					print("Failed to find payments for {0}:{1}".format(entry.party, amount))
					continue
			added_payments += [payment]
			entry.reference_type = payment.reference_type
			entry.reference_name = payment.reference_name
			entry.mode_of_payment = "Wire Transfer"
			entry.outstanding_amount = min(amount, 0)
			if (entry.payment_reference is None):
				entry.payment_reference = frappe.safe_decode(entry.description)
			entry.invoices = ",".join(matching_invoices)
			#print("Matching payment is {0}:{1}".format(entry.reference_type, entry.reference_name))

	def get_matching_payments(self, party, amount, pay_date):
		query = """select 'Payment Entry' as reference_type, name as reference_name, paid_amount as amount
					from `tabPayment Entry` where party='{0}' and paid_amount={1} and posting_date='{2}' and docstatus != 2
					""".format(party, amount, pay_date)
		matching_payments = frappe.db.sql(query, as_dict=True)
		return matching_payments

	def map_unknown_transactions(self):
		for entry in self.new_transaction_items:
			if (entry.party): continue
			inv_type = "Sales Invoice" if (entry.amount > 0) else "Purchase Invoice"
			party_type = "customer" if (entry.amount > 0) else "supplier"

			query = """select posting_date, name, {0}, outstanding_amount
							from `tab{1}` where ROUND(outstanding_amount)={2} and posting_date < '{3}'
							""".format(party_type, inv_type, round(abs(entry.amount)), entry.transaction_date)
			invoices = frappe.db.sql(query, as_dict = True)
			if(len(invoices) > 0):
				entry.party = invoices[0].get(party_type)

	def populate_matching_vouchers(self):
		for entry in self.new_transaction_items:
			if (not entry.party or entry.reference_name): continue
			print("Finding matching voucher for {0}".format(frappe.safe_decode(entry.description)))
			amount = abs(entry.amount)
			invoices = []
			vouchers = get_matching_journal_entries(self.from_date, self.to_date, entry.party, self.bank_account, amount)
			if len(vouchers) == 0: continue
			for voucher in vouchers:
				added = next((entry.invoice for entry in self.payment_invoice_items if entry.invoice == voucher.voucher_no), None)
				if (added):
					print("Found voucher {0}".format(added))
					continue
				print("Adding voucher {0} {1} {2}".format(voucher.voucher_no, voucher.posting_date, voucher.debit))
				ent = self.append('payment_invoice_items', {})
				ent.invoice_date = voucher.posting_date
				ent.invoice_type = "Journal Entry"
				ent.invoice = voucher.voucher_no
				ent.payment_description = frappe.safe_decode(entry.description)
				ent.allocated_amount = max(voucher.debit, voucher.credit)

				invoices += [ent.invoice_type + "|" + ent.invoice]
				entry.reference_type = "Journal Entry"
				entry.mode_of_payment = "Wire Transfer"
				entry.reference_name = ent.invoice
				#entry.account = entry.party
				entry.invoices = ",".join(invoices)
				break


	def create_payment_entries(self):
		for payment_entry in self.new_transaction_items:
			if (not payment_entry.party): continue
			if (payment_entry.reference_name): continue
			print("Creating payment entry for {0}".format(frappe.safe_decode(payment_entry.description)))
			if (payment_entry.party_type == "Account"):
				payment = self.create_journal_entry(payment_entry)
				invoices = [payment.doctype + "|" + payment.name]
				payment_entry.invoices = ",".join(invoices)
			else:
				payment = self.create_payment_entry(payment_entry)
				invoices = [entry.reference_doctype + "|" + entry.reference_name for entry in payment.references if entry is not None]
				payment_entry.invoices = ",".join(invoices)
				payment_entry.mode_of_payment = payment.mode_of_payment
				payment_entry.account = self.receivable_account if payment_entry.party_type == "Customer" else self.payable_account
			payment_entry.reference_name = payment.name
			payment_entry.reference_type = payment.doctype
		frappe.msgprint(_("Successfully created payment entries"))

	def create_payment_entry(self, pe):
		payment = frappe.new_doc("Payment Entry")
		payment.posting_date = pe.transaction_date
		payment.payment_type = "Receive" if pe.party_type == "Customer" else "Pay"
		payment.mode_of_payment = "Wire Transfer"
		payment.party_type = pe.party_type
		payment.party = pe.party
		payment.paid_to = self.bank_account if pe.party_type == "Customer" else self.payable_account
		payment.paid_from = self.receivable_account if pe.party_type == "Customer" else self.bank_account
		payment.paid_amount = payment.received_amount = abs(pe.amount)
		payment.reference_no = pe.description
		payment.reference_date = pe.transaction_date
		payment.save()
		for inv_entry in self.payment_invoice_items:
			if (pe.description != inv_entry.payment_description or pe.transaction_date != inv_entry.transaction_date): continue
			if (pe.party != inv_entry.party): continue
			reference = payment.append("references", {})
			reference.reference_doctype = inv_entry.invoice_type
			reference.reference_name = inv_entry.invoice
			reference.allocated_amount = inv_entry.allocated_amount
			print ("Adding invoice {0} {1}".format(reference.reference_name, reference.allocated_amount))
		payment.setup_party_account_field()
		payment.set_missing_values()
		#payment.set_exchange_rate()
		#payment.set_amounts()
		#print("Created payment entry {0}".format(payment.as_dict()))
		payment.save()
		return payment

	def create_journal_entry(self, pe):
		je = frappe.new_doc("Journal Entry")
		je.is_opening = "No"
		je.voucher_type = "Bank Entry"
		je.cheque_no = pe.description
		je.cheque_date = pe.transaction_date
		je.remark = pe.description
		je.posting_date = pe.transaction_date
		if (pe.amount < 0):
			je.append("accounts", {"account": pe.party, "debit_in_account_currency": abs(pe.amount)})
			je.append("accounts", {"account": self.bank_account, "credit_in_account_currency": abs(pe.amount)})
		else:
			je.append("accounts", {"account": pe.party, "credit_in_account_currency": pe.amount})
			je.append("accounts", {"account": self.bank_account, "debit_in_account_currency": pe.amount})
		je.save()
		return je

	def update_payment_entry(self, payment):
		lst = []
		invoices = payment.invoices.strip().split(',')
		if (len(invoices) == 0): return
		amount = float(abs(payment.amount))
		for invoice_entry in invoices:
			if (not invoice_entry.strip()): continue
			invs = invoice_entry.split('|')
			invoice_type, invoice = invs[0], invs[1]
			outstanding_amount = frappe.get_value(invoice_type, invoice, 'outstanding_amount')

			lst.append(frappe._dict({
				'voucher_type': payment.reference_type,
				'voucher_no' : payment.reference_name,
				'against_voucher_type' : invoice_type,
				'against_voucher'  : invoice,
				'account' : payment.account,
				'party_type': payment.party_type,
				'party': frappe.get_value("Payment Entry", payment.reference_name, "party"),
				'unadjusted_amount' : float(amount),
				'allocated_amount' : min(outstanding_amount, amount)
			}))
			amount -= outstanding_amount
		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			try:
				reconcile_against_document(lst)
			except:
				frappe.throw("Exception occurred while reconciling {0}".format(payment.reference_name))

	def submit_payment_entries(self):
		for payment in self.new_transaction_items:
			if payment.reference_name is None: continue
			doc = frappe.get_doc(payment.reference_type, payment.reference_name)
			if doc.docstatus == 1:
				if (payment.reference_type == "Journal Entry"): continue
				if doc.unallocated_amount == 0: continue
				print("Reconciling payment {0}".format(payment.reference_name))
				self.update_payment_entry(payment)
			else:
				print("Submitting payment {0}".format(payment.reference_name))
				if (payment.reference_type == "Payment Entry"):
					if (payment.payment_reference):
						doc.reference_no = payment.payment_reference
					doc.mode_of_payment = payment.mode_of_payment
				doc.save()
				doc.submit()
		self.move_reconciled_entries()
		self.populate_matching_invoices()

	def move_reconciled_entries(self):
		idx = 0
		while idx < len(self.new_transaction_items):
			entry = self.new_transaction_items[idx]
			try:
				print("Checking transaction {0}: {2} in {1} entries".format(idx, len(self.new_transaction_items), frappe.safe_decode(entry.description)))
			except UnicodeEncodeError:
				pass
			idx += 1
			if entry.reference_name is None: continue
			doc = frappe.get_doc(entry.reference_type, entry.reference_name)
			if doc.docstatus == 1 and (entry.reference_type == "Journal Entry" or doc.unallocated_amount == 0):
				self.remove(entry)
				rc_entry = self.append('reconciled_transaction_items', {})
				dentry = entry.as_dict()
				dentry.pop('idx', None)
				rc_entry.update(dentry)
				idx -= 1


def get_matching_journal_entries(from_date, to_date, account, against, amount):
	query = """select voucher_no, posting_date, account, against, debit_in_account_currency as debit, credit_in_account_currency as credit
							      from `tabGL Entry`
								  where posting_date between '{0}' and '{1}' and account = '{2}' and against = '{3}' and debit = '{4}'
								  """.format(from_date, to_date, account, against, amount)
	jv_entries = frappe.db.sql(query, as_dict=True)
	#print("voucher query:{0}\n Returned {1} entries".format(query, len(jv_entries)))
	return jv_entries

def get_payments_matching_invoice(invoice, amount, pay_date):
	query = """select pe.name as reference_name, per.reference_doctype as reference_type, per.outstanding_amount, per.allocated_amount
				from `tabPayment Entry Reference` as per JOIN `tabPayment Entry` as pe on pe.name = per.parent
				where per.reference_name='{0}' and (posting_date='{1}' or reference_date='{1}') and pe.docstatus != 2
				""".format(invoice, pay_date)
	payments = frappe.db.sql(query, as_dict=True)
	if (len(payments) == 0): return
	payment = next((payment for payment in payments if payment.allocated_amount == amount), payments[0])
	#Hack: Update the reference type which is set to invoice type
	payment.reference_type = "Payment Entry"
	return payment

def is_headers_present(headers, row):
	for header in headers:
		if header not in row:
			return False
	return True

def get_header_index(headers, row):
	header_index = {}
	for header in headers:
		if header in row:
			header_index[header] = row.index(header)
	return header_index

def get_transaction_info(headers, header_index, row):
	transaction = {}
	for header in headers:
		transaction[header] = row[header_index[header]]
		if (transaction[header] == None):
			transaction[header] = ""
	return transaction

def get_transaction_entries(filename, headers):
	header_index = {}
	rows, transactions = [], []

	if (filename.lower().endswith("xlsx")):
		from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
		rows = read_xlsx_file_from_attached_file(file_id=filename)
	elif (filename.lower().endswith("csv")):
		from frappe.utils.csvutils import read_csv_content
		_file = frappe.get_doc("File", {"file_name": filename})
		filepath = _file.get_full_path()
		with open(filepath,'rb') as csvfile:
			rows = read_csv_content(csvfile.read())
	elif (filename.lower().endswith("xls")):
		rows = get_rows_from_xls_file(filename)
	else:
		frappe.throw("Only .csv and .xlsx files are supported currently")

	stmt_headers = headers.values()
	for row in rows:
		if len(row) == 0 or row[0] == None or not row[0]: continue
		#print("Processing row {0}".format(row))
		if header_index:
			transaction = get_transaction_info(stmt_headers, header_index, row)
			transactions.append(transaction)
		elif is_headers_present(stmt_headers, row):
			header_index = get_header_index(stmt_headers, row)
	return transactions

def get_rows_from_xls_file(filename):
	_file = frappe.get_doc("File", {"file_name": filename})
	filepath = _file.get_full_path()
	import xlrd
	book = xlrd.open_workbook(filepath)
	sheets = book.sheets()
	rows = []
	for row in range(1, sheets[0].nrows):
		row_values = []
		for col in range(1, sheets[0].ncols):
			row_values.append(sheets[0].cell_value(row, col))
		rows.append(row_values)
	return rows
