# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe.utils import flt
from erpnext.accounts.utils import get_balance_on
from erpnext.accounts.report.financial_statements import sort_root_accounts

@frappe.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	return [d.name for d in frappe.get_list("Organization", fields=["name"],
		order_by="name")]

@frappe.whitelist()
def get_children():
	args = frappe.local.form_dict
	ctype, organization = args['ctype'], args['comp']	
	fieldname = frappe.db.escape(ctype.lower().replace(' ','_'))
	doctype = frappe.db.escape(ctype)
	
	# root
	if args['parent'] in ("Accounts", "Cost Centers"):
		fields = ", root_type, report_type, account_currency" if ctype=="Account" else ""
		acc = frappe.db.sql(""" select
			name as value, is_group as expandable {fields}
			from `tab{doctype}`
			where ifnull(`parent_{fieldname}`,'') = ''
			and `organization` = %s	and docstatus<2
			order by name""".format(fields=fields, fieldname = fieldname, doctype=doctype),
				organization, as_dict=1)

		if args["parent"]=="Accounts":
			sort_root_accounts(acc)
	else:
		# other
		fields = ", account_currency" if ctype=="Account" else ""
		acc = frappe.db.sql("""select
			name as value, is_group as expandable, parent_{fieldname} as parent {fields}
	 		from `tab{doctype}`
			where ifnull(`parent_{fieldname}`,'') = %s
			and docstatus<2
			order by name""".format(fields=fields, fieldname=fieldname, doctype=doctype),
				args['parent'], as_dict=1)

	if ctype == 'Account':
		organization_currency = frappe.db.get_value("Organization", organization, "default_currency")
		for each in acc:
			each["organization_currency"] = organization_currency
			each["balance"] = flt(get_balance_on(each.get("value"), in_account_currency=False))
			if each.account_currency != organization_currency:
				each["balance_in_account_currency"] = flt(get_balance_on(each.get("value")))

	return acc
