# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, getdate
from frappe.utils.file_manager import save_file
from .default_website import website_maker
from erpnext.accounts.doctype.account.account import RootNotEditable

def get_company_records(args):
	records = []

	# Price lists
	for pl_type, pl_name in (("Selling", _("Standard Selling")), ("Buying", _("Standard Buying"))):
		records.append({
			"doctype": "Price List",
			"price_list_name": pl_name,
			"enabled": 1,
			"buying": 1 if pl_type == "Buying" else 0,
			"selling": 1 if pl_type == "Selling" else 0,
			"currency": args["currency"]
		})

	curr_fiscal_year = get_fy_details(args.get('fy_start_date'), args.get('fy_end_date'))

	# Fiscal year
	records.append({
		"doctype":"Fiscal Year",
		'year': curr_fiscal_year,
		'year_start_date': args.get('fy_start_date'),
		'year_end_date': args.get('fy_end_date'),
	})

	# Company
	records.append({
		"doctype":"Company",
		'company_name':args.get('company_name'),
		'enable_perpetual_inventory': 1,
		'abbr':args.get('company_abbr'),
		'default_currency':args.get('currency'),
		'country': args.get('country'),
		'create_chart_of_accounts_based_on': 'Standard Template',
		'chart_of_accounts': args.get('chart_of_accounts'),
		'domain': args.get('domains')[0]
	})

	# Shopping cart
	# Needs Price List
	records.append({
		"doctype": "Shopping Cart Settings",
		"enabled": 1,
		'company': args.get('company_name')	,
		'price_list': frappe.db.get_value("Price List", {"selling": 1}),
		'default_customer_group': _("Individual"),
		'quotation_series': "QTN-",
	})

	# Bank Account
	if args.get("bank_account"):
		company_name = args.get('company_name')
		bank_account_group =  frappe.db.get_value("Account",
			{"account_type": "Bank", "is_group": 1, "root_type": "Asset",
				"company": company_name})
		if bank_account_group:
			records.append({
				"doctype": "Account",
				'account_name': args.get("bank_account"),
				'parent_account': bank_account_group,
				'is_group':0,
				'company': company_name,
				"account_type": "Bank",
			})

	return records

def get_email_digest():
	from frappe.utils.user import get_system_managers
	system_managers = get_system_managers(only_name=True)
	if not system_managers:
		return
	records = []

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
					edigest[df.fieldname] = 1

			records.append(edigest)

	# scheduler errors digest
	if companies:
		records.append({
			"doctype": "Email Digest",
			"name": "Scheduler Errors",
			"company": companies[0],
			"frequency": "Daily",
			"recipient_list": "\n".join(system_managers),
			"scheduler_errors": 1,
			"enabled": 1
		})
	return records

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
	if args.get('setup_website'):
		website_maker(args)

def get_fy_details(fy_start_date, fy_end_date):
	start_year = getdate(fy_start_date).year
	if start_year == getdate(fy_end_date).year:
		fy = cstr(start_year)
	else:
		fy = cstr(start_year) + '-' + cstr(start_year + 1)
	return fy