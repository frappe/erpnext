# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json

from frappe.utils import cstr, flt, getdate
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.translate import (set_default_language, get_dict,
	get_lang_dict, send_translations, get_language_from_code)
from frappe.geo.country_info import get_country_info
from frappe.utils.nestedset import get_root_of
from default_website import website_maker
import install_fixtures

@frappe.whitelist()
def setup_account(args=None):
	try:
		if frappe.db.sql("select name from tabCompany"):
			frappe.throw(_("Setup Already Complete!!"))

		if not args:
			args = frappe.local.form_dict
		if isinstance(args, basestring):
			args = json.loads(args)

		args = frappe._dict(args)

		if args.language != "english":
			set_default_language(args.language)

		install_fixtures.install(args.get("country"))

		update_user_name(args)
		frappe.local.message_log = []

		create_fiscal_year_and_company(args)
		frappe.local.message_log = []

		set_defaults(args)
		frappe.local.message_log = []

		create_territories()
		frappe.local.message_log = []

		create_price_lists(args)
		frappe.local.message_log = []

		create_feed_and_todo()
		frappe.local.message_log = []

		create_email_digest()
		frappe.local.message_log = []

		create_letter_head(args)
		frappe.local.message_log = []

		create_taxes(args)
		frappe.local.message_log = []

		create_items(args)
		frappe.local.message_log = []

		create_customers(args)
		frappe.local.message_log = []

		create_suppliers(args)
		frappe.local.message_log = []

		frappe.db.set_default('desktop:home_page', 'desktop')

		website_maker(args.company_name.strip(), args.company_tagline, args.name)
		create_logo(args)

		login_as_first_user(args)

		frappe.clear_cache()
		frappe.db.commit()

	except:
		if args:
			traceback = frappe.get_traceback()
			for hook in frappe.get_hooks("setup_wizard_exception"):
				frappe.get_attr(hook)(traceback, args)

		raise

	else:
		for hook in frappe.get_hooks("setup_wizard_success"):
			frappe.get_attr(hook)(args)


def update_user_name(args):
	if args.get("email"):
		args['name'] = args.get("email")
		frappe.flags.mute_emails = True
		frappe.get_doc({
			"doctype":"User",
			"email": args.get("email"),
			"first_name": args.get("first_name"),
			"last_name": args.get("last_name")
		}).insert()
		frappe.flags.mute_emails = False
		from frappe.auth import _update_password
		_update_password(args.get("email"), args.get("password"))

	else:
		args['name'] = frappe.session.user

		# Update User
		if not args.get('last_name') or args.get('last_name')=='None':
				args['last_name'] = None
		frappe.db.sql("""update `tabUser` SET first_name=%(first_name)s,
			last_name=%(last_name)s WHERE name=%(name)s""", args)

	if args.get("attach_user"):
		attach_user = args.get("attach_user").split(",")
		if len(attach_user)==3:
			filename, filetype, content = attach_user
			fileurl = save_file(filename, content, "User", args.get("name"), decode=True).file_url
			frappe.db.set_value("User", args.get("name"), "user_image", fileurl)

	add_all_roles_to(args.get("name"))

def create_fiscal_year_and_company(args):
	curr_fiscal_year = get_fy_details(args.get('fy_start_date'), args.get('fy_end_date'))
	frappe.get_doc({
		"doctype":"Fiscal Year",
		'year': curr_fiscal_year,
		'year_start_date': args.get('fy_start_date'),
		'year_end_date': args.get('fy_end_date'),
	}).insert()

	# Company
	frappe.get_doc({
		"doctype":"Company",
		'domain': args.get("industry"),
		'company_name':args.get('company_name').strip(),
		'abbr':args.get('company_abbr'),
		'default_currency':args.get('currency'),
		'country': args.get('country'),
		'chart_of_accounts': args.get(('chart_of_accounts')),
	}).insert()

	# Bank Account

	args["curr_fiscal_year"] = curr_fiscal_year

def create_price_lists(args):
	for pl_type, pl_name in (("Selling", _("Standard Selling")), ("Buying", _("Standard Buying"))):
		frappe.get_doc({
			"doctype": "Price List",
			"price_list_name": pl_name,
			"enabled": 1,
			"buying": 1 if pl_type == "Buying" else 0,
			"selling": 1 if pl_type == "Selling" else 0,
			"currency": args["currency"],
			"territories": [{
				"territory": get_root_of("Territory")
			}]
		}).insert()

def set_defaults(args):
	# enable default currency
	frappe.db.set_value("Currency", args.get("currency"), "enabled", 1)

	global_defaults = frappe.get_doc("Global Defaults", "Global Defaults")
	global_defaults.update({
		'current_fiscal_year': args.curr_fiscal_year,
		'default_currency': args.get('currency'),
		'default_company':args.get('company_name').strip(),
		"country": args.get("country"),
	})

	global_defaults.save()

	number_format = get_country_info(args.get("country")).get("number_format", "#,###.##")

	# replace these as float number formats, as they have 0 precision
	# and are currency number formats and not for floats
	if number_format=="#.###":
		number_format = "#.###,##"
	elif number_format=="#,###":
		number_format = "#,###.##"

	system_settings = frappe.get_doc("System Settings", "System Settings")
	system_settings.update({
		"language": args.get("language"),
		"time_zone": args.get("timezone"),
		"float_precision": 3,
		'date_format': frappe.db.get_value("Country", args.get("country"), "date_format"),
		'number_format': number_format,
		'enable_scheduler': 1
	})
	system_settings.save()

	accounts_settings = frappe.get_doc("Accounts Settings")
	accounts_settings.auto_accounting_for_stock = 1
	accounts_settings.save()

	stock_settings = frappe.get_doc("Stock Settings")
	stock_settings.item_naming_by = "Item Code"
	stock_settings.valuation_method = "FIFO"
	stock_settings.stock_uom = _("Nos")
	stock_settings.auto_indent = 1
	stock_settings.save()

	selling_settings = frappe.get_doc("Selling Settings")
	selling_settings.cust_master_name = "Customer Name"
	selling_settings.so_required = "No"
	selling_settings.dn_required = "No"
	selling_settings.save()

	buying_settings = frappe.get_doc("Buying Settings")
	buying_settings.supp_master_name = "Supplier Name"
	buying_settings.po_required = "No"
	buying_settings.pr_required = "No"
	buying_settings.maintain_same_rate = 1
	buying_settings.save()

	notification_control = frappe.get_doc("Notification Control")
	notification_control.quotation = 1
	notification_control.sales_invoice = 1
	notification_control.purchase_order = 1
	notification_control.save()

	hr_settings = frappe.get_doc("HR Settings")
	hr_settings.emp_created_by = "Naming Series"
	hr_settings.save()

def create_feed_and_todo():
	"""update Activity feed and create todo for creation of item, customer, vendor"""
	frappe.get_doc({
		"doctype": "Feed",
		"feed_type": "Comment",
		"subject": "ERPNext Setup Complete!"
	}).insert(ignore_permissions=True)

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

			for fieldname in edigest.meta.get("fields", {"fieldtype": "Check"}):
				if fieldname != "scheduler_errors":
					edigest.set(fieldname, 1)

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

def create_taxes(args):
	for i in xrange(1,6):
		if args.get("tax_" + str(i)):
			# replace % in case someone also enters the % symbol
			tax_rate = (args.get("tax_rate_" + str(i)) or "").replace("%", "")

			try:
				tax_group = frappe.db.get_value("Account", {"company": args.get("company_name"),
					"group_or_ledger": "Group", "account_type": "Tax", "root_type": "Liability"})
				if tax_group:
					frappe.get_doc({
						"doctype":"Account",
						"company": args.get("company_name").strip(),
						"parent_account": tax_group,
						"account_name": args.get("tax_" + str(i)),
						"group_or_ledger": "Ledger",
						"report_type": "Balance Sheet",
						"account_type": "Tax",
						"tax_rate": flt(tax_rate) if tax_rate else None
					}).insert()
			except frappe.NameError, e:
				if e.args[2][0]==1062:
					pass
				else:
					raise

def create_items(args):
	for i in xrange(1,6):
		item = args.get("item_" + str(i))
		if item:
			item_group = args.get("item_group_" + str(i))
			is_sales_item = args.get("is_sales_item_" + str(i))
			is_purchase_item = args.get("is_purchase_item_" + str(i))
			is_stock_item = item_group!=_("Services")
			default_warehouse = ""
			if is_stock_item:
				default_warehouse = frappe.db.get_value("Warehouse", filters={
					"warehouse_name": _("Finished Goods") if is_sales_item else _("Stores"),
					"company": args.get("company_name").strip()
				})

			frappe.get_doc({
				"doctype":"Item",
				"item_code": item,
				"item_name": item,
				"description": item,
				"is_sales_item": "Yes" if is_sales_item else "No",
				"is_purchase_item": "Yes" if is_purchase_item else "No",
				"show_in_website": 1,
				"is_stock_item": is_stock_item and "Yes" or "No",
				"item_group": item_group,
				"stock_uom": args.get("item_uom_" + str(i)),
				"default_warehouse": default_warehouse
			}).insert()

			if args.get("item_img_" + str(i)):
				item_image = args.get("item_img_" + str(i)).split(",")
				if len(item_image)==3:
					filename, filetype, content = item_image
					fileurl = save_file(filename, content, "Item", item, decode=True).file_url
					frappe.db.set_value("Item", item, "image", fileurl)

def create_customers(args):
	for i in xrange(1,6):
		customer = args.get("customer_" + str(i))
		if customer:
			frappe.get_doc({
				"doctype":"Customer",
				"customer_name": customer,
				"customer_type": "Company",
				"customer_group": _("Commercial"),
				"territory": args.get("country"),
				"company": args.get("company_name").strip()
			}).insert()

			if args.get("customer_contact_" + str(i)):
				contact = args.get("customer_contact_" + str(i)).split(" ")
				frappe.get_doc({
					"doctype":"Contact",
					"customer": customer,
					"first_name":contact[0],
					"last_name": len(contact) > 1 and contact[1] or ""
				}).insert()

def create_suppliers(args):
	for i in xrange(1,6):
		supplier = args.get("supplier_" + str(i))
		if supplier:
			frappe.get_doc({
				"doctype":"Supplier",
				"supplier_name": supplier,
				"supplier_type": _("Local"),
				"company": args.get("company_name").strip()
			}).insert()

			if args.get("supplier_contact_" + str(i)):
				contact = args.get("supplier_contact_" + str(i)).split(" ")
				frappe.get_doc({
					"doctype":"Contact",
					"supplier": supplier,
					"first_name":contact[0],
					"last_name": len(contact) > 1 and contact[1] or ""
				}).insert()


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

def create_logo(args):
	if args.get("attach_logo"):
		attach_logo = args.get("attach_logo").split(",")
		if len(attach_logo)==3:
			filename, filetype, content = attach_logo
			fileurl = save_file(filename, content, "Website Settings", "Website Settings",
				decode=True).file_url
			frappe.db.set_value("Website Settings", "Website Settings", "banner_html",
				"<img src='%s' style='max-width: 100%%;'>" % fileurl)

def add_all_roles_to(name):
	user = frappe.get_doc("User", name)
	for role in frappe.db.sql("""select name from tabRole"""):
		if role[0] not in ["Administrator", "Guest", "All", "Customer", "Supplier", "Partner", "Employee"]:
			d = user.append("user_roles")
			d.role = role[0]
	user.save()

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
		frappe.local.login_manager.user = args.get("email")
		frappe.local.login_manager.post_login()

@frappe.whitelist()
def load_messages(language):
	frappe.clear_cache()
	lang = get_lang_dict()[language]
	frappe.local.lang = lang
	m = get_dict("page", "setup-wizard")
	m.update(get_dict("boot"))
	send_translations(m)
	return lang

@frappe.whitelist()
def load_languages():
	return {
		"default_language": get_language_from_code(frappe.local.lang),
		"languages": sorted(get_lang_dict().keys())
	}
