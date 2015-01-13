# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class FixedAssetSale(Document):
	def post_journal_entry(self):
		validate_account = frappe.db.get_value("Account", {"account_name": "Accumulated Depreciation"})
		if not validate_account:
			frappe.throw("""Account 'Accumulated Depreciation' Not Found""")
		jv = frappe.new_doc('Journal Entry')
		jv.voucher_type = 'Journal Entry'
		jv.company = self.company
		jv.posting_date = self.posting_date
		jv.user_remark = 'Fixed Asset Sale'


		td1 = jv.append("accounts");		
		td1.account = frappe.db.get_value("Fixed Asset Account", self.fixed_asset_account,"fixed_asset_account")
		td1.set("credit", float(self.asset_purchase_cost))

		td2 = jv.append("accounts")
		from erpnext.accounts.party import get_party_account
		td2.account = get_party_account(self.company, self.sold_to, 'Customer')
		td2.party = self.sold_to
		td2.party_type = 'Customer'

		td2.set('debit', float(self.sales_amount))

		td5 = jv.append("accounts")
		# td5.account = frappe.db.get_value("Fixed Asset Account", self.fixed_asset_account,"fixed_asset_account")
		td5.account = frappe.db.get_value("Account", {"account_name": "Accumulated Depreciation"})
		td5.set('debit', float(self.accumulated_depreciation))

		if self.profit_or_loss == "Loss":
			td3 = jv.append("accounts")
			td3.account = self.booking_account
			td3.set('debit', float(self.difference))
		elif self.profit_or_loss == "Profit":
			td4 = jv.append("accounts")
			td4.account = self.booking_account
			td4.set('credit', float(self.difference))


		return jv.insert()

	def validate(self):
		fa = frappe.get_doc("Fixed Asset Account", self.fixed_asset_account)
		if fa.is_sold:
			frappe.throw("Asset Already Sold Cannot Continue")

	def on_submit(self):
		fa = frappe.get_doc("Fixed Asset Account", self.fixed_asset_account)
		fa.is_sold = True
		fa.save()

	def on_cancel(self):
		fa = frappe.get_doc("Fixed Asset Account", self.fixed_asset_account)
		fa.is_sold = False
		fa.save()		

