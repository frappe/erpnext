# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, money_in_words
from erpnext.accounts.doctype.business_activity.business_activity import get_default_ba
from erpnext.accounts.party import get_party_account

class InsuranceandRegistration(Document):
	def validate(self):
		self.prevent_row_remove()

	def prevent_row_remove(self):
		unsafed_record = [d.name for d in self.insurance_item]
		if flt(len(unsafed_record)) <= 0:
			unsafed_record = ["Dummy"]
		for d in frappe.db.get_list('Insurance Details', filters={'parent': self.name },
							fields=['name', 'journal_entry','idx'],
						):
			if d.name not in unsafed_record and d.journal_entry:
				je = frappe.get_doc("Journal Entry",d.journal_entry)
				if je.docstatus != 2:
					frappe.throw("You cannot delete row {} from Insurance Detail as \
						accounting entry is booked".format(frappe.bold(d.idx)))
		# unsafed_record = [d.name for d in self.items]
		# if flt(len(unsafed_record)) <= 0:
		# 	unsafed_record = ["Dummy"]
		# for d in frappe.db.get_list('Bluebook Fitness and Emission Details', filters={'parent': self.name },
		# 					fields=['name', 'journal_entry','idx'],
		# 				):
		# 	if d.name not in unsafed_record and d.journal_entry:
		# 		je = frappe.get_doc("Journal Entry",d.journal_entry)
		# 		if je.docstatus != 2:
		# 			frappe.throw("You cannot delete row {} from Bluebook Fitness \
		# 					and Emission Details as accounting entry is booked".format(frappe.bold(d.idx)))
		
	@frappe.whitelist()
	def create_je(self, args):
		if args.journal_entry and frappe.db.exists("Journal Entry",args.journal_entry):
			doc = frappe.get_doc("Journal Entry", args.journal_entry)
			if doc.docstatus != 2:
				frappe.throw("Journal Entry exists for this transaction {}".format(frappe.get_desk_link("Journal Entry",args.journal_entry)))
			
		if flt(args.total_amount) <= 0:
			frappe.throw(_("Amount should be greater than zero"))
			
		default_bank_account = frappe.db.get_value("Branch", self.branch,'expense_bank_account')

		# Posting Journal Entry
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		if args.get("type") == "Insurance":
			debit_account 	= get_party_account("Supplier",args.get("party"),self.company, is_advance = True)
			posting_date = args.get("insured_date")
		else:
			posting_date = args.get("receipt_date")
			debit_account 	= frappe.db.get_value("Company", self.company,'repair_and_service_expense_account')
		if not debit_account:
			frappe.throw("Setup Fleet Expense Account in company")
		if not default_bank_account:
			frappe.throw("Setup Default Bank Account in company")
		posting_date
		je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Payment Voucher",
			"title": args.type + " Charge - " + self.equipment,
			"user_remark": "Note: " + args.type + " Charge paid against Vehicle " + self.equipment,
			"posting_date": posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(args.total_amount),
			"branch": self.branch,
		})
		je.append("accounts",{
			"account": debit_account,
			"debit_in_account_currency": args.total_amount,
			"cost_center": frappe.db.get_value('Branch',self.branch,'cost_center'),
			"party_check": 0,
			"party_type": "Supplier",
			"party": args.party,
			"reference_type": self.doctype,
			"reference_name": self.name
			})
		je.append("accounts",{
			"account": default_bank_account,
			"credit_in_account_currency": args.total_amount,
			"cost_center": frappe.db.get_value('Branch',self.branch,'cost_center')
		})
		je.insert()
		frappe.msgprint(_('Journal Entry {0} posted to accounts').format(frappe.get_desk_link("Journal Entry",je.name)))
		return je.name
		#Set a reference to the claim journal entry
