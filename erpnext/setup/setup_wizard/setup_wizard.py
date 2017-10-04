# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, copy

import os
import json
from frappe.utils import cstr, flt, getdate
from frappe import _
from frappe.utils.file_manager import save_file
from .default_website import website_maker
from .healthcare import setup_healthcare
import install_fixtures
from .sample_data import make_sample_data
from erpnext.accounts.doctype.account.account import RootNotEditable
from frappe.core.doctype.communication.comment import add_info_comment
from erpnext.setup.setup_wizard.domainify import setup_domain
from erpnext.setup.doctype.company.company import install_country_fixtures

def setup_complete(args=None):
	if frappe.db.sql("select name from tabCompany"):
		frappe.throw(_("Setup Already Complete!!"))

	install_fixtures.install(args.get("country"))

	create_price_lists(args)
	create_fiscal_year_and_company(args)
	create_sales_tax(args)
	create_employee_for_self(args)
	set_defaults(args)
	create_territories()
	create_feed_and_todo()
	create_email_digest()
	create_letter_head(args)
	set_no_copy_fields_in_variant_settings()

	if args.get('domain').lower() == 'education':
		create_academic_year()
		create_academic_term()

	if args.domain.lower() == 'healthcare':
		setup_healthcare()

	if args.get('setup_website'):
		website_maker(args)

	create_logo(args)

	frappe.local.message_log = []
	setup_domain(args.get('domain'))

	frappe.db.commit()
	login_as_first_user(args)

	frappe.db.commit()
	frappe.clear_cache()

	try:
		make_sample_data(args.get('domain'))
		frappe.clear_cache()
	except:
		# clear message
		if frappe.message_log:
			frappe.message_log.pop()

		pass

def create_fiscal_year_and_company(args):
	if (args.get('fy_start_date')):
		curr_fiscal_year = get_fy_details(args.get('fy_start_date'), args.get('fy_end_date'))
		frappe.get_doc({
			"doctype":"Fiscal Year",
			'year': curr_fiscal_year,
			'year_start_date': args.get('fy_start_date'),
			'year_end_date': args.get('fy_end_date'),
		}).insert()
		args["curr_fiscal_year"] = curr_fiscal_year

	# Company
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
			'domain': args.get('domain')
		}).insert()

		#Enable shopping cart
		enable_shopping_cart(args)

		# Bank Account
		create_bank_account(args)

def enable_shopping_cart(args):
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

def create_price_lists(args):
	for pl_type, pl_name in (("Selling", _("Standard Selling")), ("Buying", _("Standard Buying"))):
		frappe.get_doc({
			"doctype": "Price List",
			"price_list_name": pl_name,
			"enabled": 1,
			"buying": 1 if pl_type == "Buying" else 0,
			"selling": 1 if pl_type == "Selling" else 0,
			"currency": args["currency"]
		}).insert()

def set_defaults(args):
	# enable default currency
	frappe.db.set_value("Currency", args.get("currency"), "enabled", 1)

	global_defaults = frappe.get_doc("Global Defaults", "Global Defaults")
	global_defaults.update({
		'current_fiscal_year': args.get('curr_fiscal_year'),
		'default_currency': args.get('currency'),
		'default_company':args.get('company_name')	,
		"country": args.get("country"),
	})

	global_defaults.save()

	system_settings = frappe.get_doc("System Settings")
	system_settings.email_footer_address = args.get("company")
	system_settings.save()

	stock_settings = frappe.get_doc("Stock Settings")
	stock_settings.item_naming_by = "Item Code"
	stock_settings.valuation_method = "FIFO"
	stock_settings.default_warehouse = frappe.db.get_value('Warehouse', {'warehouse_name': _('Stores')})
	stock_settings.stock_uom = _("Nos")
	stock_settings.auto_indent = 1
	stock_settings.auto_insert_price_list_rate_if_missing = 1
	stock_settings.automatically_set_serial_nos_based_on_fifo = 1
	stock_settings.save()

	selling_settings = frappe.get_doc("Selling Settings")
	selling_settings.cust_master_name = "Customer Name"
	selling_settings.so_required = "No"
	selling_settings.dn_required = "No"
	selling_settings.allow_multiple_items = 1
	selling_settings.save()

	buying_settings = frappe.get_doc("Buying Settings")
	buying_settings.supp_master_name = "Supplier Name"
	buying_settings.po_required = "No"
	buying_settings.pr_required = "No"
	buying_settings.maintain_same_rate = 1
	buying_settings.allow_multiple_items = 1
	buying_settings.save()

	notification_control = frappe.get_doc("Notification Control")
	notification_control.quotation = 1
	notification_control.sales_invoice = 1
	notification_control.purchase_order = 1
	notification_control.save()

	hr_settings = frappe.get_doc("HR Settings")
	hr_settings.emp_created_by = "Naming Series"
	hr_settings.save()

	domain_settings = frappe.get_doc("Domain Settings")
	domain_settings.append('active_domains', dict(domain=_(args.get('domain'))))
	domain_settings.save()

def create_feed_and_todo():
	"""update Activity feed and create todo for creation of item, customer, vendor"""
	add_info_comment(**{
		"subject": _("ERPNext Setup Complete!")
	})

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

def get_fy_details(fy_start_date, fy_end_date):
	start_year = getdate(fy_start_date).year
	if start_year == getdate(fy_end_date).year:
		fy = cstr(start_year)
	else:
		fy = cstr(start_year) + '-' + cstr(start_year + 1)
	return fy

def create_sales_tax(args):
	country_wise_tax = get_country_wise_tax(args.get("country"))
	if country_wise_tax and len(country_wise_tax) > 0:
		for sales_tax, tax_data in country_wise_tax.items():
			make_tax_account_and_template(
				args.get("company_name"),
				tax_data.get('account_name'),
				tax_data.get('tax_rate'), sales_tax)

# Tax utils start
def make_tax_account_and_template(company, account_name, tax_rate, template_name=None):
	try:
		if not isinstance(account_name, (list, tuple)):
			account_name = [account_name]
			tax_rate = [tax_rate]

		accounts = []
		for i, name in enumerate(account_name):
			accounts.append(make_tax_account(company, account_name[i], tax_rate[i]))

		if accounts:
			make_sales_and_purchase_tax_templates(accounts, template_name)
	except frappe.NameError:
		pass
	except RootNotEditable:
		pass

def make_tax_account(company, account_name, tax_rate):
	tax_group = get_tax_account_group(company)
	if tax_group:
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
		}).insert(ignore_permissions=True)

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
			"category": "Valuation and Total",
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

# Tax utils end

def get_country_wise_tax(country):
	data = {}
	with open (os.path.join(os.path.dirname(__file__), "data", "country_wise_tax.json")) as countrywise_tax:
		data = json.load(countrywise_tax).get(country)

	return data

def create_letter_head(args):
	if args.get("attach_letterhead"):
		frappe.get_doc({
			"doctype":"Letter Head",
			"letter_head_name": _("Standard"),
			"is_default": 1
		}).insert()

		attach_letterhead = args.get("attach_letterhead").split(",")
		if len(attach_letterhead)==3:
			filename, filetype, content = attach_letterhead
			fileurl = save_file(filename, content, "Letter Head", _("Standard"), decode=True).file_url
			frappe.db.set_value("Letter Head", _("Standard"), "content", "<img src='%s' style='max-width: 100%%;'>" % fileurl)

def set_no_copy_fields_in_variant_settings():
	# set no copy fields of an item doctype to item variant settings
	doc = frappe.get_doc('Item Variant Settings')
	doc.set_default_fields()
	doc.save()

def create_logo(args):
	if args.get("attach_logo"):
		attach_logo = args.get("attach_logo").split(",")
		if len(attach_logo)==3:
			filename, filetype, content = attach_logo
			fileurl = save_file(filename, content, "Website Settings", "Website Settings",
				decode=True).file_url
			frappe.db.set_value("Website Settings", "Website Settings", "brand_html",
				"<img src='{0}' style='max-width: 40px; max-height: 25px;'> {1}".format(fileurl, args.get("company_name")	))

def create_territories():
	"""create two default territories, one for home country and one named Rest of the World"""
	from frappe.utils.nestedset import get_root_of
	country = frappe.db.get_default("country")
	root_territory = get_root_of("Territory")
	for name in (country, _("Rest Of The World")):
		if name and not frappe.db.exists("Territory", name):
			frappe.get_doc({
				"doctype": "Territory",
				"territory_name": name.replace("'", ""),
				"parent_territory": root_territory,
				"is_group": "No"
			}).insert()

def login_as_first_user(args):
	if args.get("email") and hasattr(frappe.local, "login_manager"):
		frappe.local.login_manager.login_as(args.get("email"))

def create_employee_for_self(args):
	if frappe.session.user == 'Administrator':
		return

	# create employee for self
	emp = frappe.get_doc({
		"doctype": "Employee",
		"employee_name": " ".join(filter(None, [args.get("first_name"), args.get("last_name")])),
		"user_id": frappe.session.user,
		"status": "Active",
		"company": args.get("company_name")
	})
	emp.flags.ignore_mandatory = True
	emp.insert(ignore_permissions = True)

# Schools
def create_academic_term():
	at = ["Semester 1", "Semester 2", "Semester 3"]
	ay = ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18"]
	for y in ay:
		for t in at:
			academic_term = frappe.new_doc("Academic Term")
			academic_term.academic_year = y
			academic_term.term_name = t
			try:
				academic_term.save()
			except frappe.DuplicateEntryError:
				pass

def create_academic_year():
	ac = ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18"]
	for d in ac:
		academic_year = frappe.new_doc("Academic Year")
		academic_year.academic_year_name = d
		try:
			academic_year.save()
		except frappe.DuplicateEntryError:
			pass

