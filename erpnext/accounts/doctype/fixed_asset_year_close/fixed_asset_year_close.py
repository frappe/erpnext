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
		finyrfrom, finyrto = get_fiscal_year(fiscal_year = self.fiscal_year)[1:]
		day_before_start = finyrfrom - timedelta (days=1)
		ps = frappe.db.sql("""select * from `tabFixed Asset Account` led where is_sold=false or (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and docstatus=1 and sale.posting_date>=%s and sale.posting_date<=%s)>0)""", (finyrfrom, finyrto), as_dict=True)

		jv = frappe.new_doc('Journal Entry')
		jv.voucher_type = 'Journal Entry'
		jv.company = self.company
		jv.posting_date = finyrto
		jv.user_remark = 'Fixed Asset Closing Entry'

		global total_depr
		total_depr = 0
		for assets in ps:
			fixed_asset_name = assets.fixed_asset_name
			fiscal_doc = frappe.get_doc("Fiscal Year", self.fiscal_year)
			data = get_report_data(fiscal_doc.year_start_date, fiscal_doc.year_end_date, self.company, fixed_asset_name)
			total_depreciation_for_year = data[0][10]
			total_depr = total_depr + total_depreciation_for_year
			deprtilllastyr = data[0][7]

			account = frappe.get_doc("Fixed Asset Account", fixed_asset_name)
			dep = account.append("depreciation")
			dep.fiscal_year = self.fiscal_year
			dep.total_accumulated_depreciation = total_depreciation_for_year+deprtilllastyr
			account.save()

			td1 = jv.append("accounts")
			td1.account = frappe.get_doc("Company", self.company).default_depreciation_expense_account
			td1.set('debit', total_depreciation_for_year)
			td1.against_fixed_asset = fixed_asset_name
	
		td2 = jv.append("accounts")
		td2.account = frappe.get_doc("Company", self.company).default_accumulated_depreciation_account
		td2.set('credit', float(total_depr))

		return jv.insert()
