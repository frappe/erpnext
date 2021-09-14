# Copyright (c) 2021, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.utils import get_fiscal_year


def execute():
	frappe.reload_doc('accounts', 'doctype', 'Tax Withholding Rate')

	if frappe.db.has_column('Tax Withholding Rate', 'fiscal_year'):
		tds_category_rates = frappe.get_all('Tax Withholding Rate', fields=['name', 'fiscal_year'])

		fiscal_year_map = {}
		for rate in tds_category_rates:
			if not fiscal_year_map.get(rate.fiscal_year):
				fiscal_year_map[rate.fiscal_year] = get_fiscal_year(fiscal_year=rate.fiscal_year)

			from_date = fiscal_year_map.get(rate.fiscal_year)[1]
			to_date = fiscal_year_map.get(rate.fiscal_year)[2]

			frappe.db.set_value('Tax Withholding Rate', rate.name, {
				'from_date': from_date,
				'to_date': to_date
			})