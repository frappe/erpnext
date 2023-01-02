# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe import _, qb, throw, bold
from erpnext.custom_utils import check_future_date
from erpnext.controllers.accounts_controller import AccountsController
from pypika import Case, functions as fn
from erpnext.production.doctype.transporter_rate.transporter_rate import get_transporter_rate
from frappe.utils import flt, cint
from erpnext.accounts.utils import get_tds_account,get_account_type
from erpnext.accounts.general_ledger import (
	get_round_off_account_and_cost_center,
	make_gl_entries,
	make_reverse_gl_entries,
	merge_similar_entries,
)

class EMEInvoice(AccountsController):
	def validate(self):
		check_future_date(self.posting_date)
		if not self.arrear_eme_payment:
			self.check_remarks()
		else:
			self.update_rate_amount()
		self.calculate_totals()
		self.set_status()
	def on_submit(self):
		self.update_logbook()
		self.make_gl_entries()
	def on_cancel(self):
		self.update_logbook()
		self.make_gl_entries()
	def update_logbook(self):
		for a in self.items:
			value = 1
			if self.docstatus == 2:
				value = 0
			logbook = frappe.get_doc("Logbook", a.logbook)
			logbook.db_set("paid", value)
	#Function to pay arrear base on change in rate
	def update_rate_amount(self):
		for a in self.get("items"):
			rate = self.get_rate(a.equipment_hiring_form,d.posting_date)
			if rate:
				a.new_rate = flt(rate)
				a.rate   = flt(a.new_rate) - flt(a.prev_rate)
				a.amount = flt(a.rate)  * flt(a.total_hours)

	def check_remarks(self):
		if not self.remarks:
			self.remarks = "EME payment to {0}".format(self.supplier)

	# fetch rate base on equipment hiring form
	def get_rate(self, ehf, posting_date):
		ehfr = qb.DocType("EHF Rate")
		rate = frappe.db.sql('''
					select hiring_rate from `tabEHF Rate` where parent = '{ehf}' 
						and from_date <= '{posting_date}' 
						and ifnull(to_date, NOW()) >= '{posting_date}' 
						and docstatus = 1 limit 1
					'''.format(ehf = ehf, posting_date = posting_date))
		if rate:
			return rate[0][0]
		else:
			throw("No rates defined in Equipment Hiring Form <b>{}</b> for date <b>{}</b>".format(frappe.get_desk_link("Equipment Hiring Form", ehf), posting_date),title="Hiring Rate Not Found")
	
	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get("amended_from"):
				self.status = "Draft"
			return

		outstanding_amount = flt(self.outstanding_amount, self.precision("outstanding_amount"))
		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if outstanding_amount > 0 and self.payable_amount > outstanding_amount:
					self.status = "Partly Paid"
				elif outstanding_amount > 0 :
					self.status = "Unpaid"
				elif outstanding_amount <= 0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		if update:
			self.db_set("status", self.status, update_modified=update_modified)

	# calculate total
	@frappe.whitelist()
	def calculate_totals(self):
		total = 0
		
		for a in self.items:
			total += flt(a.amount)
			if not a.expense_account:
				a.expense_account = frappe.db.get_value("Expense Head",a.expense_head,"expense_account")
				if not a.expense_account:
					throw("Expense Account not defined in Expense Head {}".format(bold(a.expense_head)),title="Expense Account Not Found")
		self.grand_total = total

		# tds
		if self.tds_percent:
			self.tds_amount  = flt(self.grand_total) * flt(self.tds_percent) / 100.0
			self.tds_account = get_tds_account(self.tds_percent,self.company)
		else:
			self.tds_amount  = 0
			self.tds_account = None

		total_deductions = 0
		for d in self.get('deduct_items'):
			if d.amount <= 0:
				frappe.throw("Deduction amount should be more than zero")
			if not d.account:
				frappe.throw("Account is mandatory for deductions")
			total_deductions += flt(d.amount, 2)
		self.total_deduction = total_deductions + flt(self.tds_amount)
		self.payable_amount = self.outstanding_amount = flt(self.grand_total, 2) - flt(self.total_deduction, 2)
	def make_gl_entries(self):
		gl_entries = []
		self.make_supplier_gl_entry(gl_entries)
		self.make_item_gl_entries(gl_entries)
		self.deduction_gl_entries(gl_entries)
		self.make_tds_gl_entries(gl_entries)
		gl_entries = merge_similar_entries(gl_entries)
		make_gl_entries(gl_entries,update_outstanding="No",cancel=self.docstatus == 2)
	
	def deduction_gl_entries(self,gl_entries):
		for d in self.deduct_items:
			party_type = party = ''
			if  get_account_type( d.account, self.company) in ["Receivable","Payable"]:
				party_type = "Supplier"
				party = self.supplier
			gl_entries.append(
				self.get_gl_dict({
					"account":  d.account,
					"credit": d.amount,
					"credit_in_account_currency": d.amount,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"party_type": party_type,
					"party": party,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name
				}, self.currency)
			)
	def make_item_gl_entries(self, gl_entries):
		for item in self.items:
			party_type = party = ''
			if  get_account_type( item.expense_account, self.company) in ["Receivable","Payable"]:
				party_type = "Supplier"
				party = self.supplier

			gl_entries.append(
				self.get_gl_dict({
						"account":  item.expense_account,
						"debit": flt(item.amount),
						"debit_in_account_currency": flt(item.amount),
						"against_voucher": self.name,
						"against_voucher_type": self.doctype,
						"party_type": party_type,
						"party": party,
						"cost_center": self.cost_center,
						"voucher_type":self.doctype,
						"voucher_no":self.name
				}, self.currency)
			)
	def make_tds_gl_entries(self,gl_entries):
		if flt(self.tds_amount)> 0:
			party_type = party = ''
			if  get_account_type(self.tds_account, self.company) in ["Receivable","Payable"]:
				party_type = "Supplier"
				party = self.supplier

			gl_entries.append(
					self.get_gl_dict({
							"account":  self.tds_account,
							"credit": flt(self.tds_amount),
							"credit_in_account_currency": flt(self.tds_amount),
							"against_voucher": self.name,
							"against_voucher_type": self.doctype,
							"party_type": party_type,
							"party": party,
							"cost_center": self.cost_center,
							"voucher_type":self.doctype,
							"voucher_no":self.name
					}, self.currency)
				)

	def make_supplier_gl_entry(self, gl_entries):
		if flt(self.payable_amount) > 0:
			# Did not use base_grand_total to book rounding loss gle
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_account,
					"credit": self.payable_amount,
					"credit_in_account_currency": self.payable_amount,
					"against_voucher": self.name,
					"party_type": "Supplier",
					"party": self.supplier,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name
				}, self.currency))

	# fetch logbook details
	@frappe.whitelist()
	def get_logbooks(self):
		if not self.branch:
			frappe.throw("Select Branch")
		if not self.supplier:
			frappe.throw("Select Supplier")

		if not self.from_date or not self.to_date:
			frappe.throw("From Date and To Date are mandatory")
		l = qb.DocType("Logbook")
		li = qb.DocType("Logbook Item")
		eme = qb.DocType("EME Invoice")
		emei = qb.DocType("EME Invoice Item")
		entries = (qb.from_(l)
					.inner_join(li)
					.on(l.name == li.parent)
					.select((l.name).as_("logbook"),l.posting_date, 
						l.equipment_hiring_form,
						li.expense_head,(li.hours).as_("total_hours"),
						l.equipment)
					.where((l.docstatus == 1) 
						& (l.supplier == self.supplier)
						& (l.cost_center == self.cost_center)
						& (l.posting_date >= self.from_date)
						& (l.posting_date <= self.to_date)
						& (l.paid == 0)
						& ((l.name).
								notin(qb.from_(eme).inner_join(emei).on(eme.name==emei.parent).select(emei.logbook)
									.where((eme.docstatus!=2)&(emei.logbook==l.name)&(eme.name != self.name)))
							))
					.orderby(l.posting_date,li.expense_head)
					).run(as_dict=True)
		self.set('items', [])
		if len(entries) == 0:
			frappe.msgprint("No valid logbooks found for owner {} between {} and {}.You must have pulled in other EME Invoices(including draft invoices)".format(frappe.bold(self.supplier), frappe.bold(self.from_date),frappe.bold(self.to_date)))

		total = 0
		exist_list = {}
		for d in entries:
			d.rate = self.get_rate(d.equipment_hiring_form, d.posting_date)
			d.amount = flt(d.total_hours * d.rate, 2)
			row = self.append('items', {})
			row.update(d)
		# self.calculate_totals()

def set_missing_values(source, target):
	target.run_method("set_missing_values")
	
@frappe.whitelist()
def make_arrear_payment(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def postprocess(source, target_doc):
		set_missing_values(source, target_doc)

	def update_item(obj, target, source_parent):
		target.rate = 0.00

	doclist = get_mapped_doc("EME Invoice", source_name, 	{
		"EME Invoice": {
			"doctype": "EME Invoice",
			"field_map": {
				"naming_series": "naming_series",
			},
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"EME Invoice Item": {
			"doctype": "EME Invoice Item",
			"field_map": {
					"rate": "prev_rate"
				},
			"postprocess": update_item
		}
	}, target_doc, postprocess)

	return doclist

# query permission
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		`tabEME Invoice`.owner = '{user}'
		or 
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabEME Invoice`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabEME Invoice`.branch)
	)""".format(user=user)
	