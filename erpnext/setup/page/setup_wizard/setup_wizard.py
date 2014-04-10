# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json, base64

from frappe.utils import cint, cstr, getdate, now, nowdate, get_defaults
from frappe import _
from frappe.utils.file_manager import save_file

@frappe.whitelist()
def setup_account(args=None):
	# if frappe.db.sql("select name from tabCompany"):
	# 	frappe.throw(_("Setup Already Complete!!"))

	if not args:
		args = frappe.local.form_dict
	if isinstance(args, basestring):
		args = json.loads(args)
	args = frappe._dict(args)

	update_user_name(args)
	create_fiscal_year_and_company(args)
	set_defaults(args)
	create_territories()
	create_price_lists(args)
	create_feed_and_todo()
	create_email_digest()
	create_letter_head(args)
	create_taxes(args)
	create_items(args)
	create_customers(args)
	create_suppliers(args)
	frappe.db.set_default('desktop:home_page', 'desktop')

	frappe.clear_cache()
	frappe.db.commit()

	# suppress msgprints
	frappe.local.message_log = []

	return "okay"

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
		filename, filetype, content = args.get("attach_user").split(",")
		fileurl = save_file(filename, content, "User", args.get("name"), decode=True).file_name
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
		'company_name':args.get('company_name'),
		'abbr':args.get('company_abbr'),
		'default_currency':args.get('currency'),
		'country': args.get('country'),
		'chart_of_accounts': args.get(('chart_of_accounts')),
	}).insert()

	args["curr_fiscal_year"] = curr_fiscal_year

def create_price_lists(args):
	for pl_type in ["Selling", "Buying"]:
		frappe.get_doc({
			"doctype": "Price List",
			"price_list_name": "Standard " + pl_type,
			"enabled": 1,
			"buying": 1 if pl_type == "Buying" else 0,
			"selling": 1 if pl_type == "Selling" else 0,
			"currency": args["currency"],
			"valid_for_territories": [{
				"territory": "All Territories"
			}]
		}).insert()

def set_defaults(args):
	# enable default currency
	frappe.db.set_value("Currency", args.get("currency"), "enabled", 1)

	global_defaults = frappe.get_doc("Global Defaults", "Global Defaults")
	global_defaults.update({
		'current_fiscal_year': args.curr_fiscal_year,
		'default_currency': args.get('currency'),
		'default_company':args.get('company_name'),
		'date_format': frappe.db.get_value("Country", args.get("country"), "date_format"),
		"float_precision": 3,
		"country": args.get("country"),
		"time_zone": args.get("time_zone")
	})
	global_defaults.save()

	accounts_settings = frappe.get_doc("Accounts Settings")
	accounts_settings.auto_accounting_for_stock = 1
	accounts_settings.save()

	stock_settings = frappe.get_doc("Stock Settings")
	stock_settings.item_naming_by = "Item Code"
	stock_settings.valuation_method = "FIFO"
	stock_settings.stock_uom = "Nos"
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

	email_settings = frappe.get_doc("Outgoing Email Settings")
	email_settings.send_print_in_body_and_attachment = 1
	email_settings.save()

	# default
	frappe.db.set_default("company_name", args["company_name"])

def create_feed_and_todo():
	"""update activty feed and create todo for creation of item, customer, vendor"""
	from erpnext.home import make_feed
	make_feed('Comment', 'ToDo', '', frappe.session['user'],
		'ERNext Setup Complete!', '#6B24B3')

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
			frappe.get_doc({
				"doctype":"Account",
				"company": args.get("company_name"),
				"parent_account": "Duties and Taxes - " + args.get("company_abbr"),
				"account_name": args.get("tax_" + str(i)),
				"group_or_ledger": "Ledger",
				"report_type": "Balance Sheet",
				"account_type": "Tax",
				"tax_rate": args.get("tax_rate_" + str(i))
			}).insert()

def create_items(args):
	for i in xrange(1,6):
		item = args.get("item_" + str(i))
		if item:
			item_group = args.get("item_group_" + str(i))
			frappe.get_doc({
				"doctype":"Item",
				"item_code": item,
				"item_name": item,
				"description": item,
				"is_sales_item": "Yes",
				"is_stock_item": item_group!="Services" and "Yes" or "No",
				"item_group": item_group,
				"stock_uom": args.get("item_uom_" + str(i)),
				"default_warehouse": item_group!="Service" and ("Finished Goods - " + args.get("company_abbr")) or ""
			}).insert()

			if args.get("item_img_" + str(i)):
				filename, filetype, content = args.get("item_img_" + str(i)).split(",")
				fileurl = save_file(filename, content, "Item", item, decode=True).file_name
				frappe.db.set_value("Item", item, "image", fileurl)

	for i in xrange(1,6):
		item = args.get("item_buy_" + str(i))
		if item:
			item_group = args.get("item_buy_group_" + str(i))
			frappe.get_doc({
				"doctype":"Item",
				"item_code": item,
				"item_name": item,
				"description": item,
				"is_sales_item": "No",
				"is_stock_item": item_group!="Services" and "Yes" or "No",
				"item_group": item_group,
				"stock_uom": args.get("item_buy_uom_" + str(i)),
				"default_warehouse": item_group!="Service" and ("Stores - " + args.get("company_abbr")) or ""
			}).insert()

			if args.get("item_img_" + str(i)):
				filename, filetype, content = args.get("item_img_" + str(i)).split(",")
				fileurl = save_file(filename, content, "Item", item, decode=True).file_name
				frappe.db.set_value("Item", item, "image", fileurl)


def create_customers(args):
	for i in xrange(1,6):
		customer = args.get("customer_" + str(i))
		if customer:
			frappe.get_doc({
				"doctype":"Customer",
				"customer_name": customer,
				"customer_type": "Company",
				"customer_group": "Commercial",
				"territory": args.get("country"),
				"company": args.get("company_name")
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
				"supplier_type": "Local",
				"company": args.get("company_name")
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
		lh = frappe.get_doc({
			"doctype":"Letter Head",
			"letter_head_name": "Standard",
			"is_default": 1
		}).insert()

		filename, filetype, content = args.get("attach_letterhead").split(",")
		fileurl = save_file(filename, content, "Letter Head", "Standard", decode=True).file_name
		frappe.db.set_value("Letter Head", "Standard", "content", "<img src='%s' style='max-width: 100%%;'>" % fileurl)

def add_all_roles_to(name):
	user = frappe.get_doc("User", name)
	for role in frappe.db.sql("""select name from tabRole"""):
		if role[0] not in ["Administrator", "Guest", "All", "Customer", "Supplier", "Partner"]:
			d = user.append("user_roles")
			d.role = role[0]
	user.save()

def create_territories():
	"""create two default territories, one for home country and one named Rest of the World"""
	from frappe.utils.nestedset import get_root_of
	country = frappe.db.get_default("country")
	root_territory = get_root_of("Territory")
	for name in (country, "Rest Of The World"):
		if name and not frappe.db.exists("Territory", name):
			frappe.get_doc({
				"doctype": "Territory",
				"territory_name": name.replace("'", ""),
				"parent_territory": root_territory,
				"is_group": "No"
			}).insert()
