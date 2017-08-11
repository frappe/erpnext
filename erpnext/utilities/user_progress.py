# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext

import json
from frappe import _
from frappe.utils import flt
from frappe.utils.file_manager import save_file

def get_slide_settings():
	defaults = frappe.defaults.get_defaults()
	domain = frappe.db.get_value('Company', erpnext.get_default_company(), 'domain')
	company = defaults.get("company") or ''
	currency = defaults.get("currency") or ''
	return [
		frappe._dict(
			name='Company',
			route=["Form", "Company", company],
			icon="fa fa-bookmark",
			title=_("Add Your Company") if domain != 'Education' else _("Add Your Institution"),
			help=_('Setup your ' + ('company' if domain != 'Education' else 'institution') + ' and brand.'),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			fields=[]
		),
		frappe._dict(
			name='Customers',
			doctype='Customer',
			# sec_doctype="Contact",
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
			# sec_doctype="Contact",
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
			name='Products',
			doctype='Item',
			domains=['Manufacturing', 'Services', 'Retail', 'Distribution'],
			icon="fa fa-barcode",
			title=_("Your Products or Services"),
			help=_("List your products or services that you buy or sell."),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_items",
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"item", "label":_("Item"),
					"placeholder":_("A Product")},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Select", "fieldname":"item_uom", "label":_("UOM"),
					"options":[_("Unit"), _("Nos"), _("Box"), _("Pair"), _("Kg"), _("Set"),
						_("Hour"), _("Minute"), _("Litre"), _("Meter"), _("Gram")],
					"default": _("Unit"), "static": 1},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Currency", "fieldname":"item_price", "label":_("Rate"), "static": 1}
			]
		),
		frappe._dict(
			name='Sales Target',
			route=["Form", "Company", company],
			domains=['Manufacturing', 'Services', 'Retail', 'Distribution'],
			title=_("Set your Target"),
			help=_("Set a sales target you'd like to achieve for your company " + company),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.set_sales_target",
			fields=[
				{"fieldtype":"Currency", "fieldname":"monthly_sales_target",
				"label":_("Monthly Sales Target (" + currency + ")")},
			]
		),

		# School slides begin
		frappe._dict(
			name='Programs',
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
				{"fieldtype":"Int", "fieldname":"room_capacity", "label":_("Room Capacity"), "static": 1},
			]
		),
		# School slides end

		frappe._dict(
			name='Users',
			doctype='User',
			sec_doctype="Employee",
			title=_("Add Users"),
			help=_("Add users to your organization, other than yourself."),
			image_src="/assets/erpnext/images/illustrations/shop.jpg",
			add_more=1,
			max_count=3,
			mandatory_entry=1,
			method="erpnext.utilities.user_progress.create_users",
			fields=[
				{"fieldtype":"Section Break"},
				{"fieldtype":"Data", "fieldname":"user_email", "label":_("Email ID"),
					"placeholder":_("user@example.com"), "options": "Email", "static": 1},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Data", "fieldname":"user_fullname",
					"label":_("Full Name"), "static": 1},
			]
		)
	]

def get_user_progress_slides():
	slides = []
	slide_settings = get_slide_settings()

	domain = frappe.db.get_value('Company', erpnext.get_default_company(), 'domain')

	for s in slide_settings:
		if not s.domains or (domain and domain in s.domains):
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
			default_warehouse = ""
			default_warehouse = frappe.db.get_value("Warehouse", filters={
				"warehouse_name": _("Finished Goods"),
				"company": defaults.get("company_name")
			})

			try:
				frappe.get_doc({
					"doctype":"Item",
					"item_code": item,
					"item_name": item,
					"description": item,
					"show_in_website": 1,
					"is_sales_item": 1,
					"is_purchase_item": 1,
					"is_stock_item": 1,
					"item_group": "Products",
					"stock_uom": _(args.get("item_uom_" + str(i))),
					"default_warehouse": default_warehouse
				}).insert()

				if args.get("item_price_" + str(i)):
					item_price = flt(args.get("item_price_" + str(i)))

					price_list_name = frappe.db.get_value("Price List", {"selling": 1})
					make_item_price(item, price_list_name, item_price)
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

@frappe.whitelist()
def set_sales_target(args_data):
	args = json.loads(args_data)
	frappe.db.set_value("Company", erpnext.get_default_company(), "monthly_sales_target", args.get('monthly_sales_target'))

# Schools
@frappe.whitelist()
def create_program(args_data):
	args = json.loads(args_data)
	for i in xrange(1,4):
		if args.get("program_" + str(i)):
			program = frappe.new_doc("Program")
			program.program_code = args.get("program_" + str(i))
			program.program_name = args.get("program_" + str(i))
			try:
				program.save()
			except frappe.DuplicateEntryError:
				pass

@frappe.whitelist()
def create_course(args_data):
	args = json.loads(args_data)
	for i in xrange(1,4):
		if args.get("course_" + str(i)):
			course = frappe.new_doc("Course")
			course.course_code = args.get("course_" + str(i))
			course.course_name = args.get("course_" + str(i))
			try:
				course.save()
			except frappe.DuplicateEntryError:
				pass

@frappe.whitelist()
def create_instructor(args_data):
	args = json.loads(args_data)
	for i in xrange(1,4):
		if args.get("instructor_" + str(i)):
			instructor = frappe.new_doc("Instructor")
			instructor.instructor_name = args.get("instructor_" + str(i))
			try:
				instructor.save()
			except frappe.DuplicateEntryError:
				pass

@frappe.whitelist()
def create_room(args_data):
	args = json.loads(args_data)
	for i in xrange(1,4):
		if args.get("room_" + str(i)):
			room = frappe.new_doc("Room")
			room.room_name = args.get("room_" + str(i))
			room.seating_capacity = args.get("room_capacity_" + str(i))
			try:
				room.save()
			except frappe.DuplicateEntryError:
				pass

@frappe.whitelist()
def create_users(args_data):
	if frappe.session.user == 'Administrator':
		return
	args = json.loads(args_data)
	defaults = frappe.defaults.get_defaults()
	for i in xrange(1,4):
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
			user.flags.delay_emails = True

			if not frappe.db.get_value("User", email):
				user.insert(ignore_permissions=True)

				# create employee
				emp = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": fullname,
					"user_id": email,
					"status": "Active",
					"company": defaults.get("company")
				})
				emp.flags.ignore_mandatory = True
				emp.insert(ignore_permissions = True)
