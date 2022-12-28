# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from frappe.utils import flt
from erpnext.accounts.party import get_party_account

class RepairAndServiceInvoice(AccountsController):
	def validate(self):
		check_future_date(self.posting_date)
		self.calculate_total()
		self.set_status()
		if not self.credit_account:
			self.credit_account = get_party_account(self.party_type,self.party,self.company)
	def on_submit(self):
		self.make_gl_entry()
		self.update_repair_and_service()
	def on_cancel(self):
		self.make_gl_entry()
		self.update_repair_and_service()

	def update_repair_and_service(self):
		if not self.repair_and_services:
			return
		value = 1
		if self.docstatus == 2:
			value = 0
		doc = frappe.get_doc("Repair And Services", self.repair_and_services)
		doc.db_set("paid", value)
	
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
				if outstanding_amount > 0 and self.total_amount > outstanding_amount:
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

	def calculate_total(self):
		self.total_amount = self.grand_total = self.outstanding_amount = 0
		for a in self.items:
			a.charge_amount = flt(flt(a.rate) * flt(a.qty),2)
			self.total_amount += flt(a.charge_amount,2)
			self.grand_total += flt(a.charge_amount,2)
			self.outstanding_amount += flt(a.charge_amount,2)
	def make_gl_entry(self):
		from erpnext.accounts.general_ledger import make_gl_entries
		gl_entries = []
		ba = get_default_ba()
		expense_account = frappe.db.get_value("Equipment Category", self.equipment_category, "r_m_expense_account")
		if not expense_account:
			expense_account = frappe.db.get_value("Company", self.company, "repair_and_service_expense_account")
		
		if not expense_account:
			frappe.throw(
				"Setup Repair And Service Expense Account in Equipment Category {}".format(self.equipment_category))

		gl_entries.append(
			self.get_gl_dict({
				"account": expense_account,
				"debit": self.total_amount,
				"debit_in_account_currency": self.total_amount,
				"voucher_no": self.name,
				"voucher_type": self.doctype,
				"cost_center": self.cost_center,
				"business_activity": ba,
			}, self.currency)
		)
		gl_entries.append(
			self.get_gl_dict({
				"account": self.credit_account,
				"party_type": self.party_type,
				"party": self.party,
				"credit": self.total_amount,
				"credit_in_account_currency": self.total_amount,
				"business_activity": ba,
				"cost_center": self.cost_center,
				"voucher_no":self.name,
				"voucher_type":self.doctype,
				"against_voucher":self.name,
				"against_voucher_type":self.doctype
			}, self.currency)
		)
		make_gl_entries(gl_entries, update_outstanding="No", cancel=(self.docstatus == 2), merge_entries=False)
# permission query
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		`tabRepair And Services Invoice`.owner = '{user}'
		or
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabRepair And Services Invoice`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabRepair And Services Invoice`.branch)
	)""".format(user=user)