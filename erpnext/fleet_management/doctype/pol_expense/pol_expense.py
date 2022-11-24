# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from frappe.utils import money_in_words

class POLExpense(Document):
	def on_submit(self):
		self.post_journal_entry()
	def post_journal_entry(self):
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

		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Receipt Voucher" if self.payment_type == "Receive" else "Bank Payment Voucher",
			"title": "POL Expense - " + self.equipment,
			"user_remark": "Note: " + "POL Expense - " + self.equipment,
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(self.amount),
			"branch": self.fuelbook_branch,
		})

		je.append("accounts",{
			"account": credit_account,
			"credit_in_account_currency": self.amount,
			"cost_center": frappe.db.get_value('Branch',self.fuelbook_branch,'cost_center'),
			"reference_type": "POL Expense",
			"reference_name": self.name,
			"business_activity": default_ba
		})

		je.append("accounts",{
			"account": advance_account,
			"debit_in_account_currency": self.amount,
			"cost_center": frappe.db.get_value('Branch',self.fuelbook_branch,'cost_center'),
			"party_check": 0,
			"party_type": "Supplier",
			"party": self.party,
			"business_activity": default_ba
		})
		je.insert()
		#Set a reference to the claim journal entry
		self.db_set("journal_entry",je.name)
		frappe.msgprint(_('Journal Entry <a href="#Form/Journal Entry/{0}">{0}</a> posted to accounts').format(je.name))

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
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabPOL Expense`.branch)
	)""".format(user=user)