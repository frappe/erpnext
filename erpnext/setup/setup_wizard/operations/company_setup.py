# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, getdate
from frappe.utils.file_manager import save_file
from .default_website import website_maker
from erpnext.accounting.doctype.account.account import RootNotEditable

def create_fiscal_year_and_company(args):
	if (args.get('fy_start_date')):
		curr_fiscal_year = get_fy_details(args.get('fy_start_date'), args.get('fy_end_date'))
		frappe.get_doc({
			"doctype":"Fiscal Year",
			'year': curr_fiscal_year,
			'year_start_date': args.get('fy_start_date'),
			'year_end_date': args.get('fy_end_date'),
		}).insert()

	if (args.get('company_name')):
		frappe.get_doc({
			"doctype":"Company",
			'company_name':args.get('company_name'),
			'enable_perpetual_inventory': 1,
			'abbr':args.get('company_abbr'),
			'default_currency':args.get('currency'),
			'country': args.get('country'),
			'create_chart_of_accounts_based_on': 'Standard Template',
			'chart_of_accounts': args.get('chart_of_accounts'),
			'domain': args.get('domains')[0]
		}).insert()

def enable_shopping_cart(args):
	# Needs price_lists
	frappe.get_doc({
		"doctype": "Shopping Cart Settings",
		"enabled": 1,
		'company': args.get('company_name')	,
		'price_list': frappe.db.get_value("Price List", {"selling": 1}),
		'default_customer_group': _("Individual"),
		'quotation_series': "QTN-",
	}).insert()

def create_bank_account(args):
	if args.get("bank_account"):
		company_name = args.get('company_name')
		bank_account_group =  frappe.db.get_value("Account",
			{"account_type": "Bank", "is_group": 1, "root_type": "Asset",
				"company": company_name})
		if bank_account_group:
			bank_account = frappe.get_doc({
				"doctype": "Account",
				'account_name': args.get("bank_account"),
				'parent_account': bank_account_group,
				'is_group':0,
				'company': company_name,
				"account_type": "Bank",
			})
			try:
				return bank_account.insert()
			except RootNotEditable:
				frappe.throw(_("Bank account cannot be named as {0}").format(args.get("bank_account")))
			except frappe.DuplicateEntryError:
				# bank account same as a CoA entry
				pass

def create_email_digest():
	from frappe.utils.user import get_system_managers
	system_managers = get_system_managers(only_name=True)
	if not system_managers:
		return

	companies = frappe.db.sql_list("select name FROM `tabCompany`")
	for company in companies:
		if not frappe.db.exists("Email Digest", "Default Weekly Digest - " + company):
			edigest = frappe.get_doc({
				"doctype": "Email Digest",
				"name": "Default Weekly Digest - " + company,
				"company": company,
				"frequency": "Weekly",
				"recipient_list": "\n".join(system_managers)
			})

			for df in edigest.meta.get("fields", {"fieldtype": "Check"}):
				if df.fieldname != "scheduler_errors":
					edigest.set(df.fieldname, 1)

			edigest.insert()

	# scheduler errors digest
	if companies:
		edigest = frappe.new_doc("Email Digest")
		edigest.update({
			"name": "Scheduler Errors",
			"company": companies[0],
			"frequency": "Daily",
			"recipient_list": "\n".join(system_managers),
			"scheduler_errors": 1,
			"enabled": 1
		})
		edigest.insert()

def create_logo(args):
	if args.get("attach_logo"):
		attach_logo = args.get("attach_logo").split(",")
		if len(attach_logo)==3:
			filename, filetype, content = attach_logo
			fileurl = save_file(filename, content, "Website Settings", "Website Settings",
				decode=True).file_url
			frappe.db.set_value("Website Settings", "Website Settings", "brand_html",
				"<img src='{0}' style='max-width: 40px; max-height: 25px;'> {1}".format(fileurl, args.get("company_name")	))

def create_website(args):
	website_maker(args)

def get_fy_details(fy_start_date, fy_end_date):
	start_year = getdate(fy_start_date).year
	if start_year == getdate(fy_end_date).year:
		fy = cstr(start_year)
	else:
		fy = cstr(start_year) + '-' + cstr(start_year + 1)
	return fy