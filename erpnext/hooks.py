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
app_logo_url = "/assets/erpnext/images/erpnext-logo.svg"


develop_version = "13.x.x-develop"

app_include_js = "/assets/js/erpnext.min.js"
app_include_css = "/assets/css/erpnext.css"
web_include_js = "/assets/js/erpnext-web.min.js"
web_include_css = "/assets/css/erpnext-web.css"

doctype_js = {
	"Address": "public/js/address.js",
	"Communication": "public/js/communication.js",
	"Event": "public/js/event.js",
	"Newsletter": "public/js/newsletter.js",
	"Contact": "public/js/contact.js",
}

override_doctype_class = {"Address": "erpnext.accounts.custom.address.ERPNextAddress"}

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
leaderboards = "erpnext.startup.leaderboard.get_leaderboards"
filters_config = "erpnext.startup.filters.get_filters_config"
additional_print_settings = "erpnext.controllers.print_settings.get_print_settings"

on_session_creation = [
	"erpnext.portal.utils.create_customer_or_supplier",
	"erpnext.e_commerce.shopping_cart.utils.set_cart_count",
]
on_logout = "erpnext.e_commerce.shopping_cart.utils.clear_cart_count"

treeviews = [
	"Account",
	"Cost Center",
	"Warehouse",
	"Item Group",
	"Customer Group",
	"Sales Person",
	"Territory",
	"Assessment Group",
	"Department",
]

# website
update_website_context = [
	"erpnext.e_commerce.shopping_cart.utils.update_website_context",
	"erpnext.education.doctype.education_settings.education_settings.update_website_context",
]
my_account_context = "erpnext.e_commerce.shopping_cart.utils.update_my_account_context"
webform_list_context = "erpnext.controllers.website_list_for_contact.get_webform_list_context"

calendars = [
	"Task",
	"Work Order",
	"Leave Application",
	"Sales Order",
	"Holiday List",
	"Course Schedule",
]

domains = {
	"Agriculture": "erpnext.domains.agriculture",
	"Distribution": "erpnext.domains.distribution",
	"Education": "erpnext.domains.education",
	"Healthcare": "erpnext.domains.healthcare",
	"Hospitality": "erpnext.domains.hospitality",
	"Manufacturing": "erpnext.domains.manufacturing",
	"Non Profit": "erpnext.domains.non_profit",
	"Retail": "erpnext.domains.retail",
	"Services": "erpnext.domains.services",
}

website_generators = [
	"Item Group",
	"Website Item",
	"BOM",
	"Sales Partner",
	"Job Opening",
	"Student Admission",
]

website_context = {
	"favicon": "/assets/erpnext/images/erpnext-favicon.svg",
	"splash_image": "/assets/erpnext/images/erpnext-logo.svg",
}

website_route_rules = [
	{"from_route": "/orders", "to_route": "Sales Order"},
	{
		"from_route": "/orders/<path:name>",
		"to_route": "order",
		"defaults": {"doctype": "Sales Order", "parents": [{"label": _("Orders"), "route": "orders"}]},
	},
	{"from_route": "/invoices", "to_route": "Sales Invoice"},
	{
		"from_route": "/invoices/<path:name>",
		"to_route": "order",
		"defaults": {
			"doctype": "Sales Invoice",
			"parents": [{"label": _("Invoices"), "route": "invoices"}],
		},
	},
	{"from_route": "/supplier-quotations", "to_route": "Supplier Quotation"},
	{
		"from_route": "/supplier-quotations/<path:name>",
		"to_route": "order",
		"defaults": {
			"doctype": "Supplier Quotation",
			"parents": [{"label": _("Supplier Quotation"), "route": "supplier-quotations"}],
		},
	},
	{"from_route": "/purchase-orders", "to_route": "Purchase Order"},
	{
		"from_route": "/purchase-orders/<path:name>",
		"to_route": "order",
		"defaults": {
			"doctype": "Purchase Order",
			"parents": [{"label": _("Purchase Order"), "route": "purchase-orders"}],
		},
	},
	{"from_route": "/purchase-invoices", "to_route": "Purchase Invoice"},
	{
		"from_route": "/purchase-invoices/<path:name>",
		"to_route": "order",
		"defaults": {
			"doctype": "Purchase Invoice",
			"parents": [{"label": _("Purchase Invoice"), "route": "purchase-invoices"}],
		},
	},
	{"from_route": "/quotations", "to_route": "Quotation"},
	{
		"from_route": "/quotations/<path:name>",
		"to_route": "order",
		"defaults": {
			"doctype": "Quotation",
			"parents": [{"label": _("Quotations"), "route": "quotations"}],
		},
	},
	{"from_route": "/shipments", "to_route": "Delivery Note"},
	{
		"from_route": "/shipments/<path:name>",
		"to_route": "order",
		"defaults": {
			"doctype": "Delivery Note",
			"parents": [{"label": _("Shipments"), "route": "shipments"}],
		},
	},
	{"from_route": "/rfq", "to_route": "Request for Quotation"},
	{
		"from_route": "/rfq/<path:name>",
		"to_route": "rfq",
		"defaults": {
			"doctype": "Request for Quotation",
			"parents": [{"label": _("Request for Quotation"), "route": "rfq"}],
		},
	},
	{"from_route": "/addresses", "to_route": "Address"},
	{
		"from_route": "/addresses/<path:name>",
		"to_route": "addresses",
		"defaults": {"doctype": "Address", "parents": [{"label": _("Addresses"), "route": "addresses"}]},
	},
	{"from_route": "/jobs", "to_route": "Job Opening"},
	{"from_route": "/admissions", "to_route": "Student Admission"},
	{"from_route": "/boms", "to_route": "BOM"},
	{"from_route": "/timesheets", "to_route": "Timesheet"},
	{"from_route": "/material-requests", "to_route": "Material Request"},
	{
		"from_route": "/material-requests/<path:name>",
		"to_route": "material_request_info",
		"defaults": {
			"doctype": "Material Request",
			"parents": [{"label": _("Material Request"), "route": "material-requests"}],
		},
	},
	{"from_route": "/project", "to_route": "Project"},
]

standard_portal_menu_items = [
	{
		"title": _("Personal Details"),
		"route": "/personal-details",
		"reference_doctype": "Patient",
		"role": "Patient",
	},
	{"title": _("Projects"), "route": "/project", "reference_doctype": "Project"},
	{
		"title": _("Request for Quotations"),
		"route": "/rfq",
		"reference_doctype": "Request for Quotation",
		"role": "Supplier",
	},
	{
		"title": _("Supplier Quotation"),
		"route": "/supplier-quotations",
		"reference_doctype": "Supplier Quotation",
		"role": "Supplier",
	},
	{
		"title": _("Purchase Orders"),
		"route": "/purchase-orders",
		"reference_doctype": "Purchase Order",
		"role": "Supplier",
	},
	{
		"title": _("Purchase Invoices"),
		"route": "/purchase-invoices",
		"reference_doctype": "Purchase Invoice",
		"role": "Supplier",
	},
	{
		"title": _("Quotations"),
		"route": "/quotations",
		"reference_doctype": "Quotation",
		"role": "Customer",
	},
	{
		"title": _("Orders"),
		"route": "/orders",
		"reference_doctype": "Sales Order",
		"role": "Customer",
	},
	{
		"title": _("Invoices"),
		"route": "/invoices",
		"reference_doctype": "Sales Invoice",
		"role": "Customer",
	},
	{
		"title": _("Shipments"),
		"route": "/shipments",
		"reference_doctype": "Delivery Note",
		"role": "Customer",
	},
	{"title": _("Issues"), "route": "/issues", "reference_doctype": "Issue", "role": "Customer"},
	{"title": _("Addresses"), "route": "/addresses", "reference_doctype": "Address"},
	{
		"title": _("Timesheets"),
		"route": "/timesheets",
		"reference_doctype": "Timesheet",
		"role": "Customer",
	},
	{
		"title": _("Lab Test"),
		"route": "/lab-test",
		"reference_doctype": "Lab Test",
		"role": "Patient",
	},
	{
		"title": _("Prescription"),
		"route": "/prescription",
		"reference_doctype": "Patient Encounter",
		"role": "Patient",
	},
	{
		"title": _("Patient Appointment"),
		"route": "/patient-appointments",
		"reference_doctype": "Patient Appointment",
		"role": "Patient",
	},
	{"title": _("Fees"), "route": "/fees", "reference_doctype": "Fees", "role": "Student"},
	{"title": _("Newsletter"), "route": "/newsletters", "reference_doctype": "Newsletter"},
	{
		"title": _("Admission"),
		"route": "/admissions",
		"reference_doctype": "Student Admission",
		"role": "Student",
	},
	{
		"title": _("Certification"),
		"route": "/certification",
		"reference_doctype": "Certification Application",
		"role": "Non Profit Portal User",
	},
	{
		"title": _("Material Request"),
		"route": "/material-requests",
		"reference_doctype": "Material Request",
		"role": "Customer",
	},
	{"title": _("Appointment Booking"), "route": "/book_appointment"},
]

default_roles = [
	{"role": "Customer", "doctype": "Contact", "email_field": "email_id"},
	{"role": "Supplier", "doctype": "Contact", "email_field": "email_id"},
	{"role": "Student", "doctype": "Student", "email_field": "student_email_id"},
]

sounds = [
	{"name": "incoming-call", "src": "/assets/erpnext/sounds/incoming-call.mp3", "volume": 0.2},
	{"name": "call-disconnect", "src": "/assets/erpnext/sounds/call-disconnect.mp3", "volume": 0.2},
]

has_upload_permission = {"Employee": "erpnext.hr.doctype.employee.employee.has_upload_permission"}

has_website_permission = {
	"Sales Order": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Quotation": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Sales Invoice": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Supplier Quotation": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Purchase Order": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Purchase Invoice": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Material Request": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Delivery Note": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Issue": "erpnext.support.doctype.issue.issue.has_website_permission",
	"Timesheet": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Lab Test": "erpnext.healthcare.web_form.lab_test.lab_test.has_website_permission",
	"Patient Encounter": "erpnext.healthcare.web_form.prescription.prescription.has_website_permission",
	"Patient Appointment": "erpnext.healthcare.web_form.patient_appointments.patient_appointments.has_website_permission",
	"Patient": "erpnext.healthcare.web_form.personal_details.personal_details.has_website_permission",
}

before_tests = "erpnext.setup.utils.before_tests"

standard_queries = {
	"Customer": "erpnext.selling.doctype.customer.customer.get_customer_list",
	"Healthcare Practitioner": "erpnext.healthcare.doctype.healthcare_practitioner.healthcare_practitioner.get_practitioner_list",
}

doc_events = {
	"*": {
		"on_submit": "erpnext.healthcare.doctype.patient_history_settings.patient_history_settings.create_medical_record",
		"on_update_after_submit": "erpnext.healthcare.doctype.patient_history_settings.patient_history_settings.update_medical_record",
		"on_cancel": "erpnext.healthcare.doctype.patient_history_settings.patient_history_settings.delete_medical_record",
	},
	"Stock Entry": {
		"on_submit": "erpnext.stock.doctype.material_request.material_request.update_completed_and_requested_qty",
		"on_cancel": "erpnext.stock.doctype.material_request.material_request.update_completed_and_requested_qty",
	},
	"User": {
		"after_insert": "frappe.contacts.doctype.contact.contact.update_contact",
		"validate": "erpnext.hr.doctype.employee.employee.validate_employee_role",
		"on_update": [
			"erpnext.hr.doctype.employee.employee.update_user_permissions",
			"erpnext.portal.utils.set_default_role",
		],
	},
	"Communication": {"on_update": ["erpnext.support.doctype.issue.issue.set_first_response_time"]},
	"Sales Taxes and Charges Template": {
		"on_update": "erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings.validate_cart_settings"
	},
	"Tax Category": {"validate": "erpnext.regional.india.utils.validate_tax_category"},
	"Sales Invoice": {
		"on_submit": [
			"erpnext.regional.create_transaction_log",
			"erpnext.regional.italy.utils.sales_invoice_on_submit",
			"erpnext.regional.saudi_arabia.utils.create_qr_code",
			"erpnext.erpnext_integrations.taxjar_integration.create_transaction",
		],
		"on_cancel": [
			"erpnext.regional.italy.utils.sales_invoice_on_cancel",
			"erpnext.erpnext_integrations.taxjar_integration.delete_transaction",
			"erpnext.regional.saudi_arabia.utils.delete_qr_code_file",
		],
		"on_trash": "erpnext.regional.check_deletion_permission",
		"validate": [
			"erpnext.regional.india.utils.validate_document_name",
			"erpnext.regional.india.utils.update_taxable_values",
			"erpnext.regional.india.utils.validate_sez_and_export_invoices",
		],
	},
	"POS Invoice": {"on_submit": ["erpnext.regional.saudi_arabia.utils.create_qr_code"]},
	"Purchase Invoice": {
		"validate": [
			"erpnext.regional.india.utils.validate_reverse_charge_transaction",
			"erpnext.regional.india.utils.update_itc_availed_fields",
			"erpnext.regional.united_arab_emirates.utils.update_grand_total_for_rcm",
			"erpnext.regional.united_arab_emirates.utils.validate_returns",
			"erpnext.regional.india.utils.update_taxable_values",
		]
	},
	"Payment Entry": {
		"validate": "erpnext.regional.india.utils.update_place_of_supply",
		"on_submit": [
			"erpnext.regional.create_transaction_log",
			"erpnext.accounts.doctype.payment_request.payment_request.update_payment_req_status",
			"erpnext.accounts.doctype.dunning.dunning.resolve_dunning",
		],
		"on_trash": "erpnext.regional.check_deletion_permission",
	},
	"Address": {
		"validate": [
			"erpnext.regional.india.utils.validate_gstin_for_india",
			"erpnext.regional.italy.utils.set_state_code",
			"erpnext.regional.india.utils.update_gst_category",
			"erpnext.healthcare.utils.update_address_links",
		],
	},
	"Supplier": {"validate": "erpnext.regional.india.utils.validate_pan_for_india"},
	(
		"Sales Invoice",
		"Sales Order",
		"Delivery Note",
		"Purchase Invoice",
		"Purchase Order",
		"Purchase Receipt",
	): {"validate": ["erpnext.regional.india.utils.set_place_of_supply"]},
	"Contact": {
		"on_trash": "erpnext.support.doctype.issue.issue.update_issue",
		"after_insert": "erpnext.telephony.doctype.call_log.call_log.link_existing_conversations",
		"validate": [
			"erpnext.crm.utils.update_lead_phone_numbers",
			"erpnext.healthcare.utils.update_patient_email_and_phone_numbers",
		],
	},
	"Email Unsubscribe": {
		"after_insert": "erpnext.crm.doctype.email_campaign.email_campaign.unsubscribe_recipient"
	},
	("Quotation", "Sales Order", "Sales Invoice"): {
		"validate": ["erpnext.erpnext_integrations.taxjar_integration.set_sales_tax"]
	},
	"Company": {
		"on_trash": [
			"erpnext.regional.india.utils.delete_gst_settings_for_company",
			"erpnext.regional.saudi_arabia.utils.delete_vat_settings_for_company",
		]
	},
	"Integration Request": {
		"validate": "erpnext.accounts.doctype.payment_request.payment_request.validate_payment"
	},
}

# On cancel event Payment Entry will be exempted and all linked submittable doctype will get cancelled.
# to maintain data integrity we exempted payment entry. it will un-link when sales invoice get cancelled.
# if payment entry not in auto cancel exempted doctypes it will cancel payment entry.
auto_cancel_exempted_doctypes = ["Payment Entry", "Inpatient Medication Entry"]

after_migrate = ["erpnext.setup.install.update_select_perm_after_install"]

scheduler_events = {
	"cron": {
		"0/5 * * * *": [
			"erpnext.manufacturing.doctype.bom_update_log.bom_update_log.resume_bom_cost_update_jobs",
		],
		"0/30 * * * *": [
			"erpnext.utilities.doctype.video.video.update_youtube_data",
		],
		# Hourly but offset by 30 minutes
		"30 * * * *": [
			"erpnext.accounts.doctype.gl_entry.gl_entry.rename_gle_sle_docs",
		],
		# Daily but offset by 45 minutes
		"45 0 * * *": [
			"erpnext.stock.reorder_item.reorder_item",
		],
	},
	"all": [
		"erpnext.projects.doctype.project.project.project_status_update_reminder",
		"erpnext.healthcare.doctype.patient_appointment.patient_appointment.send_appointment_reminder",
		"erpnext.hr.doctype.interview.interview.send_interview_reminder",
		"erpnext.crm.doctype.social_media_post.social_media_post.process_scheduled_social_media_posts",
	],
	"hourly": [
		"erpnext.hr.doctype.daily_work_summary_group.daily_work_summary_group.trigger_emails",
		"erpnext.erpnext_integrations.doctype.amazon_mws_settings.amazon_mws_settings.schedule_get_order_details",
		"erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.automatic_synchronization",
		"erpnext.projects.doctype.project.project.hourly_reminder",
		"erpnext.projects.doctype.project.project.collect_project_status",
		"erpnext.support.doctype.issue.issue.set_service_level_agreement_variance",
		"erpnext.erpnext_integrations.connectors.shopify_connection.sync_old_orders",
	],
	"hourly_long": [
		"erpnext.accounts.doctype.subscription.subscription.process_all",
		"erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.repost_entries",
		"erpnext.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts",
	],
	"daily": [
		"erpnext.support.doctype.issue.issue.auto_close_tickets",
		"erpnext.crm.doctype.opportunity.opportunity.auto_close_opportunity",
		"erpnext.controllers.accounts_controller.update_invoice_status",
		"erpnext.accounts.doctype.fiscal_year.fiscal_year.auto_create_fiscal_year",
		"erpnext.hr.doctype.employee.employee_reminders.send_work_anniversary_reminders",
		"erpnext.hr.doctype.employee.employee_reminders.send_birthday_reminders",
		"erpnext.projects.doctype.task.task.set_tasks_as_overdue",
		"erpnext.assets.doctype.asset.depreciation.post_depreciation_entries",
		"erpnext.hr.doctype.daily_work_summary_group.daily_work_summary_group.send_summary",
		"erpnext.stock.doctype.serial_no.serial_no.update_maintenance_status",
		"erpnext.buying.doctype.supplier_scorecard.supplier_scorecard.refresh_scorecards",
		"erpnext.setup.doctype.company.company.cache_companies_monthly_sales_history",
		"erpnext.assets.doctype.asset.asset.update_maintenance_status",
		"erpnext.assets.doctype.asset.asset.make_post_gl_entry",
		"erpnext.crm.doctype.contract.contract.update_status_for_contracts",
		"erpnext.projects.doctype.project.project.update_project_sales_billing",
		"erpnext.projects.doctype.project.project.send_project_status_email_to_users",
		"erpnext.quality_management.doctype.quality_review.quality_review.review",
		"erpnext.support.doctype.service_level_agreement.service_level_agreement.check_agreement_status",
		"erpnext.crm.doctype.email_campaign.email_campaign.send_email_to_leads_or_contacts",
		"erpnext.crm.doctype.email_campaign.email_campaign.set_email_campaign_status",
		"erpnext.selling.doctype.quotation.quotation.set_expired_status",
		"erpnext.healthcare.doctype.patient_appointment.patient_appointment.update_appointment_status",
		"erpnext.buying.doctype.supplier_quotation.supplier_quotation.set_expired_status",
		"erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts.send_auto_email",
		"erpnext.non_profit.doctype.membership.membership.set_expired_status",
		"erpnext.hr.doctype.interview.interview.send_daily_feedback_reminder",
	],
	"daily_long": [
		"erpnext.setup.doctype.email_digest.email_digest.send",
		"erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.auto_update_latest_price_in_all_boms",
		"erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",
		"erpnext.hr.utils.generate_leave_encashment",
		"erpnext.hr.utils.allocate_earned_leaves",
		"erpnext.loan_management.doctype.process_loan_security_shortfall.process_loan_security_shortfall.create_process_loan_security_shortfall",
		"erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual.process_loan_interest_accrual_for_term_loans",
		"erpnext.crm.doctype.lead.lead.daily_open_lead",
	],
	"weekly": ["erpnext.hr.doctype.employee.employee_reminders.send_reminders_in_advance_weekly"],
	"monthly": ["erpnext.hr.doctype.employee.employee_reminders.send_reminders_in_advance_monthly"],
	"monthly_long": [
		"erpnext.accounts.deferred_revenue.process_deferred_accounting",
		"erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual.process_loan_interest_accrual_for_demand_loans",
	],
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
	"erpnext.utilities.bot.FindItemBot",
]

get_site_info = "erpnext.utilities.get_site_info"

payment_gateway_enabled = "erpnext.accounts.utils.create_payment_gateway_account"

communication_doctypes = ["Customer", "Supplier"]

accounting_dimension_doctypes = [
	"GL Entry",
	"Sales Invoice",
	"Purchase Invoice",
	"Payment Entry",
	"Asset",
	"Expense Claim",
	"Expense Claim Detail",
	"Expense Taxes and Charges",
	"Stock Entry",
	"Budget",
	"Payroll Entry",
	"Delivery Note",
	"Sales Invoice Item",
	"Purchase Invoice Item",
	"Purchase Order Item",
	"Journal Entry Account",
	"Material Request Item",
	"Delivery Note Item",
	"Purchase Receipt Item",
	"Stock Entry Detail",
	"Payment Entry Deduction",
	"Sales Taxes and Charges",
	"Purchase Taxes and Charges",
	"Shipping Rule",
	"Landed Cost Item",
	"Asset Value Adjustment",
	"Asset Repair",
	"Loyalty Program",
	"Fee Schedule",
	"Fee Structure",
	"Stock Reconciliation",
	"Travel Request",
	"Fees",
	"POS Profile",
	"Opening Invoice Creation Tool",
	"Opening Invoice Creation Tool Item",
	"Subscription",
	"Subscription Plan",
	"POS Invoice",
	"POS Invoice Item",
	"Purchase Order",
	"Purchase Receipt",
	"Sales Order",
]

regional_overrides = {
	"France": {
		"erpnext.tests.test_regional.test_method": "erpnext.regional.france.utils.test_method"
	},
	"India": {
		"erpnext.tests.test_regional.test_method": "erpnext.regional.india.utils.test_method",
		"erpnext.controllers.taxes_and_totals.get_itemised_tax_breakup_header": "erpnext.regional.india.utils.get_itemised_tax_breakup_header",
		"erpnext.controllers.taxes_and_totals.get_itemised_tax_breakup_data": "erpnext.regional.india.utils.get_itemised_tax_breakup_data",
		"erpnext.accounts.party.get_regional_address_details": "erpnext.regional.india.utils.get_regional_address_details",
		"erpnext.controllers.taxes_and_totals.get_regional_round_off_accounts": "erpnext.regional.india.utils.get_regional_round_off_accounts",
		"erpnext.hr.utils.calculate_annual_eligible_hra_exemption": "erpnext.regional.india.utils.calculate_annual_eligible_hra_exemption",
		"erpnext.hr.utils.calculate_hra_exemption_for_period": "erpnext.regional.india.utils.calculate_hra_exemption_for_period",
		"erpnext.controllers.accounts_controller.validate_einvoice_fields": "erpnext.regional.india.e_invoice.utils.validate_einvoice_fields",
		"erpnext.assets.doctype.asset.asset.get_depreciation_amount": "erpnext.regional.india.utils.get_depreciation_amount",
		"erpnext.stock.doctype.item.item.set_item_tax_from_hsn_code": "erpnext.regional.india.utils.set_item_tax_from_hsn_code",
	},
	"United Arab Emirates": {
		"erpnext.controllers.taxes_and_totals.update_itemised_tax_data": "erpnext.regional.united_arab_emirates.utils.update_itemised_tax_data",
		"erpnext.accounts.doctype.purchase_invoice.purchase_invoice.make_regional_gl_entries": "erpnext.regional.united_arab_emirates.utils.make_regional_gl_entries",
	},
	"Saudi Arabia": {
		"erpnext.controllers.taxes_and_totals.update_itemised_tax_data": "erpnext.regional.united_arab_emirates.utils.update_itemised_tax_data"
	},
	"Italy": {
		"erpnext.controllers.taxes_and_totals.update_itemised_tax_data": "erpnext.regional.italy.utils.update_itemised_tax_data",
		"erpnext.controllers.accounts_controller.validate_regional": "erpnext.regional.italy.utils.sales_invoice_validate",
	},
}
user_privacy_documents = [
	{
		"doctype": "Lead",
		"match_field": "email_id",
		"personal_fields": ["phone", "mobile_no", "fax", "website", "lead_name"],
	},
	{
		"doctype": "Opportunity",
		"match_field": "contact_email",
		"personal_fields": ["contact_mobile", "contact_display", "customer_name"],
	},
]

# ERPNext doctypes for Global Search
global_search_doctypes = {
	"Default": [
		{"doctype": "Customer", "index": 0},
		{"doctype": "Supplier", "index": 1},
		{"doctype": "Item", "index": 2},
		{"doctype": "Warehouse", "index": 3},
		{"doctype": "Account", "index": 4},
		{"doctype": "Employee", "index": 5},
		{"doctype": "BOM", "index": 6},
		{"doctype": "Sales Invoice", "index": 7},
		{"doctype": "Sales Order", "index": 8},
		{"doctype": "Quotation", "index": 9},
		{"doctype": "Work Order", "index": 10},
		{"doctype": "Purchase Order", "index": 11},
		{"doctype": "Purchase Receipt", "index": 12},
		{"doctype": "Purchase Invoice", "index": 13},
		{"doctype": "Delivery Note", "index": 14},
		{"doctype": "Stock Entry", "index": 15},
		{"doctype": "Material Request", "index": 16},
		{"doctype": "Delivery Trip", "index": 17},
		{"doctype": "Pick List", "index": 18},
		{"doctype": "Salary Slip", "index": 19},
		{"doctype": "Leave Application", "index": 20},
		{"doctype": "Expense Claim", "index": 21},
		{"doctype": "Payment Entry", "index": 22},
		{"doctype": "Lead", "index": 23},
		{"doctype": "Opportunity", "index": 24},
		{"doctype": "Item Price", "index": 25},
		{"doctype": "Purchase Taxes and Charges Template", "index": 26},
		{"doctype": "Sales Taxes and Charges", "index": 27},
		{"doctype": "Asset", "index": 28},
		{"doctype": "Project", "index": 29},
		{"doctype": "Task", "index": 30},
		{"doctype": "Timesheet", "index": 31},
		{"doctype": "Issue", "index": 32},
		{"doctype": "Serial No", "index": 33},
		{"doctype": "Batch", "index": 34},
		{"doctype": "Branch", "index": 35},
		{"doctype": "Department", "index": 36},
		{"doctype": "Employee Grade", "index": 37},
		{"doctype": "Designation", "index": 38},
		{"doctype": "Job Opening", "index": 39},
		{"doctype": "Job Applicant", "index": 40},
		{"doctype": "Job Offer", "index": 41},
		{"doctype": "Salary Structure Assignment", "index": 42},
		{"doctype": "Appraisal", "index": 43},
		{"doctype": "Loan", "index": 44},
		{"doctype": "Maintenance Schedule", "index": 45},
		{"doctype": "Maintenance Visit", "index": 46},
		{"doctype": "Warranty Claim", "index": 47},
	],
	"Healthcare": [
		{"doctype": "Patient", "index": 1},
		{"doctype": "Medical Department", "index": 2},
		{"doctype": "Vital Signs", "index": 3},
		{"doctype": "Healthcare Practitioner", "index": 4},
		{"doctype": "Patient Appointment", "index": 5},
		{"doctype": "Healthcare Service Unit", "index": 6},
		{"doctype": "Patient Encounter", "index": 7},
		{"doctype": "Antibiotic", "index": 8},
		{"doctype": "Diagnosis", "index": 9},
		{"doctype": "Lab Test", "index": 10},
		{"doctype": "Clinical Procedure", "index": 11},
		{"doctype": "Inpatient Record", "index": 12},
		{"doctype": "Sample Collection", "index": 13},
		{"doctype": "Patient Medical Record", "index": 14},
		{"doctype": "Appointment Type", "index": 15},
		{"doctype": "Fee Validity", "index": 16},
		{"doctype": "Practitioner Schedule", "index": 17},
		{"doctype": "Dosage Form", "index": 18},
		{"doctype": "Lab Test Sample", "index": 19},
		{"doctype": "Prescription Duration", "index": 20},
		{"doctype": "Prescription Dosage", "index": 21},
		{"doctype": "Sensitivity", "index": 22},
		{"doctype": "Complaint", "index": 23},
		{"doctype": "Medical Code", "index": 24},
	],
	"Education": [
		{"doctype": "Article", "index": 1},
		{"doctype": "Video", "index": 2},
		{"doctype": "Topic", "index": 3},
		{"doctype": "Course", "index": 4},
		{"doctype": "Program", "index": 5},
		{"doctype": "Quiz", "index": 6},
		{"doctype": "Question", "index": 7},
		{"doctype": "Fee Schedule", "index": 8},
		{"doctype": "Fee Structure", "index": 9},
		{"doctype": "Fees", "index": 10},
		{"doctype": "Student Group", "index": 11},
		{"doctype": "Student", "index": 12},
		{"doctype": "Instructor", "index": 13},
		{"doctype": "Course Activity", "index": 14},
		{"doctype": "Quiz Activity", "index": 15},
		{"doctype": "Course Enrollment", "index": 16},
		{"doctype": "Program Enrollment", "index": 17},
		{"doctype": "Student Language", "index": 18},
		{"doctype": "Student Applicant", "index": 19},
		{"doctype": "Assessment Result", "index": 20},
		{"doctype": "Assessment Plan", "index": 21},
		{"doctype": "Grading Scale", "index": 22},
		{"doctype": "Guardian", "index": 23},
		{"doctype": "Student Leave Application", "index": 24},
		{"doctype": "Student Log", "index": 25},
		{"doctype": "Room", "index": 26},
		{"doctype": "Course Schedule", "index": 27},
		{"doctype": "Student Attendance", "index": 28},
		{"doctype": "Announcement", "index": 29},
		{"doctype": "Student Category", "index": 30},
		{"doctype": "Assessment Group", "index": 31},
		{"doctype": "Student Batch Name", "index": 32},
		{"doctype": "Assessment Criteria", "index": 33},
		{"doctype": "Academic Year", "index": 34},
		{"doctype": "Academic Term", "index": 35},
		{"doctype": "School House", "index": 36},
		{"doctype": "Student Admission", "index": 37},
		{"doctype": "Fee Category", "index": 38},
		{"doctype": "Assessment Code", "index": 39},
		{"doctype": "Discussion", "index": 40},
	],
	"Agriculture": [
		{"doctype": "Weather", "index": 1},
		{"doctype": "Soil Texture", "index": 2},
		{"doctype": "Water Analysis", "index": 3},
		{"doctype": "Soil Analysis", "index": 4},
		{"doctype": "Plant Analysis", "index": 5},
		{"doctype": "Agriculture Analysis Criteria", "index": 6},
		{"doctype": "Disease", "index": 7},
		{"doctype": "Crop", "index": 8},
		{"doctype": "Fertilizer", "index": 9},
		{"doctype": "Crop Cycle", "index": 10},
	],
	"Non Profit": [
		{"doctype": "Certified Consultant", "index": 1},
		{"doctype": "Certification Application", "index": 2},
		{"doctype": "Volunteer", "index": 3},
		{"doctype": "Membership", "index": 4},
		{"doctype": "Member", "index": 5},
		{"doctype": "Donor", "index": 6},
		{"doctype": "Chapter", "index": 7},
		{"doctype": "Grant Application", "index": 8},
		{"doctype": "Volunteer Type", "index": 9},
		{"doctype": "Donor Type", "index": 10},
		{"doctype": "Membership Type", "index": 11},
	],
	"Hospitality": [
		{"doctype": "Hotel Room", "index": 0},
		{"doctype": "Hotel Room Reservation", "index": 1},
		{"doctype": "Hotel Room Pricing", "index": 2},
		{"doctype": "Hotel Room Package", "index": 3},
		{"doctype": "Hotel Room Type", "index": 4},
	],
}

additional_timeline_content = {
	"*": ["erpnext.telephony.doctype.call_log.call_log.get_linked_call_logs"]
}
