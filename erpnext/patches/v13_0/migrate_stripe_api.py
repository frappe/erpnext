import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("accounts", "doctype", "subscription_plan")
	rename_field("Subscription Plan", "payment_plan_id", "product_price_id")
