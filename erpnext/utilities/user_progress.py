# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext
from frappe import _
from erpnext.setup.doctype.setup_progress.setup_progress import get_action_completed_state

def get_slide_settings():
	defaults = frappe.defaults.get_defaults()
	domain = frappe.db.get_value('Company', erpnext.get_default_company(), 'domain')
	company = defaults.get("company") or ''
	currency = defaults.get("currency") or ''

	doc = frappe.get_doc("Setup Progress")
	item = [d for d in doc.get("actions") if d.action_name == "Set Sales Target"]
	
	if len(item):
		item = item[0]
		if not item.action_document:
			item.action_document = company
			doc.save()

	# Initial state of slides
	return [
		frappe._dict(
			action_name='Add Company',
			title=_("Setup Company") if domain != 'Education' else _("Setup Institution"),
			help=_('Setup your ' + ('company' if domain != 'Education' else 'institution') + ' and brand.'),
			# image_src="/assets/erpnext/images/illustrations/shop.jpg",
			fields=[],
			done_state_title=_("You added " +  company),
			done_state_title_route=["Form", "Company", company],
			help_links=[
				{
					"label": _("Chart of Accounts"),
					"url": ["https://erpnext.com/docs/user/manual/en/accounts/chart-of-accounts"]
				},
				{
					"label": _("Opening Balances"),
					"video_id": "U5wPIvEn-0c"
				}
			]
		),
		frappe._dict(
			action_name='Set Sales Target',
			domains=('Manufacturing', 'Services', 'Retail', 'Distribution'),
			title=_("Set a Target"),
			help=_("Set a sales goal you'd like to achieve for your company."),
			fields=[
				{"fieldtype":"Currency", "fieldname":"monthly_sales_target",
					"label":_("Monthly Sales Target (" + currency + ")"), "reqd":1},
			],
			submit_method="erpnext.utilities.user_progress_utils.set_sales_target",
			done_state_title=_("Go to " + company),
			done_state_title_route=["Form", "Company", company],
			help_links=[
				{
					"label": _('Learn More'),
					"url": ["https://erpnext.com/docs/user/manual/en/setting-up/setting-company-sales-goal"]
				}
			]
		),
		frappe._dict(
			action_name='Add Customers',
			domains=('Manufacturing', 'Services', 'Retail', 'Distribution'),
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
			done_state_title=_("Go to Customers"),
			done_state_title_route=["List", "Customer"],
			help_links=[
				{
					"label": _('Learn More'),
					"url": ["https://erpnext.com/docs/user/manual/en/CRM/customer.html"]
				}
			]
		),

		frappe._dict(
			action_name='Add Letterhead',
			domains=('Manufacturing', 'Services', 'Retail', 'Distribution', 'Education'),
			title=_("Add Letterhead"),
			help=_("Upload your letter head (Keep it web friendly as 900px by 100px)"),
			fields=[
				{"fieldtype":"Attach Image", "fieldname":"letterhead",
					"is_private": 0,
					"align": "center"
				},
			],
			mandatory_entry=1,
			submit_method="erpnext.utilities.user_progress_utils.create_letterhead",
			done_state_title=_("Go to Letterheads"),
			done_state_title_route=["List", "Letter Head"]
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
			done_state_title=_("Go to Suppliers"),
			done_state_title_route=["List", "Supplier"],
			help_links=[
				{
					"label": _('Learn More'),
					"url": ["https://erpnext.com/docs/user/manual/en/buying/supplier"]
				},
				{
					"label": _('Customers and Suppliers'),
					"video_id": "zsrrVDk6VBs"
				},
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
			done_state_title=_("Go to Items"),
			done_state_title_route=["List", "Item"],
			help_links=[
				{
					"label": _("Explore Sales Cycle"),
					"video_id": "1eP90MWoDQM"
				},
			]
		),

		# Education slides begin
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
			done_state_title=_("Go to Programs"),
			done_state_title_route=["List", "Program"],
			help_links=[
				{
					"label": _("Student Application"),
					"video_id": "l8PUACusN3E"
				},
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
			done_state_title=_("Go to Courses"),
			done_state_title_route=["List", "Course"],
			help_links=[
				{
					"label": _('Add Students'),
					"route": ["List", "Student"]
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
			done_state_title=_("Go to Instructors"),
			done_state_title_route=["List", "Instructor"],
			help_links=[
				{
					"label": _('Student Batches'),
					"route": ["List", "Student Batch"]
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
			done_state_title=_("Go to Rooms"),
			done_state_title_route=["List", "Room"],
			help_links=[]
		),
		# Education slides end

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
			done_state_title=_("Go to Users"),
			done_state_title_route=["List", "User"],
			help_links=[
				{
					"label": _('Learn More'),
					"url": ["https://erpnext.com/docs/user/manual/en/setting-up/users-and-permissions"]
				},
				{
					"label": _('Users and Permissions'),
					"video_id": "8Slw1hsTmUI"
				},
			]
		)
	]

def get_user_progress_slides():
	slides = []
	slide_settings = get_slide_settings()

	domains = frappe.get_active_domains()
	for s in slide_settings:
		if not s.domains or any(d in domains for d in s.domains):
			s.mark_as_done_method = "erpnext.setup.doctype.setup_progress.setup_progress.set_action_completed_state"
			s.done = get_action_completed_state(s.action_name) or 0
			slides.append(s)

	return slides

