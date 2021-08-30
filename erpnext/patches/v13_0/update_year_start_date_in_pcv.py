# Copyright (c) 2021, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	pcvs = frappe.db.get_all(
		doctype='Period Closing Voucher',
		filters={'docstatus': 1},
		fields=['name', 'posting_date', 'fiscal_year', 'company']
	)
	if pcvs:
		from erpnext.accounts.utils import get_fiscal_year
		frappe.reload_doc('accounts', 'doctype', 'period_closing_voucher')

		for pcv in pcvs:
			year_start_date = get_fiscal_year(pcv.posting_date, pcv.fiscal_year, company=pcv.company)[1]
			frappe.db.set_value('Period Closing Voucher', pcv.name, 'year_start_date', year_start_date)
