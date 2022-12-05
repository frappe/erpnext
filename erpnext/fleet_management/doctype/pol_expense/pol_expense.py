# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from frappe.utils import money_in_words, flt
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from frappe import _, qb, throw, bold

class POLExpense(Document):
	def validate(self):
		validate_workflow_states(self)

		self.validate_amount()
		self.calculate_pol()
		if not self.credit_account:
			self.credit_account = frappe.db.get_value("Company",self.company,"default_bank_account")
		if self.workflow_state != "Approved":
			notify_workflow_states(self)

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
	def on_submit(self):
		self.post_journal_entry()
		notify_workflow_states(self)
	
	def calculate_km_diff(self):
		pol_exp = qb.DocType("POL Expense")
		if not self.uom:
			self.uom = frappe.db.get_value("Equipment", self.equipment,"reading_uom")
		
		previous_km_reading = (
								qb.from_(pol_exp)
								.select(pol_exp.present_km_reading, pol_exp.name)
								.where((pol_exp.equipment == self.equipment) & (pol_exp.docstatus==1) & (pol_exp.uom == self.uom) & (pol_exp.name != self.name))
								.orderby( pol_exp.entry_date,order=qb.desc)
								.orderby( pol_exp.name, order=qb.desc)
								.limit(1)
								.run()
								)
		pv_km = 0
		if not previous_km_reading:
			pv_km = frappe.db.get_value("Equipment",self.equipment,"initial_km_reading")
		else:
			pv_km = previous_km_reading[0][0]
		self.previous_km_reading = pv_km
		
	def post_journal_entry(self):
		if flt(self.is_opening) == 1:
			return
		if not self.amount:
			frappe.throw(_("Amount should be greater than zero"))
			
		self.posting_date = self.entry_date
		default_ba = get_default_ba()

		credit_account = self.credit_account
		advance_account = frappe.db.get_value("Company", self.company,'pol_advance_account')
			
		if not credit_account:
			frappe.throw("Expense Account is mandatory")
		if not advance_account:
			frappe.throw("Setup POL Advance Account in company")

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
			"title": "POL Expense - " + self.equipment,
			"user_remark": "Note: " + "POL Expense - " + self.equipment,
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.amount),
			"branch": self.fuelbook_branch,
		})
		je.append("accounts",{
			"account": advance_account,
			"debit_in_account_currency": self.amount,
			"cost_center": frappe.db.get_value('Branch',self.fuelbook_branch,'cost_center'),
			"party_check": 0,
			"party_type": "Supplier",
			"party": self.party,
			"reference_type": "POL Expense",
			"reference_name": self.name,
			"business_activity": default_ba
		})
		je.append("accounts",{
			"account": credit_account,
			"credit_in_account_currency": self.amount,
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
	def validate_amount(self):
		if flt(self.amount) > flt(self.expense_limit):
			frappe.throw("Amount cannot be greater than expense limit")
	@frappe.whitelist()
	def pull_previous_expense(self):
		pol_exp = qb.DocType(self.doctype)
		self.set('items',[])

		if flt(self.expense_limit) <= 0 and self.equipment_type:
			self.expense_limit = frappe.db.get_value("Equipment Type",self.equipment_type,"pol_expense_limit")
			
		total_amount = 0
		for d in (qb.from_(pol_exp).select(pol_exp.name.as_("reference"), pol_exp.amount,pol_exp.adjusted_amount, pol_exp.balance_amount)
						.where((pol_exp.equipment == self.equipment) & (pol_exp.docstatus == 1 ) & ( pol_exp.balance_amount > 0 ) & (pol_exp.name != self.name))
						).run(as_dict= True):
			total_amount += flt(d.balance_amount)
			self.append("items", d)
		self.previous_balance_amount = total_amount
		if flt(self.expense_limit) > 0 :
			self.amount = flt(self.expense_limit) - flt(self.previous_balance_amount)
			self.balance_amount = self.amount
		self.calculate_km_diff()

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabPOL Expense`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` as e
			where e.user_id = `tabPOL Expense`.owner
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabPOL Expense`.branch)
		or
		(`tabPOL Expense`.approver = '{user}' and `tabPOL Expense`.workflow_state not in  ('Draft','Approved','Rejected','Cancelled'))
	)""".format(user=user)