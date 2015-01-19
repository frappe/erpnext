# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from __future__ import division
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from datetime import date, timedelta
from datetime import datetime
from erpnext.accounts.utils import get_fiscal_year
from erpnext.accounts.doctype.fixed_asset_account.depreciation_report import get_report_data

class FixedAssetYearClose(Document):
	def post_journal_entry(self):
		from erpnext.accounts.doctype.fixed_asset_account.fixed_asset_account import validate_default_accounts
		validate_default_accounts(self.company)

		financial_year_from, financial_year_to = get_fiscal_year(fiscal_year = self.fiscal_year)[1:]
		day_before_start = financial_year_from - timedelta (days=1)

		asset_query = """select * from `tabFixed Asset Account` led where is_sold=false or 
			(is_sold=true and (select count(*) from `tabFixed Asset Sale` sale where
			   sale.fixed_asset_account=led.fixed_asset_name and docstatus=1 and 
			   sale.posting_date>=%s and sale.posting_date<=%s)>0)"""

		ps = frappe.db.sql(asset_query, (financial_year_from, financial_year_to), as_dict=True)

		jv = frappe.new_doc('Journal Entry')
		jv.voucher_type = 'Journal Entry'
		jv.company = self.company
		jv.posting_date = financial_year_to
		jv.user_remark = 'Fixed Asset Closing Entry'

		total_depreciation = 0
		for assets in ps:
			fixed_asset_name = assets.fixed_asset_name

			data = get_report_data(str(financial_year_from), str(financial_year_to), \
				self.company, fixed_asset_name)

			total_depreciation_for_year = data[0][10]

			total_depreciation = total_depreciation + total_depreciation_for_year
			depr_provided_till_last_year = data[0][7]

			account = frappe.get_doc("Fixed Asset Account", fixed_asset_name)
			dep = account.append("depreciation")
			dep.fiscal_year = self.fiscal_year
			dep.total_accumulated_depreciation = total_depreciation_for_year+depr_provided_till_last_year
			account.save()

			td1 = jv.append("accounts")
			td1.account = frappe.get_doc("Company", self.company).default_depreciation_expense_account
			td1.set('debit', total_depreciation_for_year)
			td1.against_fixed_asset = fixed_asset_name
	
		td2 = jv.append("accounts")
		td2.account = frappe.get_doc("Company", self.company).default_accumulated_depreciation_account
		td2.set('credit', float(total_depreciation))

		return jv.insert()
