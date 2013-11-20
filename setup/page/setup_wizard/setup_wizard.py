# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes, json, base64

from webnotes.utils import cint, cstr, getdate, now, nowdate, get_defaults
from webnotes import _
from webnotes.utils.file_manager import save_file

@webnotes.whitelist()
def setup_account(args=None):
	# if webnotes.conn.sql("select name from tabCompany"):
	# 	webnotes.throw(_("Setup Already Complete!!"))
		
	if not args:
		args = webnotes.local.form_dict
	if isinstance(args, basestring):
		args = json.loads(args)
	args = webnotes._dict(args)
	
	update_profile_name(args)
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
	webnotes.conn.set_value('Control Panel', None, 'home_page', 'desktop')

	webnotes.clear_cache()
	webnotes.conn.commit()
	
	# suppress msgprints
	webnotes.local.message_log = []

	return "okay"
	
def update_profile_name(args):
	if args.get("email"):
		args['name'] = args.get("email")
		webnotes.flags.mute_emails = True
		webnotes.bean({
			"doctype":"Profile",
			"email": args.get("email"),
			"first_name": args.get("first_name"),
			"last_name": args.get("last_name")
		}).insert()
		webnotes.flags.mute_emails = False
		from webnotes.auth import _update_password
		_update_password(args.get("email"), args.get("password"))

	else:
		args['name'] = webnotes.session.user

		# Update Profile
		if not args.get('last_name') or args.get('last_name')=='None': 
				args['last_name'] = None
		webnotes.conn.sql("""update `tabProfile` SET first_name=%(first_name)s,
			last_name=%(last_name)s WHERE name=%(name)s""", args)
		
	if args.get("attach_profile"):
		filename, filetype, content = args.get("attach_profile").split(",")
		fileurl = save_file(filename, content, "Profile", args.get("name"), decode=True).file_name
		webnotes.conn.set_value("Profile", args.get("name"), "user_image", fileurl)
		
	add_all_roles_to(args.get("name"))
	
def create_fiscal_year_and_company(args):
	curr_fiscal_year, fy_start_date, fy_abbr = get_fy_details(args.get('fy_start'), True)
	webnotes.bean([{
		"doctype":"Fiscal Year",
		'year': curr_fiscal_year,
		'year_start_date': fy_start_date
	}]).insert()

	curr_fiscal_year, fy_start_date, fy_abbr = get_fy_details(args.get('fy_start'))
	webnotes.bean([{
		"doctype":"Fiscal Year",
		'year': curr_fiscal_year,
		'year_start_date': fy_start_date,
	}]).insert()

	
	# Company
	webnotes.bean([{
		"doctype":"Company",
		'domain': args.get("industry"),
		'company_name':args.get('company_name'),
		'abbr':args.get('company_abbr'),
		'default_currency':args.get('currency'),
	}]).insert()
	
	args["curr_fiscal_year"] = curr_fiscal_year
	
def create_price_lists(args):
	for pl_type in ["Selling", "Buying"]:
		webnotes.bean([
			{
				"doctype": "Price List",
				"price_list_name": "Standard " + pl_type,
				"buying_or_selling": pl_type,
				"currency": args["currency"]
			},
			{
				"doctype": "Applicable Territory",
				"parentfield": "valid_for_territories",
				"territory": "All Territories"
			}
		]).insert()
	
def set_defaults(args):
	# enable default currency
	webnotes.conn.set_value("Currency", args.get("currency"), "enabled", 1)
	
	global_defaults = webnotes.bean("Global Defaults", "Global Defaults")
	global_defaults.doc.fields.update({
		'current_fiscal_year': args.curr_fiscal_year,
		'default_currency': args.get('currency'),
		'default_company':args.get('company_name'),
		'date_format': webnotes.conn.get_value("Country", args.get("country"), "date_format"),
		"float_precision": 3,
		"country": args.get("country"),
		"time_zone": args.get("time_zone")
	})
	global_defaults.save()
	
	accounts_settings = webnotes.bean("Accounts Settings")
	accounts_settings.doc.auto_accounting_for_stock = 1
	accounts_settings.save()

	stock_settings = webnotes.bean("Stock Settings")
	stock_settings.doc.item_naming_by = "Item Code"
	stock_settings.doc.valuation_method = "FIFO"
	stock_settings.doc.stock_uom = "Nos"
	stock_settings.doc.auto_indent = 1
	stock_settings.save()
	
	selling_settings = webnotes.bean("Selling Settings")
	selling_settings.doc.cust_master_name = "Customer Name"
	selling_settings.doc.so_required = "No"
	selling_settings.doc.dn_required = "No"
	selling_settings.save()

	buying_settings = webnotes.bean("Buying Settings")
	buying_settings.doc.supp_master_name = "Supplier Name"
	buying_settings.doc.po_required = "No"
	buying_settings.doc.pr_required = "No"
	buying_settings.doc.maintain_same_rate = 1
	buying_settings.save()

	notification_control = webnotes.bean("Notification Control")
	notification_control.doc.quotation = 1
	notification_control.doc.sales_invoice = 1
	notification_control.doc.purchase_order = 1
	notification_control.save()

	hr_settings = webnotes.bean("HR Settings")
	hr_settings.doc.emp_created_by = "Naming Series"
	hr_settings.save()

	# control panel
	cp = webnotes.doc("Control Panel", "Control Panel")
	cp.company_name = args["company_name"]
	cp.save()
			
def create_feed_and_todo():
	"""update activty feed and create todo for creation of item, customer, vendor"""
	import home
	home.make_feed('Comment', 'ToDo', '', webnotes.session['user'],
		'ERNext Setup Complete!', '#6B24B3')

def create_email_digest():
	from webnotes.profile import get_system_managers
	system_managers = get_system_managers()
	if not system_managers: 
		return
	
	for company in webnotes.conn.sql_list("select name FROM `tabCompany`"):
		if not webnotes.conn.exists("Email Digest", "Default Weekly Digest - " + company):
			edigest = webnotes.bean({
				"doctype": "Email Digest",
				"name": "Default Weekly Digest - " + company,
				"company": company,
				"frequency": "Weekly",
				"recipient_list": "\n".join(system_managers)
			})

			for fieldname in edigest.meta.get_fieldnames({"fieldtype": "Check"}):
				edigest.doc.fields[fieldname] = 1
		
			edigest.insert()
		
def get_fy_details(fy_start, last_year=False):
	st = {'1st Jan':'01-01','1st Apr':'04-01','1st Jul':'07-01', '1st Oct': '10-01'}
	if cint(getdate(nowdate()).month) < cint((st[fy_start].split('-'))[0]):
		curr_year = getdate(nowdate()).year - 1
	else:
		curr_year = getdate(nowdate()).year
	
	if last_year:
		curr_year = curr_year - 1
	
	stdt = cstr(curr_year)+'-'+cstr(st[fy_start])

	if(fy_start == '1st Jan'):
		fy = cstr(curr_year)
		abbr = cstr(fy)[-2:]
	else:
		fy = cstr(curr_year) + '-' + cstr(curr_year+1)
		abbr = cstr(curr_year)[-2:] + '-' + cstr(curr_year+1)[-2:]
	return fy, stdt, abbr

def create_taxes(args):
	for i in xrange(1,6):
		if args.get("tax_" + str(i)):
			webnotes.bean({
				"doctype":"Account",
				"company": args.get("company_name"),
				"parent_account": "Duties and Taxes - " + args.get("company_abbr"),
				"account_name": args.get("tax_" + str(i)),
				"group_or_ledger": "Ledger",
				"is_pl_account": "No",
				"account_type": "Tax",
				"tax_rate": args.get("tax_rate_" + str(i))
			}).insert()

def create_items(args):
	for i in xrange(1,6):
		item = args.get("item_" + str(i))
		if item:
			item_group = args.get("item_group_" + str(i))
			webnotes.bean({
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
				webnotes.conn.set_value("Item", item, "image", fileurl)
					
	for i in xrange(1,6):
		item = args.get("item_buy_" + str(i))
		if item:
			item_group = args.get("item_buy_group_" + str(i))
			webnotes.bean({
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
				webnotes.conn.set_value("Item", item, "image", fileurl)


def create_customers(args):
	for i in xrange(1,6):
		customer = args.get("customer_" + str(i))
		if customer:
			webnotes.bean({
				"doctype":"Customer",
				"customer_name": customer,
				"customer_type": "Company",
				"customer_group": "Commercial",
				"territory": args.get("country"),
				"company": args.get("company_name")
			}).insert()
			
			if args.get("customer_contact_" + str(i)):
				contact = args.get("customer_contact_" + str(i)).split(" ")
				webnotes.bean({
					"doctype":"Contact",
					"customer": customer,
					"first_name":contact[0],
					"last_name": len(contact) > 1 and contact[1] or ""
				}).insert()
			
def create_suppliers(args):
	for i in xrange(1,6):
		supplier = args.get("supplier_" + str(i))
		if supplier:
			webnotes.bean({
				"doctype":"Supplier",
				"supplier_name": supplier,
				"supplier_type": "Local",
				"company": args.get("company_name")
			}).insert()

			if args.get("supplier_contact_" + str(i)):
				contact = args.get("supplier_contact_" + str(i)).split(" ")
				webnotes.bean({
					"doctype":"Contact",
					"supplier": supplier,
					"first_name":contact[0],
					"last_name": len(contact) > 1 and contact[1] or ""
				}).insert()


def create_letter_head(args):
	if args.get("attach_letterhead"):
		lh = webnotes.bean({
			"doctype":"Letter Head",
			"letter_head_name": "Standard",
			"is_default": 1
		}).insert()
		
		filename, filetype, content = args.get("attach_letterhead").split(",")
		fileurl = save_file(filename, content, "Letter Head", "Standard", decode=True).file_name
		webnotes.conn.set_value("Letter Head", "Standard", "content", "<img src='%s' style='max-width: 100%%;'>" % fileurl)
		
		
				
def add_all_roles_to(name):
	profile = webnotes.doc("Profile", name)
	for role in webnotes.conn.sql("""select name from tabRole"""):
		if role[0] not in ["Administrator", "Guest", "All", "Customer", "Supplier", "Partner"]:
			d = profile.addchild("user_roles", "UserRole")
			d.role = role[0]
			d.insert()
			
def create_territories():
	"""create two default territories, one for home country and one named Rest of the World"""
	from setup.utils import get_root_of
	country = webnotes.conn.get_value("Control Panel", None, "country")
	root_territory = get_root_of("Territory")
	for name in (country, "Rest Of The World"):
		if name and not webnotes.conn.exists("Territory", name):
			webnotes.bean({
				"doctype": "Territory",
				"territory_name": name.replace("'", ""),
				"parent_territory": root_territory,
				"is_group": "No"
			}).insert()