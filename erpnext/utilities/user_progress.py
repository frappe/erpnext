# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext
from frappe import _
from erpnext.setup.doctype.setup_progress.setup_progress import get_action_completed_state

def get_slide_settings():
	defaults = frappe.defaults.get_defaults()
	domain = frappe.db.get_value('Company', erpnext.get_default_company(), 'domain')
	company = defaults.get("company") or ''
	# Initial state of slides
	return [
		frappe._dict(
			action_name='Add Company',
			title=_("Add Your Company") if domain != 'Education' else _("Add Your Institution"),
			help=_('Setup your ' + ('company' if domain != 'Education' else 'institution') + ' and brand.'),
			# image_src="/assets/erpnext/images/illustrations/shop.jpg",
			fields=[],
			action_cards=[
				{
					"action_name": "Make Company",
					"title": _("You added " +  company),
					"title_route": ["Form", "Company", company],
					"done": 1
					# "actions": [{
					# 	"label": _("View " + company),
					# 	"route":
					# }]
				},
				# {
				# 	"action_name": "Watch Accounts Opening Balance",
				# 	"title": _("Accounts Opening Balance"),
				# 	"title_link": _("Company"),
				# 	"content": _("Set an opening balance in Accounts."),
				# 	"video_id": "U5wPIvEn-0c"
				# },
				{
					"action_name": "Review Chart of Accounts",
					"title": _("Review Chart of Accounts"),
					"title_route": ["Tree", "Account"],
					# "content": _("Review the Chart of Accounts, update your opening balance and more"),
					# "actions": [{
					# 	"label": _("View Chart of Accounts"),
					# 	"route": ["Tree", "Account"]
					# }],
					"help_links": [{
						"label": _('Need help?'),
						"url": ["https://erpnext.org/docs/user/manual/en/accounts"]
					},
					{
						"label": _('Set an Opening Balance'),
						"video_id": "U5wPIvEn-0c"
					}

					]
				},
				{
					"action_name": "Set Sales Target",
					"title": _("Set a Sales Target"),
					"title_route": ["Form", "Company", company],
					# "content": _("Set a monthly sales goal that you'd like to achieve for your company " + company +
					# 	"."),
					# "actions": [{
					# 	"label": _('Set a monthly target'),
					# 	"route": ["Form", "Company", company]
					# }],
					"help_links": [{
						"label": _('Need help?'),
						"url": ["https://erpnext.org/docs/user/manual/en/setting-up/setting-company-sales-goal"]
					}]
				}
			]
		)
		,
		frappe._dict(
			action_name='Add Customers',
			domains=('Manufacturing', 'Services', 'Retail', 'Distribution'),
			icon="fa fa-group",
			title=_("Add Customers"),
			help=_("List a few of your customers. They could be organizations or individuals."),
			fields=[
				{"fieldtype":"Section Break"},
				{"fieldtype":"Data", "fieldname":"customer", "label":_("Customer"),
					"placeholder":_("Customer Name")},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Data", "fieldname":"customer_contact",
					"label":_("Contact Name"), "placeholder":_("Contact Name")}
			],
			add_more=1, max_count=3, mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_customers",
			action_cards=[
				{
					"action_name": "Add Customers",
					"title": _("You added Customers"),
					"done": 1,
					"actions": [{
						"label": _('Go to Customers'),
						"route": ["List", "Customer"]
					}, {
						"label": _("Import Customers"),
						"route": ["data-import-tool", {"doctype": "Customer"}]
					}],
					"help_links": [{
						"label": _('Learn More'),
						"link": ["https://erpnext.org/docs/user/manual/en/CRM/customer.html"]
					}]
				},
				{
					"action_name": "Create Leads",
					"title": _("Create Leads"),
					"content": _("Leads help you get business, add all your contacts and more as your leads"),
					"actions": [{
						"label": _('Make a Lead'),
						"new_doc": 'Lead'
					}],
					"help_links": [{
						"label": _('Learn More'),
						"url": ["https://erpnext.org/docs/user/manual/en/CRM/lead"]
					}]
				},
				{
					"action_name": "Watch CRM",
					"title": _("The CRM Module"),
					"content": _("How to manage Leads, Opportunities and Quotations in ERPNext."),
					"video_id": "o9XCSZHJfpA"
				}
			]
		),
		frappe._dict(
			action_name='Add Suppliers',
			domains=('Manufacturing', 'Services', 'Retail', 'Distribution'),
			icon="fa fa-group",
			title=_("Your Suppliers"),
			help=_("List a few of your suppliers. They could be organizations or individuals."),
			fields=[
				{"fieldtype":"Section Break"},
				{"fieldtype":"Data", "fieldname":"supplier", "label":_("Supplier"),
					"placeholder":_("Supplier Name")},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Data", "fieldname":"supplier_contact",
					"label":_("Contact Name"), "placeholder":_("Contact Name")},
			],
			add_more=1, max_count=3, mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_suppliers",
			action_cards=[
				{
					"action_name": "Add Suppliers",
					"title": _("You added Suppliers"),
					"done": 1,
					"actions": [{
						"label": _('Go to Suppliers'),
						"route": ["List", "Supplier"]
					}, {
						"label": _("Import Suppliers"),
						"route": ["data-import-tool", {"doctype": "Supplier"}]
					}],
					"help_links": [{
						"label": _('Learn More'),
						"link": ["https://erpnext.org/docs/user/manual/en/buying/supplier"]
					}]
				},
				{
					"action_name": "Watch Customers and Suppliers",
					"title": _("Customers and Suppliers"),
					"content": _("Manage Customers, Supplier, their address and contact and other defaults."),
					"video_id": "zsrrVDk6VBs"
				},
				{
					"action_name": "Watch Request for Quotation",
					"title": _("Request for Quotation"),
					"content": _("RFQs and Supplier Quotations in ERPNext."),
					"video_id": "q85GFvWfZGI"
				}
			]
		),
		frappe._dict(
			action_name='Add Products',
			domains=['Manufacturing', 'Services', 'Retail', 'Distribution'],
			icon="fa fa-barcode",
			title=_("Your Products or Services"),
			help=_("List your products or services that you buy or sell."),
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
			],
			add_more=1, max_count=3, mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_items",
			action_cards=[
				{
					"action_name": "Add Products",
					"title": _("You added Products"),
					"done": 1,
					"actions": [{
						"label": _("View Items"),
						"route": ["List", "Item"]
					}, {
						"label": _("Import Items"),
						"route": ["data-import-tool", {"doctype": "Item"}]
					}]
				},
				{
					"action_name": "Make Sales Order",
					"title": _("Manage your orders"),
					"content": _("Make Sales Orders to help you plan your work and deliver on-time."),
					"actions": [{
						"label": _('Make Sales Order'),
						"new_doc": 'Sales Order'
					}],
					"help_links": [{
						"label": _('Learn More'),
						"url": ["https://erpnext.org/docs/user/manual/en/selling/sales-order"]
					}]
				},
				{
					"action_name": "Learn Sales Cycle",
					"title": _("Sales Cycle"),
					"content": _("Learn how to create transactions related to sales cycle like Sales Order, Delivery Note, Sales Invoice and Payment Entry."),
					"video_id": "1eP90MWoDQM"
				}
			]
		),

		# School slides begin
		frappe._dict(
			action_name='Add Programs',
			domains=("Education"),
			title=_("Program"),
			help=_("Example: Masters in Computer Science"),
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"program", "label":_("Program"), "placeholder": _("Program Name")},
			],
			add_more=1, max_count=3, mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_program",
			action_cards=[
				{
					"action_name": "Add Programs",
					"title": _("You added Programs"),
					"done": 1,
					"actions": [{
						"label": _('Go to Programs'),
						"route": ["List", "Program"]
					}, {
						"label": _("Import Programs"),
						"route": ["data-import-tool", {"doctype": "Program"}]
					}]
				},
				{
					"action_name": "Watch Student Application",
					"title": _("Student Application"),
					"content": _("Manage student applications and create a web form for online applications"),
					"video_id": "l8PUACusN3E"
				}
			]

		),
		frappe._dict(
			action_name='Add Courses',
			domains=["Education"],
			title=_("Course"),
			help=_("Example: Basic Mathematics"),
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"course", "label":_("Course"),  "placeholder": _("Course Name")},
			],
			add_more=1, max_count=3, mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_course",
			action_cards=[
				{
					"action_name": "Add Courses",
					"title": _("You added Courses"),
					"done": 1,
					"actions": [{
						"label": _('Go to Courses'),
						"route": ["List", "Course"]
					}, {
						"label": _("Import Courses"),
						"route": ["data-import-tool", {"doctype": "Course"}]
					}]
				},
				{
					"action_name": "Add Students",
					"title": _("Add Students"),
					"content": _("Students are at the heart of the system. Add all your students."),
					"actions": [{
						"label": _('Make a Student'),
						"new_doc": 'Student'
					}]
				}
			]
		),
		frappe._dict(
			action_name='Add Instructors',
			domains=["Education"],
			title=_("Instructor"),
			help=_("People who teach at your organisation"),
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"instructor", "label":_("Instructor"),  "placeholder": _("Instructor Name")},
			],
			add_more=1, max_count=3, mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_instructor",
			action_cards=[
				{
					"action_name": "Add Instructors",
					"title": _("You added Instructors"),
					"done": 1,
					"actions": [{
						"label": _('Go to Instructors'),
						"route": ["List", "Instructor"]
					}, {
						"label": _("Import Instructors"),
						"route": ["data-import-tool", {"doctype": "Instructor"}]
					}]
				},
				{
					"action_name": "Make a Student Batch",
					"title": _("Make a Student Batch"),
					"content": _("Student Batches help you track attendance, assessments and fees for students"),
					"actions": [{
						"label": _('Make a Student Batch'),
						"new_doc": 'Student Batch'
					}]
				}
			]
		),
		frappe._dict(
			action_name='Add Rooms',
			domains=["Education"],
			title=_("Room"),
			help=_("Classrooms/ Laboratories etc where lectures can be scheduled."),
			fields=[
				{"fieldtype":"Section Break", "show_section_border": 1},
				{"fieldtype":"Data", "fieldname":"room", "label":_("Room")},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Int", "fieldname":"room_capacity", "label":_("Room Capacity"), "static": 1},
			],
			add_more=1, max_count=3, mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_room",
			action_cards=[
				{
					"action_name": "Add Rooms",
					"title": _("You added Rooms"),
					"done": 1,
					"actions": [{
						"label": _('Go to Rooms'),
						"route": ["List", "Room"]
					}, {
						"label": _("Import Rooms"),
						"route": ["data-import-tool", {"doctype": "Room"}]
					}]
				}
			]
		),
		# School slides end

		frappe._dict(
			action_name='Add Users',
			title=_("Add Users"),
			help=_("Add users to your organization, other than yourself."),
			fields=[
				{"fieldtype":"Section Break"},
				{"fieldtype":"Data", "fieldname":"user_email", "label":_("Email ID"),
					"placeholder":_("user@example.com"), "options": "Email", "static": 1},
				{"fieldtype":"Column Break"},
				{"fieldtype":"Data", "fieldname":"user_fullname",
					"label":_("Full Name"), "static": 1},
			],
			add_more=1, max_count=3, mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_users",
			action_cards=[
				{
					"action_name": "Add Users",
					"title": _("You added Users"),
					"done": 1,
					"actions": [{
						"label": _('Go to Users'),
						"route": ["List", "User"]
					}, {
						"label": _("Import Users"),
						"route": ["data-import-tool", {"doctype": "User"}]
					}],
					"help_links": [{
						"label": _('Learn More'),
						"link": ["https://erpnext.org/docs/user/manual/en/CRM/customer.html"]
					}]
				},
				{
					"action_name": "Watch Users and Permissions",
					"title": _("Users and Permissions"),
					"content": _("Add users in an ERPNext account, and manage their permissions"),
					"video_id": "8Slw1hsTmUI"
				}
			]
		)
	]

def get_user_progress_slides():
	slides = []
	slide_settings = get_slide_settings()

	domain = frappe.db.get_value('Company', erpnext.get_default_company(), 'domain')

	for s in slide_settings:
		if not s.domains or (domain and domain in s.domains):
			s.mark_as_done_method = "erpnext.setup.doctype.setup_progress.setup_progress.set_action_completed_state"
			s.done = get_action_completed_state(s.action_name) or 0
			slides.append(s)

	return slides

