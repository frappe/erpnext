# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class FixedAssetAccount(Document):
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
   print val
   return val

