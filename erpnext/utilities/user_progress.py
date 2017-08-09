# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext

import json, copy
from frappe import _
from frappe.utils import cstr, flt
from frappe.utils.file_manager import save_file
from erpnext.accounts.doctype.account.account import RootNotEditable

def get_slide_settings():
	defaults = frappe.defaults.get_defaults()
	domain = frappe.db.get_value('Company', erpnext.get_default_company(), 'domain')
	company = defaults.get("company") or ''
	return [
		frappe._dict(
			name='Brand',
			route=["Form", "Company", company],
			icon="fa fa-bookmark",
			title=_("Add Your Company") if domain != 'Education' else _("Add Your Institution"),
			done=1,
			help=_('Setup your ' + ('company' if domain != 'Education' else 'institution') + ' and brand.'),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			fields=[]
		),
		frappe._dict(
			name='Customers',
			doctype='Customer',
			domains=('Manufacturing', 'Services', 'Retail', 'Distribution'),
			icon="fa fa-group",
			title=_("Add Customers"),
			help=_("List a few of your customers. They could be organizations or individuals."),
			image_src="/assets/erpnext/images/illustrations/shop2.jpg",
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_customers",
			fields=[
				{"fieldtype":"Section Break"},
				{"fieldtype":"Data", "fieldname":"customer", "label":_("Customer"),
					"placeholder":_("Customer Name")},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Data", "fieldname":"customer_contact",
					"label":_("Contact Name"), "placeholder":_("Contact Name")}
			]
		),
		frappe._dict(
			name='Suppliers',
			doctype='Supplier',
			domains=('Manufacturing', 'Services', 'Retail', 'Distribution'),
			icon="fa fa-group",
			title=_("Your Suppliers"),
			help=_("List a few of your suppliers. They could be organizations or individuals."),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_suppliers",
			fields=[
				{"fieldtype":"Section Break"},
				{"fieldtype":"Data", "fieldname":"supplier", "label":_("Supplier"),
					"placeholder":_("Supplier Name")},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Data", "fieldname":"supplier_contact",
					"label":_("Contact Name"), "placeholder":_("Contact Name")},
			]
		),
		frappe._dict(
			name='Taxes',
			route=["Form", "Company", company],
			domains=('Manufacturing', 'Services', 'Retail', 'Distribution'),
			icon="fa fa-money",
			title=_("Add Taxes"),
			help=_("List your tax heads (e.g. VAT, Customs etc; they should have unique names) and their standard rates. This will create a standard template, which you can edit and add more later."),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			add_more=1,
			max_count=3,
			mandatory_entry=0,
			method="erpnext.utilities.user_progress.create_taxes",
			fields=[
				{"fieldtype":"Section Break"},
				{"fieldtype":"Data", "fieldname":"tax", "label":_("Tax"),
					"placeholder":_("e.g. VAT")},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Float", "fieldname":"tax_rate", "label":_("Rate (%)"), "placeholder":_("e.g. 5")}
			]
		),
		frappe._dict(
			name='Products',
			doctype='Item',
			domains=['Manufacturing', 'Services', 'Retail', 'Distribution'],
			icon="fa fa-barcode",
			title=_("Your Products or Services"),
			help=_("List your products or services that you buy or sell. Make sure to check the Item Group, Unit of Measure and other properties when you start."),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_items",
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"item", "label":_("Item"),
					"placeholder":_("A Product or Service")},
				{"fieldtype":"Select", "label":_("Group"), "fieldname":"item_group",
					"options":[_("Products"), _("Services"),
						_("Raw Material"), _("Consumable"), _("Sub Assemblies")],
					"default": _("Products"), "static": 1},
				{"fieldtype":"Select", "fieldname":"item_uom", "label":_("UOM"),
					"options":[_("Unit"), _("Nos"), _("Box"), _("Pair"), _("Kg"), _("Set"),
						_("Hour"), _("Minute"), _("Litre"), _("Meter"), _("Gram")],
					"default": _("Unit"), "static": 1},
				{"fieldtype": "Check", "fieldname": "is_sales_item",
					"label":_("We sell this Item"), "default": 1, "static": 1},
				{"fieldtype": "Check", "fieldname": "is_purchase_item",
					"label":_("We buy this Item"), "default": 1, "static": 1},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Currency", "fieldname":"item_price", "label":_("Rate"), "static": 1},
				{"fieldtype":"Attach Image", "fieldname":"item_img", "label":_("Attach Image"), "is_private": 0, "static": 1},
			]
		),
		frappe._dict(
			name='Sales Target',
			route=["Form", "Company", company],
			domains=['Manufacturing', 'Services', 'Retail', 'Distribution'],
			title=_("Set your Target"),
			help=_("Set a sales target you'd like to achieve for your company " + company),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			method="erpnext.utilities.user_progress.set_sales_target",
			fields=[
				{"fieldtype":"Currency", "fieldname":"monthly_sales_target", "label":_("Monthly Sales Target")},
			]
		),
		frappe._dict(
			name='Program',
			doctype='Program',
			domains=("Education"),
			title=_("Program"),
			help=_("Example: Masters in Computer Science"),
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_program",
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"program", "label":_("Program"), "placeholder": _("Program Name")},
			]
		),
		frappe._dict(
			name='Courses',
			doctype='Course',
			domains=["Education"],
			title=_("Course"),
			help=_("Example: Basic Mathematics"),
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_course",
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"course", "label":_("Course"),  "placeholder": _("Course Name")},
			]
		),
		frappe._dict(
			name='Instructors',
			doctype='Instructor',
			domains=["Education"],
			title=_("Instructor"),
			help=_("People who teach at your organisation"),
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_instructor",
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"instructor", "label":_("Instructor"),  "placeholder": _("Instructor Name")},
			]
		),
		frappe._dict(
			name='Rooms',
			doctype='Room',
			domains=["Education"],
			title=_("Room"),
			help=_("Classrooms/ Laboratories etc where lectures can be scheduled."),
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_room",
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"room", "label":_("Room")},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Int", "fieldname":"room_capacity", "label":_("Room") + " Capacity", "static": 1},
			]
		)
	]

def get_user_progress_slides():
	slides = []
	slide_settings = get_slide_settings()

	domain = frappe.db.get_value('Company', erpnext.get_default_company(), 'domain')

	for s in slide_settings:
		if not s.domains or (domain and domain in s.domains):
			if(s.doctype):
				s.doc_count = frappe.db.count(s.doctype)
			if not s.done:
				s.done = 1 if s.doc_count else 0
			slides.append(s)

	return slides

@frappe.whitelist()
def create_customers(args_data):
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
		customer = args.get("customer_" + str(i))
		if customer:
			try:
				doc = frappe.get_doc({
					"doctype":"Customer",
					"customer_name": customer,
					"customer_type": "Company",
					"customer_group": _("Commercial"),
					"territory": defaults.get("country"),
					"company": defaults.get("company")
				}).insert()

				if args.get("customer_contact_" + str(i)):
					create_contact(args.get("customer_contact_" + str(i)),
						"Customer", doc.name)
			except frappe.NameError:
				pass

@frappe.whitelist()
def create_suppliers(args_data):
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
		supplier = args.get("supplier_" + str(i))
		if supplier:
			try:
				doc = frappe.get_doc({
					"doctype":"Supplier",
					"supplier_name": supplier,
					"supplier_type": _("Local"),
					"company": defaults.get("company")
				}).insert()

				if args.get("supplier_contact_" + str(i)):
					create_contact(args.get("supplier_contact_" + str(i)),
						"Supplier", doc.name)
			except frappe.NameError:
				pass

def create_contact(contact, party_type, party):
	"""Create contact based on given contact name"""
	contact = contact	.split(" ")

	contact = frappe.get_doc({
		"doctype":"Contact",
		"first_name":contact[0],
		"last_name": len(contact) > 1 and contact[1] or ""
	})
	contact.append('links', dict(link_doctype=party_type, link_name=party))
	contact.insert()

@frappe.whitelist()
def create_items(args_data):
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
		item = args.get("item_" + str(i))
		if item:
			item_group = _(args.get("item_group_" + str(i)))
			is_sales_item = args.get("is_sales_item_" + str(i))
			is_purchase_item = args.get("is_purchase_item_" + str(i))
			is_stock_item = item_group!=_("Services")
			default_warehouse = ""
			if is_stock_item:
				default_warehouse = frappe.db.get_value("Warehouse", filters={
					"warehouse_name": _("Finished Goods") if is_sales_item else _("Stores"),
					"company": defaults.get("company_name")
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
					"stock_uom": _(args.get("item_uom_" + str(i))),
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

@frappe.whitelist
def create_taxes(args_data):
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
		if args.get("tax_" + str(i)):
			# replace % in case someone also enters the % symbol
			tax_rate = cstr(args.get("tax_rate_" + str(i)) or "").replace("%", "")
			account_name = args.get("tax_" + str(i))

			make_tax_account_and_template(defaults.get("company_name")	, account_name, tax_rate)

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

def get_tax_account_group(company):
	tax_group = frappe.db.get_value("Account",
		{"account_name": "Duties and Taxes", "is_group": 1, "company": company})
	if not tax_group:
		tax_group = frappe.db.get_value("Account", {"is_group": 1, "root_type": "Liability",
				"account_type": "Tax", "company": company})

	return tax_group

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

# Tax utils end

@frappe.whitelist
def set_sales_target(args_data):
	args = json.loads(args_data)
	frappe.set_value("Company", erpnext.get_default_company(), "monthly_sales_target", args.get('monthly_sales_target'))

# Schools
@frappe.whitelist
def create_program(args_data):
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
		if args.get("program_" + str(i)):
			program = frappe.new_doc("Program")
			program.program_code = args.get("program_" + str(i))
			program.program_name = args.get("program_" + str(i))
			try:
				program.save()
			except frappe.DuplicateEntryError:
				pass

@frappe.whitelist
def create_course(args_data):
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
		if args.get("course_" + str(i)):
			course = frappe.new_doc("Course")
			course.course_code = args.get("course_" + str(i))
			course.course_name = args.get("course_" + str(i))
			try:
				course.save()
			except frappe.DuplicateEntryError:
				pass

@frappe.whitelist
def create_instructor(args_data):
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
		if args.get("instructor_" + str(i)):
			instructor = frappe.new_doc("Instructor")
			instructor.instructor_name = args.get("instructor_" + str(i))
			try:
				instructor.save()
			except frappe.DuplicateEntryError:
				pass

@frappe.whitelist
def create_room(args_data):
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
		if args.get("room_" + str(i)):
			room = frappe.new_doc("Room")
			room.room_name = args.get("room_" + str(i))
			room.seating_capacity = args.get("room_capacity_" + str(i))
			try:
				room.save()
			except frappe.DuplicateEntryError:
				pass

