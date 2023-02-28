# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from frappe.utils import money_in_words, cstr, flt, fmt_money, formatdate, getdate, nowdate, cint, get_link_to_form, now_datetime, get_datetime
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from frappe import _, qb, throw, bold
from erpnext.accounts.party import get_party_account
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import (
	get_round_off_account_and_cost_center,
	make_gl_entries,
	make_reverse_gl_entries,
	merge_similar_entries,
)

class POLExpense(AccountsController):
	def validate(self):
		if flt(self.is_opening) == 0:
			validate_workflow_states(self)
		self.posting_date = self.entry_date
		self.validate_amount()
		self.calculate_pol()
		if cint(self.use_common_fuelbook) == 1:
			self.credit_account = get_party_account(self.party_type, self.party, self.company, is_advance = True)
		else:
			self.credit_account = get_party_account(self.party_type, self.party, self.company)

		if flt(self.is_opening) == 0 and self.workflow_state != "Approved" :
			notify_workflow_states(self)
		self.set_status()

	
	def on_submit(self): 
		if cint(self.use_common_fuelbook) == 0:
			self.make_gl_entries()
		self.post_journal_entry()
		if flt(self.is_opening) == 0:
			notify_workflow_states(self)

	def before_cancel(self):
		if self.is_opening:
			return
		if frappe.db.exists("Journal Entry",self.journal_entry):
			doc = frappe.get_doc("Journal Entry", self.journal_entry)
			if doc.docstatus != 2:
				frappe.throw("Journal Entry exists for this transaction {}".format(frappe.get_desk_link("Journal Entry",self.journal_entry)))
				
	def on_cancel(self):
		if cint(self.use_common_fuelbook) == 0:
			self.make_gl_entries()

	def make_gl_entries(self):
		if self.is_opening:
			return

		gl_entries = []
		self.make_supplier_gl_entry(gl_entries)
		self.make_expense_gl_entry(gl_entries)
		gl_entries = merge_similar_entries(gl_entries)
		make_gl_entries(gl_entries,update_outstanding="No",cancel=self.docstatus == 2)

	def make_supplier_gl_entry(self, gl_entries):
		if flt(self.amount) > 0:
			# Did not use base_grand_total to book rounding loss gle
			gl_entries.append(
				self.get_gl_dict({
					"account": self.credit_account,
					"credit": self.amount,
					"credit_in_account_currency": self.amount,
					"against_voucher": self.name,
					"party_type": self.party_type,
					"party": self.party,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"voucher_type":self.doctype,
					"voucher_no":self.name,
					"posting_date":self.entry_date
				}, self.currency))
	def make_expense_gl_entry(self, gl_entries):
		if flt(self.amount) > 0:
			expense_account = frappe.db.get_value("Equipment Category", self.equipment_category,'pol_expense_account')
			gl_entries.append(
					self.get_gl_dict({
						"account": expense_account,
						"debit": self.amount,
						"debit_in_account_currency": self.amount,
						"against_voucher": self.name,
						"party_type": self.party_type,
						"party": self.party,
						"against_voucher_type": self.doctype,
						"cost_center": self.cost_center,
						"voucher_type":self.doctype,
						"voucher_no":self.name,
						"posting_date":self.entry_date
					}, self.currency))

	def calculate_pol(self):
		if self.opening_pol_tank_balance and self.pol_issue_during_the_period and self.closing_pol_tank_balance :
			self.total_petrol_diesel_consumed =  flt(self.opening_pol_tank_balance) + flt(self.pol_issue_during_the_period) - flt(self.closing_pol_tank_balance)
		
		if self.previous_km_reading and self.present_km_reading :
			self.total_km_reading = flt(self.present_km_reading) - flt(self.previous_km_reading)
		
		if self.total_km_reading and self.total_petrol_diesel_consumed:
			if self.uom == "KM":
				self.average_km_reading = flt(self.total_km_reading) / flt(self.total_petrol_diesel_consumed)
			else: 
				self.average_km_reading = flt(self.total_petrol_diesel_consumed) / flt(self.total_km_reading)
			
	def validate_km_diff(self):
		if flt(self.previous_km_reading) >= flt(self.present_km_reading):
			throw("Previous reading({}) cannot be greater than current km {}".format(bold(self.previous_km_reading),bold(self.present_km_reading)))
			
	def calculate_km_diff(self):
		pol_exp = qb.DocType("POL Expense")
		if not self.uom:
			self.uom = frappe.db.get_value("Equipment", self.equipment,"reading_uom")
		pol_rev = qb.DocType("POL Receive")
		previous_km_reading = (
						qb.from_(pol_rev)
						.select(pol_rev.cur_km_reading)
						.where((pol_rev.equipment == self.equipment) & (pol_rev.docstatus==1) & (pol_rev.uom == self.uom) & (pol_rev.posting_date<self.from_date))
						.orderby( pol_rev.posting_date,order=qb.desc)
						.orderby( pol_rev.posting_time,order=qb.desc)
						.limit(1)
						.run()
						)
		pv_km = 0
		previous_km_reading_pol_issue = frappe.db.sql('''
				select cur_km_reading
				from `tabPOL Issue` p inner join `tabPOL Issue Items` pi on p.name = pi.parent	
				where p.docstatus = 1 and pi.equipment = '{}'
				and pi.uom = '{}' and p.posting_date < '{}'
				order by p.posting_date desc, p.posting_time desc
				limit 1
			'''.format(self.equipment, self.uom, self.from_date))

		if not previous_km_reading and previous_km_reading_pol_issue:
			previous_km_reading = previous_km_reading_pol_issue
		elif previous_km_reading and previous_km_reading_pol_issue:
			if flt(previous_km_reading[0][0]) < previous_km_reading_pol_issue[0][0]:
				previous_km_reading = previous_km_reading_pol_issue

		if not previous_km_reading:
			pv_km = frappe.db.get_value("Equipment",self.equipment,"initial_km_reading")
		else:
			pv_km = previous_km_reading[0][0]
		
		closing_pol_tank_balance = (
								qb.from_(pol_exp)
								.select(pol_exp.closing_pol_tank_balance)
								.where((pol_exp.equipment == self.equipment) & (pol_exp.docstatus==1) & (pol_exp.uom == self.uom) & (pol_exp.name != self.name) & (pol_exp.entry_date< self.from_date))
								.orderby( pol_exp.entry_date,order=qb.desc)
								.orderby( pol_exp.name, order=qb.desc)
								.limit(1)
								.run()
								)
		if closing_pol_tank_balance[0][0]:
			self.opening_pol_tank_balance = closing_pol_tank_balance[0][0]
		self.previous_km_reading = pv_km
		
	def post_journal_entry(self):
		if self.is_opening:
			return
		if not self.amount:
			frappe.throw(_("Amount should be greater than zero"))
			
		default_ba = get_default_ba()
		
		credit_account = self.credit_account
		expense_account = frappe.db.get_value("Branch",self.fuelbook_branch,"expense_bank_account")
		if not expense_account:
			expense_account = frappe.db.get_value("Company",self.company,"default_bank_account")
		if not credit_account:
			frappe.throw("Credit Account is mandatory")
		
		r = []
		if self.cheque_no:
			if self.cheque_date:
				r.append(_('Reference #{0} dated {1}').format(self.cheque_no, formatdate(self.cheque_date)))
			else:
				msgprint(_("Please enter Cheque Date date"), raise_exception=frappe.MandatoryError)
		
		if self.user_remark:
			r.append(_("Note: {0}").format(self.user_remark))

		remarks = ("").join(r) #User Remarks is not mandatory
		
		# Posting Journal Entry
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Payment Voucher",
			"title": "POL Expense - " + self.equipment if cint(self.use_common_fuelbook) == 0 else self.fuel_book,
			"user_remark": "Note: " + "POL Expense - " + self.equipment if cint(self.use_common_fuelbook) == 0 else self.fuel_book,
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.amount),
			"branch": self.fuelbook_branch,
		})
		je.append("accounts",{
			"account": self.credit_account,
			"debit_in_account_currency": flt(self.amount,2),
			"cost_center": frappe.db.get_value('Branch',self.fuelbook_branch,'cost_center'),
			"party_check": 0,
			"party_type": "Supplier",
			"party": self.party,
			"reference_type": "POL Expense",
			"reference_name": self.name,
			"business_activity": default_ba
		})
		je.append("accounts",{
			"account": expense_account,
			"credit_in_account_currency": flt(self.amount,2),
			"cost_center": frappe.db.get_value('Branch',self.fuelbook_branch,'cost_center'),
			"business_activity": default_ba
		})

		je.insert()
		#Set a reference to the claim journal entry
		self.db_set("journal_entry",je.name)
		frappe.msgprint(_('Journal Entry <a href="#Form/Journal Entry/{0}">{0}</a> posted to accounts').format(je.name))
	@frappe.whitelist()
	def get_pol_received(self):
		if self.is_opening:
			return
		pol_rev = qb.DocType("POL Receive")
		self.set("pol_received_item",[])
		total_qty = total_bill_amt = 0
		for d in (qb.from_(pol_rev).select(pol_rev.name.as_("pol_receive_ref"),
						pol_rev.km_difference.as_("km_hr_difference"),
						pol_rev.cur_km_reading.as_("current_km_hr_reading"),
						pol_rev.mileage, pol_rev.rate, pol_rev.total_amount.as_("bill_amount"), pol_rev.qty)
						.where((pol_rev.docstatus == 1) & ( pol_rev.equipment == self.equipment)
							& (pol_rev.posting_date >= self.from_date)
							& ( pol_rev.posting_date <= self.to_date))).run(as_dict=True):
			self.append("pol_received_item",d)
			total_qty += flt(d.qty)
			total_bill_amt += flt(d.bill_amount,2)
		self.total_qty_received = total_qty
		self.total_bill_amount = total_bill_amt
		self.pol_issue_during_the_period = total_qty
		if not self.pol_received_item:
			frappe.msgprint("No pol receive found within Date {} to {}".format(self.from_date, self.to_date))
		self.calculate_km_diff()
	def validate_amount(self):
		if cint(self.use_common_fuelbook) == 0 and flt(self.amount) > flt(self.expense_limit):
			frappe.throw("Amount cannot be greater than expense limit")
		if cint(self.is_opening) == 0 :
			self.outstanding_amount = self.amount

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			self.payment_status = "Draft"
			return

		outstanding_amount = flt(self.outstanding_amount,2)
		if not status:
			if self.docstatus == 2:
				self.payment_status = "Cancelled"
			elif self.docstatus == 1:
				if cint(self.is_opening) == 1 :
					self.payment_status = "Paid"
				elif outstanding_amount > 0 and flt(self.amount) > outstanding_amount:
					self.payment_status = "Partly Paid"
				elif outstanding_amount > 0 :
					self.payment_status = "Unpaid"
				elif outstanding_amount <= 0:
					self.payment_status = "Paid"
				else:
					self.payment_status = "Submitted"
			else:
				self.payment_status = "Draft"

		if update:
			self.db_set("payment_status", self.payment_status, update_modified=update_modified)

	@frappe.whitelist()
	def pull_previous_expense(self):
		pol_exp = qb.DocType(self.doctype)
		total_amount = 0
		if cint(self.use_common_fuelbook) == 1:
			if not self.fuel_book:
				frappe.throw("Fuel book is missing")
			if flt(self.expense_limit) <= 0 :
				self.expense_limit = frappe.db.get_value("Fuelbook", self.fuel_book,"expense_limit")
			for d in (qb.from_(pol_exp).select(pol_exp.name.as_("reference"), pol_exp.amount,pol_exp.adjusted_amount, pol_exp.balance_amount)
						.where( (pol_exp.docstatus == 1 ) & ( pol_exp.balance_amount > 0 ) 
							& (pol_exp.name != self.name) & (pol_exp.fuel_book == self.fuel_book))
						).run(as_dict= True):
				total_amount += flt(d.balance_amount)
				self.append("items", d)
				self.previous_balance_amount = total_amount
		else:
			if not self.equipment or not self.fuel_book:
				frappe.throw("Equipment or Fuel book is missing")
			self.set('items',[])

			if flt(self.expense_limit) <= 0 and self.equipment_type:
				self.expense_limit = frappe.db.get_value("Equipment Type",self.equipment_type,"pol_expense_limit")
				
			for d in (qb.from_(pol_exp).select(pol_exp.name.as_("reference"), pol_exp.amount,pol_exp.adjusted_amount, pol_exp.balance_amount)
							.where((pol_exp.equipment == self.equipment) & (pol_exp.docstatus == 1 ) & ( pol_exp.balance_amount > 0 ) 
								& (pol_exp.name != self.name) & (pol_exp.fuel_book == self.fuel_book))
							).run(as_dict= True):
				total_amount += flt(d.balance_amount)
				self.append("items", d)
			self.previous_balance_amount = total_amount

		if flt(self.expense_limit) > 0 :
			self.amount = flt(self.expense_limit) - flt(self.previous_balance_amount)
			self.balance_amount = self.amount

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		`tabPOL Expense`.owner = '{user}'
		or
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabPOL Expense`.fuelbook_branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabPOL Expense`.fuelbook_branch)
		or
		(`tabPOL Expense`.approver = '{user}' and `tabPOL Expense`.workflow_state not in  ('Draft','Approved','Rejected','Cancelled'))
	)""".format(user=user)