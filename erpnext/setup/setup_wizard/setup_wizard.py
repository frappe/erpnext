# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, copy

from frappe.utils import cstr, flt, getdate
from frappe import _
from frappe.utils.file_manager import save_file
from .default_website import website_maker
import install_fixtures
from .sample_data import make_sample_data
from erpnext.accounts.utils import FiscalYearError
from erpnext.accounts.doctype.account.account import RootNotEditable

def setup_complete(args=None):
	if frappe.db.sql("select name from tabCompany"):
		frappe.throw(_("Setup Already Complete!!"))

	install_fixtures.install(args.get("country"))

	update_user_name(args)
	create_fiscal_year_and_company(args)
	create_users(args)
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
	frappe.local.message_log = []

	website_maker(args.company_name.strip(), args.company_tagline, args.name)
	create_logo(args)

	frappe.db.commit()
	login_as_first_user(args)
	frappe.db.commit()
	frappe.clear_cache()

	if args.get("add_sample_data"):
		try:
			make_sample_data()
			frappe.clear_cache()
		except FiscalYearError:
			pass


def update_user_name(args):
	if args.get("email"):
		args['name'] = args.get("email")

		_mute_emails, frappe.flags.mute_emails = frappe.flags.mute_emails, True
		doc = frappe.get_doc({
			"doctype":"User",
			"email": args.get("email"),
			"first_name": args.get("first_name"),
			"last_name": args.get("last_name")
		})
		doc.flags.no_welcome_mail = True
		doc.insert()
		frappe.flags.mute_emails = _mute_emails
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
			"currency": args["currency"]
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

	frappe.db.set_value("System Settings", None, "email_footer_address", args.get("company"))

	accounts_settings = frappe.get_doc("Accounts Settings")
	accounts_settings.auto_accounting_for_stock = 1
	accounts_settings.save()

	stock_settings = frappe.get_doc("Stock Settings")
	stock_settings.item_naming_by = "Item Code"
	stock_settings.valuation_method = "FIFO"
	stock_settings.stock_uom = _("Nos")
	stock_settings.auto_indent = 1
	stock_settings.auto_insert_price_list_rate_if_missing = 1
	stock_settings.automatically_set_serial_nos_based_on_fifo = 1
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

def create_taxes(args):

	for i in xrange(1,6):
		if args.get("tax_" + str(i)):
			# replace % in case someone also enters the % symbol
			tax_rate = cstr(args.get("tax_rate_" + str(i)) or "").replace("%", "")

			try:
				tax_group = frappe.db.get_value("Account", {"company": args.get("company_name"),
					"is_group": 1, "account_type": "Tax", "root_type": "Liability"})
				if tax_group:
					account = make_tax_head(args, i, tax_group, tax_rate)
					make_sales_and_purchase_tax_templates(account)

			except frappe.NameError, e:
				if e.args[2][0]==1062:
					pass
				else:
					raise
			except RootNotEditable, e:
				pass

def make_tax_head(args, i, tax_group, tax_rate):
	return frappe.get_doc({
		"doctype":"Account",
		"company": args.get("company_name").strip(),
		"parent_account": tax_group,
		"account_name": args.get("tax_" + str(i)),
		"is_group": 0,
		"report_type": "Balance Sheet",
		"account_type": "Tax",
		"tax_rate": flt(tax_rate) if tax_rate else None
	}).insert(ignore_permissions=True)

def make_sales_and_purchase_tax_templates(account):
	doc = {
		"doctype": "Sales Taxes and Charges Template",
		"title": account.name,
		"taxes": [{
		    "category": "Valuation and Total",
		    "charge_type": "On Net Total",
			"account_head": account.name,
			"description": "{0} @ {1}".format(account.account_name, account.tax_rate),
			"rate": account.tax_rate
		}]
	}

	# Sales
	frappe.get_doc(copy.deepcopy(doc)).insert()

	# Purchase
	doc["doctype"] = "Purchase Taxes and Charges Template"
	frappe.get_doc(copy.deepcopy(doc)).insert()

def create_items(args):
	for i in xrange(1,6):
		item = args.get("item_" + str(i))
		if item:
			item_group = args.get("item_group_" + str(i))
			is_sales_item = args.get("is_sales_item_" + str(i))
			is_purchase_item = args.get("is_purchase_item_" + str(i))
			is_stock_item = item_group!=_("Services")
			is_pro_applicable = item_group!=_("Services")
			default_warehouse = ""
			if is_stock_item:
				default_warehouse = frappe.db.get_value("Warehouse", filters={
					"warehouse_name": _("Finished Goods") if is_sales_item else _("Stores"),
					"company": args.get("company_name").strip()
				})

			try:
				frappe.get_doc({
					"doctype":"Item",
					"item_code": item,
					"item_name": item,
					"description": item,
					"is_sales_item": 1 if is_sales_item else 0,
					"is_purchase_item": 1 if is_purchase_item else 0,
					"show_in_website": 1,
					"is_stock_item": is_stock_item and 1 or 0,
					"is_pro_applicable": is_pro_applicable and 1 or 0,
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

				if args.get("item_price_" + str(i)):
					item_price = flt(args.get("item_price_" + str(i)))

					if is_sales_item:
						price_list_name = frappe.db.get_value("Price List", {"selling": 1})
						make_item_price(item, price_list_name, item_price)

					if is_purchase_item:
						price_list_name = frappe.db.get_value("Price List", {"buying": 1})
						make_item_price(item, price_list_name, item_price)

			except frappe.NameError:
				pass

def make_item_price(item, price_list_name, item_price):
	frappe.get_doc({
		"doctype": "Item Price",
		"price_list": price_list_name,
		"item_code": item,
		"price_list_rate": item_price
	}).insert()


def create_customers(args):
	for i in xrange(1,6):
		customer = args.get("customer_" + str(i))
		if customer:
			try:
				frappe.get_doc({
					"doctype":"Customer",
					"customer_name": customer,
					"customer_type": "Company",
					"customer_group": _("Commercial"),
					"territory": args.get("country"),
					"company": args.get("company_name").strip()
				}).insert()

				if args.get("customer_contact_" + str(i)):
					create_contact(args.get("customer_contact_" + str(i)),
						"customer", customer)
			except frappe.NameError:
				pass

def create_suppliers(args):
	for i in xrange(1,6):
		supplier = args.get("supplier_" + str(i))
		if supplier:
			try:
				frappe.get_doc({
					"doctype":"Supplier",
					"supplier_name": supplier,
					"supplier_type": _("Local"),
					"company": args.get("company_name").strip()
				}).insert()

				if args.get("supplier_contact_" + str(i)):
					create_contact(args.get("supplier_contact_" + str(i)),
						"supplier", supplier)
			except frappe.NameError:
				pass

def create_contact(contact, party_type, party):
	"""Create contact based on given contact name"""
	contact = contact.strip().split(" ")

	frappe.get_doc({
		"doctype":"Contact",
		party_type: party,
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
			frappe.db.set_value("Website Settings", "Website Settings", "brand_html",
				"<img src='{0}' style='max-width: 40px; max-height: 25px;'> {1}".format(fileurl, args.get("company_name").strip()))

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
		frappe.local.login_manager.login_as(args.get("email"))

def create_users(args):
	# create employee for self
	emp = frappe.get_doc({
		"doctype": "Employee",
		"full_name": " ".join(filter(None, [args.get("first_name"), args.get("last_name")])),
		"user_id": frappe.session.user,
		"status": "Active",
		"company": args.get("company_name")
	})
	emp.flags.ignore_mandatory = True
	emp.insert(ignore_permissions = True)

	for i in xrange(1,5):
		email = args.get("user_email_" + str(i))
		fullname = args.get("user_fullname_" + str(i))
		if email:
			if not fullname:
				fullname = email.split("@")[0]

			parts = fullname.split(" ", 1)

			user = frappe.get_doc({
				"doctype": "User",
				"email": email,
				"first_name": parts[0],
				"last_name": parts[1] if len(parts) > 1 else "",
				"enabled": 1,
				"user_type": "System User"
			})

			# default roles
			user.append_roles("Projects User", "Stock User", "Support Team")

			if args.get("user_sales_" + str(i)):
				user.append_roles("Sales User", "Sales Manager", "Accounts User")
			if args.get("user_purchaser_" + str(i)):
				user.append_roles("Purchase User", "Purchase Manager", "Accounts User")
			if args.get("user_accountant_" + str(i)):
				user.append_roles("Accounts Manager", "Accounts User")

			user.flags.delay_emails = True

			if not frappe.db.get_value("User", email):
				user.insert(ignore_permissions=True)

				# create employee
				emp = frappe.get_doc({
					"doctype": "Employee",
					"full_name": fullname,
					"user_id": email,
					"status": "Active",
					"company": args.get("company_name")
				})
				emp.flags.ignore_mandatory = True
				emp.insert(ignore_permissions = True)

