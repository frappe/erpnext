from __future__ import unicode_literals
from frappe import _

app_name = "erpnext"
app_title = "ERPNext"
app_publisher = "Frappe Technologies Pvt. Ltd."
app_description = """ERP made simple"""
app_icon = "fa fa-th"
app_color = "#e74c3c"
app_email = "info@erpnext.com"
app_license = "GNU General Public License (v3)"
source_link = "https://github.com/frappe/erpnext"

develop_version = '12.x.x-develop'
staging_version = '11.0.3-beta.21'

error_report_email = "support@erpnext.com"

docs_app = "foundation"

app_include_js = "assets/js/erpnext.min.js"
app_include_css = "assets/css/erpnext.css"
web_include_js = "assets/js/erpnext-web.min.js"
web_include_css = "assets/css/erpnext-web.css"

doctype_js = {
	"Communication": "public/js/communication.js",
	"Event": "public/js/event.js"
}

welcome_email = "erpnext.setup.utils.welcome_email"

# setup wizard
setup_wizard_requires = "assets/erpnext/js/setup_wizard.js"
setup_wizard_stages = "erpnext.setup.setup_wizard.setup_wizard.get_setup_stages"
setup_wizard_test = "erpnext.setup.setup_wizard.test_setup_wizard.run_setup_wizard_test"

before_install = "erpnext.setup.install.check_setup_wizard_not_completed"
after_install = "erpnext.setup.install.after_install"

boot_session = "erpnext.startup.boot.boot_session"
notification_config = "erpnext.startup.notifications.get_notification_config"
get_help_messages = "erpnext.utilities.activation.get_help_messages"
get_user_progress_slides = "erpnext.utilities.user_progress.get_user_progress_slides"
update_and_get_user_progress = "erpnext.utilities.user_progress_utils.update_default_domain_actions_and_get_state"

on_session_creation = "erpnext.shopping_cart.utils.set_cart_count"
on_logout = "erpnext.shopping_cart.utils.clear_cart_count"

treeviews = ['Account', 'Cost Center', 'Warehouse', 'Item Group', 'Customer Group', 'Sales Person', 'Territory', 'Assessment Group']

# website
update_website_context = "erpnext.shopping_cart.utils.update_website_context"
my_account_context = "erpnext.shopping_cart.utils.update_my_account_context"

email_append_to = ["Job Applicant", "Lead", "Opportunity", "Issue"]

calendars = ["Task", "Work Order", "Leave Application", "Sales Order", "Holiday List", "Course Schedule"]



domains = {
	'Agriculture': 'erpnext.domains.agriculture',
	'Distribution': 'erpnext.domains.distribution',
	'Education': 'erpnext.domains.education',
	'Healthcare': 'erpnext.domains.healthcare',
	'Hospitality': 'erpnext.domains.hospitality',
	'Manufacturing': 'erpnext.domains.manufacturing',
	'Non Profit': 'erpnext.domains.non_profit',
	'Retail': 'erpnext.domains.retail',
	'Services': 'erpnext.domains.services',
}

website_generators = ["Item Group", "Item", "BOM", "Sales Partner",
	"Job Opening", "Student Admission"]

website_context = {
	"favicon": 	"/assets/erpnext/images/favicon.png",
	"splash_image": "/assets/erpnext/images/erp-icon.svg"
}

website_route_rules = [
	{"from_route": "/orders", "to_route": "Sales Order"},
	{"from_route": "/orders/<path:name>", "to_route": "order",
		"defaults": {
			"doctype": "Sales Order",
			"parents": [{"label": _("Orders"), "route": "orders"}]
		}
	},
	{"from_route": "/invoices", "to_route": "Sales Invoice"},
	{"from_route": "/invoices/<path:name>", "to_route": "order",
		"defaults": {
			"doctype": "Sales Invoice",
			"parents": [{"label": _("Invoices"), "route": "invoices"}]
		}
	},
	{"from_route": "/supplier-quotations", "to_route": "Supplier Quotation"},
	{"from_route": "/supplier-quotations/<path:name>", "to_route": "order",
		"defaults": {
			"doctype": "Supplier Quotation",
			"parents": [{"label": _("Supplier Quotation"), "route": "supplier-quotations"}]
		}
	},
	{"from_route": "/quotations", "to_route": "Quotation"},
	{"from_route": "/quotations/<path:name>", "to_route": "order",
		"defaults": {
			"doctype": "Quotation",
			"parents": [{"label": _("Quotations"), "route": "quotations"}]
		}
	},
	{"from_route": "/shipments", "to_route": "Delivery Note"},
	{"from_route": "/shipments/<path:name>", "to_route": "order",
		"defaults": {
			"doctype": "Delivery Note",
			"parents": [{"label": _("Shipments"), "route": "shipments"}]
		}
	},
	{"from_route": "/rfq", "to_route": "Request for Quotation"},
	{"from_route": "/rfq/<path:name>", "to_route": "rfq",
		"defaults": {
			"doctype": "Request for Quotation",
			"parents": [{"label": _("Request for Quotation"), "route": "rfq"}]
		}
	},
	{"from_route": "/addresses", "to_route": "Address"},
	{"from_route": "/addresses/<path:name>", "to_route": "addresses",
		"defaults": {
			"doctype": "Address",
			"parents": [{"label": _("Addresses"), "route": "addresses"}]
		}
	},
	{"from_route": "/jobs", "to_route": "Job Opening"},
	{"from_route": "/admissions", "to_route": "Student Admission"},
	{"from_route": "/boms", "to_route": "BOM"},
	{"from_route": "/timesheets", "to_route": "Timesheet"},
]

standard_portal_menu_items = [
	{"title": _("Personal Details"), "route": "/personal-details", "reference_doctype": "Patient", "role": "Patient"},
	{"title": _("Projects"), "route": "/project", "reference_doctype": "Project"},
	{"title": _("Request for Quotations"), "route": "/rfq", "reference_doctype": "Request for Quotation", "role": "Supplier"},
	{"title": _("Supplier Quotation"), "route": "/supplier-quotations", "reference_doctype": "Supplier Quotation", "role": "Supplier"},
	{"title": _("Quotations"), "route": "/quotations", "reference_doctype": "Quotation", "role":"Customer"},
	{"title": _("Orders"), "route": "/orders", "reference_doctype": "Sales Order", "role":"Customer"},
	{"title": _("Invoices"), "route": "/invoices", "reference_doctype": "Sales Invoice", "role":"Customer"},
	{"title": _("Shipments"), "route": "/shipments", "reference_doctype": "Delivery Note", "role":"Customer"},
	{"title": _("Issues"), "route": "/issues", "reference_doctype": "Issue", "role":"Customer"},
	{"title": _("Addresses"), "route": "/addresses", "reference_doctype": "Address"},
	{"title": _("Timesheets"), "route": "/timesheets", "reference_doctype": "Timesheet", "role":"Customer"},
	{"title": _("Timesheets"), "route": "/timesheets", "reference_doctype": "Timesheet", "role":"Customer"},
	{"title": _("Lab Test"), "route": "/lab-test", "reference_doctype": "Lab Test", "role":"Patient"},
	{"title": _("Prescription"), "route": "/prescription", "reference_doctype": "Patient Encounter", "role":"Patient"},
	{"title": _("Patient Appointment"), "route": "/patient-appointments", "reference_doctype": "Patient Appointment", "role":"Patient"},
	{"title": _("Fees"), "route": "/fees", "reference_doctype": "Fees", "role":"Student"},
	{"title": _("Newsletter"), "route": "/newsletters", "reference_doctype": "Newsletter"},
	{"title": _("Admission"), "route": "/admissions", "reference_doctype": "Student Admission"},
	{"title": _("Certification"), "route": "/certification", "reference_doctype": "Certification Application"},
]

default_roles = [
	{'role': 'Customer', 'doctype':'Contact', 'email_field': 'email_id'},
	{'role': 'Supplier', 'doctype':'Contact', 'email_field': 'email_id'},
	{'role': 'Student', 'doctype':'Student', 'email_field': 'student_email_id'},
]

has_website_permission = {
	"Sales Order": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Quotation": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Sales Invoice": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Supplier Quotation": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Delivery Note": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Issue": "erpnext.support.doctype.issue.issue.has_website_permission",
	"Timesheet": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Lab Test": "erpnext.healthcare.web_form.lab_test.lab_test.has_website_permission",
	"Patient Encounter": "erpnext.healthcare.web_form.prescription.prescription.has_website_permission",
	"Patient Appointment": "erpnext.healthcare.web_form.patient_appointments.patient_appointments.has_website_permission",
	"Patient": "erpnext.healthcare.web_form.personal_details.personal_details.has_website_permission"
}

dump_report_map = "erpnext.startup.report_data_map.data_map"

before_tests = "erpnext.setup.utils.before_tests"

standard_queries = {
	"Customer": "erpnext.selling.doctype.customer.customer.get_customer_list"
}

doc_events = {
	"Stock Entry": {
		"on_submit": "erpnext.stock.doctype.material_request.material_request.update_completed_and_requested_qty",
		"on_cancel": "erpnext.stock.doctype.material_request.material_request.update_completed_and_requested_qty"
	},
	"User": {
		"after_insert": "frappe.contacts.doctype.contact.contact.update_contact",
		"validate": "erpnext.hr.doctype.employee.employee.validate_employee_role",
		"on_update": ["erpnext.hr.doctype.employee.employee.update_user_permissions",
			"erpnext.portal.utils.set_default_role"]
	},
	("Sales Taxes and Charges Template", 'Price List'): {
		"on_update": "erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings.validate_cart_settings"
	},

	"Website Settings": {
		"validate": "erpnext.portal.doctype.products_settings.products_settings.home_page_is_products"
	},
	"Sales Invoice": {
		"on_submit": "erpnext.regional.france.utils.create_transaction_log",
		"on_trash": "erpnext.regional.check_deletion_permission"
	},
	"Payment Entry": {
		"on_submit": ["erpnext.regional.france.utils.create_transaction_log", "erpnext.accounts.doctype.payment_request.payment_request.make_status_as_paid"],
		"on_trash": "erpnext.regional.check_deletion_permission"
	},
	'Address': {
		'validate': 'erpnext.regional.india.utils.validate_gstin_for_india'
	},
	('Sales Invoice', 'Purchase Invoice', 'Delivery Note'): {
		'validate': 'erpnext.regional.india.utils.set_place_of_supply'
	},
	"Contact":{
		"on_trash": "erpnext.support.doctype.issue.issue.update_issue"
	}
}

scheduler_events = {
	"hourly": [
		'erpnext.hr.doctype.daily_work_summary_group.daily_work_summary_group.trigger_emails',
		"erpnext.accounts.doctype.subscription.subscription.process_all",
		"erpnext.erpnext_integrations.doctype.amazon_mws_settings.amazon_mws_settings.schedule_get_order_details"
	],
	"daily": [
		"erpnext.stock.reorder_item.reorder_item",
		"erpnext.setup.doctype.email_digest.email_digest.send",
		"erpnext.support.doctype.issue.issue.auto_close_tickets",
		"erpnext.crm.doctype.opportunity.opportunity.auto_close_opportunity",
		"erpnext.controllers.accounts_controller.update_invoice_status",
		"erpnext.accounts.doctype.fiscal_year.fiscal_year.auto_create_fiscal_year",
		"erpnext.hr.doctype.employee.employee.send_birthday_reminders",
		"erpnext.projects.doctype.task.task.set_tasks_as_overdue",
		"erpnext.assets.doctype.asset.depreciation.post_depreciation_entries",
		"erpnext.hr.doctype.daily_work_summary_group.daily_work_summary_group.send_summary",
		"erpnext.stock.doctype.serial_no.serial_no.update_maintenance_status",
		"erpnext.buying.doctype.supplier_scorecard.supplier_scorecard.refresh_scorecards",
		"erpnext.setup.doctype.company.company.cache_companies_monthly_sales_history",
		"erpnext.assets.doctype.asset.asset.update_maintenance_status",
		"erpnext.assets.doctype.asset.asset.make_post_gl_entry",
		"erpnext.crm.doctype.contract.contract.update_status_for_contracts",
		"erpnext.projects.doctype.project.project.update_project_sales_billing"
	],
	"daily_long": [
		"erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.update_latest_price_in_all_boms"
	],
	"monthly": [
		"erpnext.accounts.deferred_revenue.convert_deferred_revenue_to_income",
		"erpnext.accounts.deferred_revenue.convert_deferred_expense_to_expense",
		"erpnext.hr.utils.allocate_earned_leaves"
	]
}

email_brand_image = "assets/erpnext/images/erpnext-logo.jpg"

default_mail_footer = """
	<span>
		Sent via
		<a class="text-muted" href="https://erpnext.com?source=via_email_footer" target="_blank">
			ERPNext
		</a>
	</span>
"""

get_translated_dict = {
	("doctype", "Global Defaults"): "frappe.geo.country_info.get_translated_dict"
}

bot_parsers = [
	'erpnext.utilities.bot.FindItemBot',
]

get_site_info = 'erpnext.utilities.get_site_info'

payment_gateway_enabled = "erpnext.accounts.utils.create_payment_gateway_account"

regional_overrides = {
	'France': {
		'erpnext.tests.test_regional.test_method': 'erpnext.regional.france.utils.test_method'
	},
	'India': {
		'erpnext.tests.test_regional.test_method': 'erpnext.regional.india.utils.test_method',
		'erpnext.controllers.taxes_and_totals.get_itemised_tax_breakup_header': 'erpnext.regional.india.utils.get_itemised_tax_breakup_header',
		'erpnext.controllers.taxes_and_totals.get_itemised_tax_breakup_data': 'erpnext.regional.india.utils.get_itemised_tax_breakup_data',
		'erpnext.accounts.party.get_regional_address_details': 'erpnext.regional.india.utils.get_regional_address_details',
		'erpnext.hr.utils.calculate_annual_eligible_hra_exemption': 'erpnext.regional.india.utils.calculate_annual_eligible_hra_exemption',
		'erpnext.hr.utils.calculate_hra_exemption_for_period': 'erpnext.regional.india.utils.calculate_hra_exemption_for_period'
	},
	'United Arab Emirates': {
		'erpnext.controllers.taxes_and_totals.update_itemised_tax_data': 'erpnext.regional.united_arab_emirates.utils.update_itemised_tax_data'
	},
	'Saudi Arabia': {
		'erpnext.controllers.taxes_and_totals.update_itemised_tax_data': 'erpnext.regional.united_arab_emirates.utils.update_itemised_tax_data'
	}
}
