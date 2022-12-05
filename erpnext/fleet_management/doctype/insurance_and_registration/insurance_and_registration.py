# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, money_in_words
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba

class InsuranceandRegistration(Document):
	pass

	@frappe.whitelist()
	def create_je(self, args):
		if flt(args.amount) <= 0:
			frappe.throw(_("Amount should be greater than zero"))
			
		default_ba = get_default_ba()

		debit_account 	= frappe.db.get_value("Company", self.company,'repair_and_service_expense_account')
		default_bank_account = frappe.db.get_value("Company", self.company,'default_bank_account')
			
		if not debit_account:
			frappe.throw("Setup Fleet Expense Account in company")
		if not default_bank_account:
			frappe.throw("Setup Default Bank Account in company")

		# Posting Journal Entry
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Payment Voucher",
			"title": args.type + " Charge - " + self.equipment,
			"user_remark": "Note: " + args.type + " Charge paid against Vehicle " + self.equipment,
			"posting_date": args.receipt_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(args.total_amount),
			"branch": self.branch,
		})

		je.append("accounts",{
			"account": default_bank_account,
			"credit_in_account_currency": args.total_amount,
			"cost_center": frappe.db.get_value('Branch',self.branch,'cost_center'),
			"reference_type": "Insurance and Registration",
			"reference_name": self.name,
			"business_activity": default_ba
		})

		je.append("accounts",{
			"account": debit_account,
			"debit_in_account_currency": args.total_amount,
			"cost_center": frappe.db.get_value('Branch',self.branch,'cost_center'),
			"party_check": 0,
			"party_type": "Supplier",
			"party": args.paid_to,
			"business_activity": default_ba
		})
		je.insert()
		frappe.msgprint(_('Journal Entry {0} posted to accounts').format(je.name))
		return je.name
		#Set a reference to the claim journal entry
