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
import install_fixtures
from .sample_data import make_sample_data
from erpnext.accounts.doctype.account.account import RootNotEditable
from frappe.core.doctype.communication.comment import add_info_comment
from erpnext.setup.setup_wizard.domainify import setup_domain

def setup_complete(args=None):
	if frappe.db.sql("select name from tabCompany"):
		frappe.throw(_("Setup Already Complete!!"))

	install_fixtures.install(args.get("country"))

	create_price_lists(args)
	create_fiscal_year_and_company(args)
	create_sales_tax(args)
	create_users(args)
	set_defaults(args)
	create_territories()
	create_feed_and_todo()
	create_email_digest()
	create_letter_head(args)
	create_taxes(args)
	create_items(args)
	create_customers(args)
	create_suppliers(args)

	if args.domain.lower() == 'education':
		create_academic_year()
		create_academic_term()
		create_program(args)
		create_course(args)
		create_instructor(args)
		create_room(args)

	if args.domain.lower() == 'medical':
		create_medical_departments()
		create_antibiotics()
		create_test_uom()
		create_duration()
		#create_dosage()
		create_lab_test_items()
		create_lab_test_template()

	if args.get('setup_website'):
		website_maker(args)

	create_logo(args)

	frappe.local.message_log = []
	setup_domain(args.get('domain'))

	frappe.db.commit()
	login_as_first_user(args)

	frappe.db.commit()
	frappe.clear_cache()

	if args.get("add_sample_data"):
		try:
			make_sample_data(args)
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
			'company_name':args.get('company_name').strip(),
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
		'company': args.get('company_name').strip(),
		'price_list': frappe.db.get_value("Price List", {"selling": 1}),
		'default_customer_group': _("Individual"),
		'quotation_series': "QTN-",
	}).insert()

def create_bank_account(args):
	if args.get("bank_account"):
		company_name = args.get('company_name').strip()
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
			make_tax_account_and_template(args.get("company_name").strip(),
				tax_data.get('account_name'), tax_data.get('tax_rate'), sales_tax)

def get_country_wise_tax(country):
	data = {}
	with open (os.path.join(os.path.dirname(__file__), "data", "country_wise_tax.json")) as countrywise_tax:
		data = json.load(countrywise_tax).get(country)

	return data

def create_taxes(args):
	for i in xrange(1,6):
		if args.get("tax_" + str(i)):
			# replace % in case someone also enters the % symbol
			tax_rate = cstr(args.get("tax_rate_" + str(i)) or "").replace("%", "")
			account_name = args.get("tax_" + str(i))

			make_tax_account_and_template(args.get("company_name").strip(), account_name, tax_rate)

def make_tax_account_and_template(company, account_name, tax_rate, template_name=None):
	try:
		account = make_tax_account(company, account_name, tax_rate)
		if account:
			make_sales_and_purchase_tax_templates(account, template_name)
	except frappe.NameError, e:
		if e.args[2][0]==1062:
			pass
		else:
			raise
	except RootNotEditable, e:
		pass

def get_tax_account_group(company):
	tax_group = frappe.db.get_value("Account",
		{"account_name": "Duties and Taxes", "is_group": 1, "company": company})
	if not tax_group:
		tax_group = frappe.db.get_value("Account", {"is_group": 1, "root_type": "Liability",
				"account_type": "Tax", "company": company})

	return tax_group

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

def make_sales_and_purchase_tax_templates(account, template_name=None):
	if not template_name:
		template_name = account.name

	sales_tax_template = {
		"doctype": "Sales Taxes and Charges Template",
		"title": template_name,
		"company": account.company,
		"taxes": [{
			"category": "Valuation and Total",
			"charge_type": "On Net Total",
			"account_head": account.name,
			"description": "{0} @ {1}".format(account.account_name, account.tax_rate),
			"rate": account.tax_rate
		}]
	}

	# Sales
	frappe.get_doc(copy.deepcopy(sales_tax_template)).insert(ignore_permissions=True)

	# Purchase
	purchase_tax_template = copy.deepcopy(sales_tax_template)
	purchase_tax_template["doctype"] = "Purchase Taxes and Charges Template"
	frappe.get_doc(purchase_tax_template).insert(ignore_permissions=True)

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

			try:
				frappe.get_doc({
					"doctype":"Item",
					"item_code": item,
					"item_name": item,
					"description": item,
					"show_in_website": 1,
					"is_sales_item": is_sales_item,
					"is_purchase_item": is_purchase_item,
					"is_stock_item": is_stock_item and 1 or 0,
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
				doc = frappe.get_doc({
					"doctype":"Customer",
					"customer_name": customer,
					"customer_type": "Company",
					"customer_group": _("Commercial"),
					"territory": args.get("country"),
					"company": args.get("company_name").strip()
				}).insert()

				if args.get("customer_contact_" + str(i)):
					create_contact(args.get("customer_contact_" + str(i)),
						"Customer", doc.name)
			except frappe.NameError:
				pass

def create_suppliers(args):
	for i in xrange(1,6):
		supplier = args.get("supplier_" + str(i))
		if supplier:
			try:
				doc = frappe.get_doc({
					"doctype":"Supplier",
					"supplier_name": supplier,
					"supplier_type": _("Local"),
					"company": args.get("company_name").strip()
				}).insert()

				if args.get("supplier_contact_" + str(i)):
					create_contact(args.get("supplier_contact_" + str(i)),
						"Supplier", doc.name)
			except frappe.NameError:
				pass

def create_contact(contact, party_type, party):
	"""Create contact based on given contact name"""
	contact = contact.strip().split(" ")

	contact = frappe.get_doc({
		"doctype":"Contact",
		"first_name":contact[0],
		"last_name": len(contact) > 1 and contact[1] or ""
	})
	contact.append('links', dict(link_doctype=party_type, link_name=party))
	contact.insert()

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
					"employee_name": fullname,
					"user_id": email,
					"status": "Active",
					"company": args.get("company_name")
				})
				emp.flags.ignore_mandatory = True
				emp.insert(ignore_permissions = True)

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

def create_program(args):
	for i in xrange(1,6):
		if args.get("program_" + str(i)):
			program = frappe.new_doc("Program")
			program.program_name = args.get("program_" + str(i))
			try:
				program.save()
			except frappe.DuplicateEntryError:
				pass

def create_course(args):
	for i in xrange(1,6):
		if args.get("course_" + str(i)):
			course = frappe.new_doc("Course")
			course.course_name = args.get("course_" + str(i))
			try:
				course.save()
			except frappe.DuplicateEntryError:
				pass

def create_instructor(args):
	for i in xrange(1,6):
		if args.get("instructor_" + str(i)):
			instructor = frappe.new_doc("Instructor")
			instructor.instructor_name = args.get("instructor_" + str(i))
			try:
				instructor.save()
			except frappe.DuplicateEntryError:
				pass

def create_room(args):
	for i in xrange(1,6):
		if args.get("room_" + str(i)):
			room = frappe.new_doc("Room")
			room.room_name = args.get("room_" + str(i))
			room.seating_capacity = args.get("room_capacity_" + str(i))
			try:
				room.save()
			except frappe.DuplicateEntryError:
				pass

def create_medical_departments():
	depts = ["Accident and emergency care" ,"Anaesthetics", "Biochemistry", "Cardiology", "Dermatology",
				"Diagnostic imaging", "ENT", "Gastroenterology", "General Surgery", "Gynaecology",
				"Haematology", "Maternity", "Microbiology", "Nephrology", "Neurology", "Oncology",
				 "Orthopaedics", "Pathology", "Physiotherapy", "Rheumatology", "Serology", "Urology"]
	for d in depts:
		mediacal_department = frappe.new_doc("Medical Department")
		mediacal_department.department = d
		try:
			mediacal_department.save()
		except frappe.DuplicateEntryError:
			pass

def create_antibiotics():
	abt = ["Amoxicillin", "Ampicillin", "Bacampicillin", "Carbenicillin", "Cloxacillin", "Dicloxacillin",
	 "Flucloxacillin", "Mezlocillin", "Nafcillin", "Oxacillin", "Penicillin G", "Penicillin V",
	 "Piperacillin", "Pivampicillin", "Pivmecillinam", "Ticarcillin", "Cefacetrile (cephacetrile)",
	 "Cefadroxil (cefadroxyl)", "Cefalexin (cephalexin)", "Cefaloglycin (cephaloglycin)",
	 "Cefalonium (cephalonium)", "Cefaloridine (cephaloradine)", "Cefalotin (cephalothin)",
	 "Cefapirin (cephapirin)", "Cefatrizine", "Cefazaflur", "Cefazedone", "Cefazolin (cephazolin)",
	 "Cefradine (cephradine)", "Cefroxadine", "Ceftezole", "Cefaclor", "Cefamandole", "Cefmetazole",
	 "Cefonicid", "Cefotetan", "Cefoxitin", "Cefprozil (cefproxil)", "Cefuroxime", "Cefuzonam",
	 "Cefcapene", "Cefdaloxime", "Cefdinir", "Cefditoren", "Cefetamet", "Cefixime", "Cefmenoxime",
	 "Cefodizime", "Cefotaxime", "Cefpimizole", "Cefpodoxime", "Cefteram", "Ceftibuten", "Ceftiofur",
	 "Ceftiolene", "Ceftizoxime", "Ceftriaxone", "Cefoperazone", "Ceftazidime", "Cefclidine", "Cefepime",
	 "Cefluprenam", "Cefoselis", "Cefozopran", "Cefpirome", "Cefquinome", "Ceftobiprole", "Ceftaroline",
	 "Cefaclomezine","Cefaloram", "Cefaparole", "Cefcanel", "Cefedrolor", "Cefempidone", "Cefetrizole",
	 "Cefivitril", "Cefmatilen", "Cefmepidium", "Cefovecin", "Cefoxazole", "Cefrotil", "Cefsumide",
	 "Cefuracetime", "Ceftioxide", "Ceftazidime/Avibactam", "Ceftolozane/Tazobactam", "Aztreonam",
	 "Imipenem", "Imipenem/cilastatin", "Doripenem", "Meropenem", "Ertapenem", "Azithromycin",
	 "Erythromycin", "Clarithromycin", "Dirithromycin", "Roxithromycin", "Telithromycin", "Clindamycin",
	 "Lincomycin", "Pristinamycin", "Quinupristin/dalfopristin", "Amikacin", "Gentamicin", "Kanamycin",
	 "Neomycin", "Netilmicin", "Paromomycin", "Streptomycin", "Tobramycin", "Flumequine", "Nalidixic acid",
	 "Oxolinic acid", "Piromidic acid", "Pipemidic acid", "Rosoxacin", "Ciprofloxacin", "Enoxacin",
	 "Lomefloxacin", "Nadifloxacin", "Norfloxacin", "Ofloxacin", "Pefloxacin", "Rufloxacin", "Balofloxacin",
	 "Gatifloxacin", "Grepafloxacin", "Levofloxacin", "Moxifloxacin", "Pazufloxacin", "Sparfloxacin",
	 "Temafloxacin", "Tosufloxacin", "Besifloxacin", "Clinafloxacin", "Gemifloxacin",
	 "Sitafloxacin", "Trovafloxacin", "Prulifloxacin", "Sulfamethizole", "Sulfamethoxazole",
	 "Sulfisoxazole", "Trimethoprim-Sulfamethoxazole", "Demeclocycline", "Doxycycline", "Minocycline",
	 "Oxytetracycline", "Tetracycline", "Tigecycline", "Chloramphenicol", "Metronidazole",
	 "Tinidazole", "Nitrofurantoin", "Vancomycin", "Teicoplanin", "Telavancin", "Linezolid",
	 "Cycloserine 2", "Rifampin", "Rifabutin", "Rifapentine", "Rifalazil", "Bacitracin", "Polymyxin B",
	 "Viomycin", "Capreomycin"]
	for a in abt:
		antibiotics = frappe.new_doc("Antibiotics")
		antibiotics.antibiotic_name = a
		try:
			antibiotics.save()
		except frappe.DuplicateEntryError:
			pass

def create_test_uom():
	records = [
		{"doctype": "Lab Test UOM", "name": "umol/L", "test_uom": "umol/L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mg/L", "test_uom": "mg/L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mg / dl", "test_uom": "mg / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "pg / ml", "test_uom": "pg / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "U/ml", "test_uom": "U/ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "/HPF", "test_uom": "/HPF", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Million Cells / cumm", "test_uom": "Million Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Lakhs Cells / cumm", "test_uom": "Lakhs Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "U / L", "test_uom": "U / L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "g / L", "test_uom": "g / L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "IU / ml", "test_uom": "IU / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "gm %", "test_uom": "gm %", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Microgram", "test_uom": "Microgram", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Micron", "test_uom": "Micron", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Cells / cumm", "test_uom": "Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "%", "test_uom": "%", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mm / dl", "test_uom": "mm / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mm / hr", "test_uom": "mm / hr", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ulU / ml", "test_uom": "ulU / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ng / ml", "test_uom": "ng / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ng / dl", "test_uom": "ng / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ug / dl", "test_uom": "ug / dl", "uom_description": None }
	]

	insert_record(records)

def create_duration():
	records = [
		{"doctype": "Duration", "name": "3 Month", "number": "3", "period": "Month" },
		{"doctype": "Duration", "name": "2 Month", "number": "2", "period": "Month" },
		{"doctype": "Duration", "name": "1 Month", "number": "1", "period": "Month" },
		{"doctype": "Duration", "name": "12 Hour", "number": "12", "period": "Hour" },
		{"doctype": "Duration", "name": "11 Hour", "number": "11", "period": "Hour" },
		{"doctype": "Duration", "name": "10 Hour", "number": "10", "period": "Hour" },
		{"doctype": "Duration", "name": "9 Hour", "number": "9", "period": "Hour" },
		{"doctype": "Duration", "name": "8 Hour", "number": "8", "period": "Hour" },
		{"doctype": "Duration", "name": "7 Hour", "number": "7", "period": "Hour" },
		{"doctype": "Duration", "name": "6 Hour", "number": "6", "period": "Hour" },
		{"doctype": "Duration", "name": "5 Hour", "number": "5", "period": "Hour" },
		{"doctype": "Duration", "name": "4 Hour", "number": "4", "period": "Hour" },
		{"doctype": "Duration", "name": "3 Hour", "number": "3", "period": "Hour" },
		{"doctype": "Duration", "name": "2 Hour", "number": "2", "period": "Hour" },
		{"doctype": "Duration", "name": "1 Hour", "number": "1", "period": "Hour" },
		{"doctype": "Duration", "name": "5 Week", "number": "5", "period": "Week" },
		{"doctype": "Duration", "name": "4 Week", "number": "4", "period": "Week" },
		{"doctype": "Duration", "name": "3 Week", "number": "3", "period": "Week" },
		{"doctype": "Duration", "name": "2 Week", "number": "2", "period": "Week" },
		{"doctype": "Duration", "name": "1 Week", "number": "1", "period": "Week" },
		{"doctype": "Duration", "name": "6 Day", "number": "6", "period": "Day" },
		{"doctype": "Duration", "name": "5 Day", "number": "5", "period": "Day" },
		{"doctype": "Duration", "name": "4 Day", "number": "4", "period": "Day" },
		{"doctype": "Duration", "name": "3 Day", "number": "3", "period": "Day" },
		{"doctype": "Duration", "name": "2 Day", "number": "2", "period": "Day" },
		{"doctype": "Duration", "name": "1 Day", "number": "1", "period": "Day" }
	]
	insert_record(records)

def create_dosage():
	records = [
		{"doctype": "Dosage", "name": "1-1-1-1", "dosage": "1-1-1-1","dosage_strength":
		[{"strength": "1.0","time": "9:00:00"}, {"strength": "1.0","time": "13:00:00"},{"strength": "1.0","time": "17:00:00"},{"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "0-0-1", "dosage": "0-0-1","dosage_strength":
		[{"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "1-0-0", "dosage": "1-0-0","dosage_strength":
		[{"strength": "1.0","time": "9:00:00"}]
		},
		{"doctype": "Dosage", "name": "0-1-0", "dosage": "0-1-0","dosage_strength":
		[{"strength": "1.0","time": "14:00:00"}]
		},
		{"doctype": "Dosage", "name": "1-1-1", "dosage": "1-1-1","dosage_strength":
		[{"strength": "1.0","time": "9:00:00"}, {"strength": "1.0","time": "14:00:00"},{"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "1-0-1", "dosage": "1-0-1","dosage_strength":
		[{"strength": "1.0","time": "9:00:00"}, {"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "Once Bedtime", "dosage": "Once Bedtime","dosage_strength":
		[{"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "5 times a day", "dosage": "5 times a day","dosage_strength":
		[{"strength": "1.0","time": "5:00:00"}, {"strength": "1.0","time": "9:00:00"}, {"strength": "1.0","time": "13:00:00"},{"strength": "1.0","time": "17:00:00"},{"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "QID", "dosage": "QID","dosage_strength":
		[{"strength": "1.0","time": "9:00:00"}, {"strength": "1.0","time": "13:00:00"},{"strength": "1.0","time": "17:00:00"},{"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "TID", "dosage": "TID","dosage_strength":
		[{"strength": "1.0","time": "9:00:00"}, {"strength": "1.0","time": "14:00:00"},{"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "BID", "dosage": "BID","dosage_strength":
		[{"strength": "1.0","time": "9:00:00"}, {"strength": "1.0","time": "21:00:00"}]
		},
		{"doctype": "Dosage", "name": "Once Daily", "dosage": "Once Daily","dosage_strength":
		[{"strength": "1.0","time": "9:00:00"}]
		}
	]
	insert_record(records)

def create_lab_test_items():
	records = [
		{'doctype': 'Item Group', 'item_group_name': _('Laboratory'),
			'is_group': 0, 'parent_item_group': _('All Item Groups') },

		{"doctype": "Item", "item_code": "MCH", "item_name": "MCH", "item_group": "Laboratory",
			"stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "LDL", "item_name": "LDL", "item_group": "Laboratory",
			"stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "GTT", "item_name": "GTT", "item_group": "Laboratory",
			"stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "HDL", "item_name": "HDL", "item_group": "Laboratory",
			"stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "BILT", "item_name": "BILT", "item_group": "Laboratory",
			"stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "BILD", "item_name": "BILD", "item_group": "Laboratory",
			"stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "BP", "item_name": "BP", "item_group": "Laboratory",
			"stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "BS", "item_name": "BS", "item_group": "Laboratory",
			"stock_uom": "Unit", "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1}
	]
	insert_record(records)

def create_lab_test_template():
	records = [
		{'doctype': 'Service Type', 'service_type': _('Laboratory')},

		{"doctype": "Lab Test Template", "name": "MCH","test_name": "MCH","test_code": "MCH",
		"test_group": "Laboratory","service_type": "Laboratory","department": "Haematology","item": "MCH",
		"test_template_type": "Single","is_billable": 1,"test_rate": 0.0,"test_uom": "Microgram",
		"test_normal_range": "27 - 32 Microgram",
		"sensitivity": 0,"test_description": "Mean Corpuscular Hemoglobin"},
		{"doctype": "Lab Test Template", "name": "LDL","test_name": "LDL (Serum)","test_code": "LDL",
		"test_group": "Laboratory","service_type": "Laboratory","department": "Biochemistry",
		"item": "LDL","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "70 - 160 mg/dlLow-density Lipoprotein (LDL)",
		"sensitivity": 0,"test_description": "Low-density Lipoprotein (LDL)"},
		{"doctype": "Lab Test Template", "name": "GTT","test_name": "GTT","test_code": "GTT",
		"test_group": "Laboratory","service_type": "Laboratory","department": "Haematology",
		"item": "GTT","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "Less than 85 mg/dl",
		"sensitivity": 0,"test_description": "Glucose Tolerance Test"},
		{"doctype": "Lab Test Template", "name": "HDL","test_name": "HDL (Serum)","test_code": "HDL",
		"test_group": "Laboratory","service_type": "Laboratory","department": "Biochemistry",
		"item": "HDL","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "35 - 65 mg/dl",
		"sensitivity": 0,"test_description": "High-density Lipoprotein (HDL)"},
		{"doctype": "Lab Test Template", "name": "BILT","test_name": "Bilirubin Total","test_code": "BILT",
		"test_group": "Laboratory","service_type": "Laboratory","department": "Biochemistry",
		"item": "BILT","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "0.2 - 1.2 mg / dl",
		"sensitivity": 0,"test_description": "Bilirubin Total"},
		{"doctype": "Lab Test Template", "name": "BILD","test_name": "Bilirubin Direct","test_code": "BILD",
		"test_group": "Laboratory","service_type": "Laboratory","department": "Biochemistry",
		"item": "BILD","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "0.4 mg / dl",
		"sensitivity": 0,"test_description": "Bilirubin Direct"},

		{"doctype": "Lab Test Template", "name": "BP","test_name": "Bile Pigment","test_code": "BP",
		"test_group": "Laboratory","service_type": "Laboratory","department": "Pathology",
		"item": "BP","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "","test_normal_range": "",
		"sensitivity": 0,"test_description": "Bile Pigment"},
		{"doctype": "Lab Test Template", "name": "BS","test_name": "Bile Salt","test_code": "BS",
		"test_group": "Laboratory","service_type": "Laboratory","department": "Pathology",
		"item": "BS","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "","test_normal_range": "",
		"sensitivity": 0,"test_description": "Bile Salt"}
	]
	insert_record(records)

def insert_record(records):
	for r in records:
		doc = frappe.new_doc(r.get("doctype"))
		doc.update(r)
		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError, e:
			# pass DuplicateEntryError and continue
			if e.args and e.args[0]==doc.doctype and e.args[1]==doc.name:
				# make sure DuplicateEntryError is for the exact same doc and not a related doc
				pass
			else:
				raise
