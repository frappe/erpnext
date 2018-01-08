# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, copy, os, json
from frappe.utils import flt
from erpnext.accounts.doctype.account.account import RootNotEditable

def create_sales_tax(args):
	country_wise_tax = get_country_wise_tax(args.get("country"))
	if country_wise_tax and len(country_wise_tax) > 0:
		for sales_tax, tax_data in country_wise_tax.items():
			make_tax_account_and_template(
				args.get("company_name"),
				tax_data.get('account_name'),
				tax_data.get('tax_rate'), sales_tax)

def make_tax_account_and_template(company, account_name, tax_rate, template_name=None):
	if not isinstance(account_name, (list, tuple)):
		account_name = [account_name]
		tax_rate = [tax_rate]

	accounts = []
	for i, name in enumerate(account_name):
		tax_account = make_tax_account(company, account_name[i], tax_rate[i])
		if tax_account:
			accounts.append(tax_account)

	try:
		if accounts:
			make_sales_and_purchase_tax_templates(accounts, template_name)
	except frappe.NameError:
		frappe.message_log.pop()
	except RootNotEditable:
		pass

def make_tax_account(company, account_name, tax_rate):
	tax_group = get_tax_account_group(company)
	if tax_group:
		try:
			return frappe.get_doc({
				"doctype":"Account",
				"company": company,
				"parent_account": tax_group,
				"account_name": account_name,
				"is_group": 0,
				"report_type": "Balance Sheet",
				"root_type": "Liability",
				"account_type": "Tax",
				"tax_rate": flt(tax_rate) if tax_rate else None
			}).insert(ignore_permissions=True, ignore_mandatory=True)
		except frappe.NameError:
			frappe.message_log.pop()
			abbr = frappe.db.get_value('Company', company, 'abbr')
			account = '{0} - {1}'.format(account_name, abbr)
			return frappe.get_doc('Account', account)

def make_sales_and_purchase_tax_templates(accounts, template_name=None):
	if not template_name:
		template_name = accounts[0].name

	sales_tax_template = {
		"doctype": "Sales Taxes and Charges Template",
		"title": template_name,
		"company": accounts[0].company,
		'taxes': []
	}

	for account in accounts:
		sales_tax_template['taxes'].append({
			"category": "Total",
			"charge_type": "On Net Total",
			"account_head": account.name,
			"description": "{0} @ {1}".format(account.account_name, account.tax_rate),
			"rate": account.tax_rate
		})
	# Sales
	frappe.get_doc(copy.deepcopy(sales_tax_template)).insert(ignore_permissions=True)

	# Purchase
	purchase_tax_template = copy.deepcopy(sales_tax_template)
	purchase_tax_template["doctype"] = "Purchase Taxes and Charges Template"

	doc = frappe.get_doc(purchase_tax_template)
	doc.insert(ignore_permissions=True)

def get_tax_account_group(company):
	tax_group = frappe.db.get_value("Account",
		{"account_name": "Duties and Taxes", "is_group": 1, "company": company})
	if not tax_group:
		tax_group = frappe.db.get_value("Account", {"is_group": 1, "root_type": "Liability",
				"account_type": "Tax", "company": company})

	return tax_group

def get_country_wise_tax(country):
	data = {}
	with open (os.path.join(os.path.dirname(__file__), "..", "data", "country_wise_tax.json")) as countrywise_tax:
		data = json.load(countrywise_tax).get(country)

	return data