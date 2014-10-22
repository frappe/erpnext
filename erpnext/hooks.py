app_name = "erpnext"
app_title = "ERPNext"
app_publisher = "Web Notes Technologies Pvt. Ltd. and Contributors"
app_description = "Open Source Enterprise Resource Planning for Small and Midsized Organizations"
app_icon = "icon-th"
app_color = "#e74c3c"
app_version = "5.0.0-alpha"

error_report_email = "support@erpnext.com"

app_include_js = "assets/js/erpnext.min.js"
app_include_css = "assets/css/erpnext.css"
web_include_js = "assets/js/erpnext-web.min.js"
web_include_css = "assets/css/shopping-cart-web.css"

after_install = "erpnext.setup.install.after_install"

boot_session = "erpnext.startup.boot.boot_session"
notification_config = "erpnext.startup.notifications.get_notification_config"

on_session_creation = "erpnext.shopping_cart.utils.set_cart_count"
on_logout = "erpnext.shopping_cart.utils.clear_cart_count"
update_website_context = ["erpnext.shopping_cart.utils.update_website_context", "erpnext.startup.webutils.update_website_context"]

dump_report_map = "erpnext.startup.report_data_map.data_map"

before_tests = "erpnext.setup.utils.before_tests"

website_generators = ["Item Group", "Item", "Sales Partner"]

standard_queries = "Customer:erpnext.selling.doctype.customer.customer.get_customer_list"

communication_covert_to = ["Lead", "Support Ticket", "Job Application"]

doc_events = {
	"Stock Entry": {
		"on_submit": "erpnext.stock.doctype.material_request.material_request.update_completed_qty",
		"on_cancel": "erpnext.stock.doctype.material_request.material_request.update_completed_qty"
	},
	"User": {
		"validate": "erpnext.hr.doctype.employee.employee.validate_employee_role",
		"on_update": "erpnext.hr.doctype.employee.employee.update_user_permissions"
	},
	"Sales Taxes and Charges Master": {
		"on_update": "erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings.validate_cart_settings"
	},
	"Price List": {
		"on_update": "erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings.validate_cart_settings"
	},
}

scheduler_events = {
	"daily": [
		"erpnext.controllers.recurring_document.create_recurring_documents",
		"erpnext.stock.reorder_item.reorder_item",
		"erpnext.setup.doctype.email_digest.email_digest.send",
		"erpnext.support.doctype.support_ticket.support_ticket.auto_close_tickets",
		"erpnext.accounts.doctype.fiscal_year.fiscal_year.auto_create_fiscal_year"
	],
	"daily_long": [
		"erpnext.setup.doctype.backup_manager.backup_manager.take_backups_daily"
	],
	"weekly_long": [
		"erpnext.setup.doctype.backup_manager.backup_manager.take_backups_weekly"
	]
}

default_mail_footer = """<div style="padding: 7px; text-align: right;">
	<a style="color: #888; font-size: 80%;" href="https://erpnext.com">Sent via ERPNext</a></div>"""
