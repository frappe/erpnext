# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class FixedAssetAccount(Document):
	def validate(self):
		for totaldepr in self.depreciation:
			count = 0
			for totaldepr_entries in self.depreciation:
				if totaldepr.fiscal_year == totaldepr_entries.fiscal_year:
					count = count + 1;
					if count >= 2:
						frappe.throw("Fiscal Yr Duplicated in Accumulated Depreciation. Pls Check")

	def post_journal_entry(self):
		jv = frappe.new_doc('Journal Entry')
		jv.voucher_type = 'Journal Entry'
		jv.company = self.company
		jv.posting_date = self.purchase_date
		jv.user_remark = 'Fixed Asset Purchase'


		td1 = jv.append("accounts");	
		from erpnext.accounts.party import get_party_account
		td1.account = get_party_account(self.company, self.purchased_from, 'Supplier')
		td1.party = self.purchased_from
		td1.party_type = 'Supplier'
		td1.set("debit", self.gross_purchase_value)

		td2 = jv.append("accounts")
		td2.account = self.fixed_asset_account
		td2.set('credit', self.gross_purchase_value)

		return jv.insert()		

@frappe.whitelist()
def get_purchase_cost(account):
   val = frappe.get_doc("Fixed Asset Account", account).gross_purchase_value
   return val

@frappe.whitelist()
def validate_default_accounts(company):
	comp = frappe.get_doc("Company", company)
	if not comp.default_depreciation_expense_account:
		frappe.throw("Pls Set Company Default Depreciation Expense Account")
	if not comp.default_accumulated_depreciation_account:
		frappe.throw("Pls Set Company Default Accumulated Depreciation Account")


