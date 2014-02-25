import frappe
import frappe.model

def execute():
	frappe.reload_doc("setup", "doctype", "item_group")
	frappe.reload_doc("stock", "doctype", "item")
	frappe.reload_doc("setup", "doctype", "sales_partner")
	frappe.model.rename_field("Item Group", "parent_website_sitemap", "parent_website_route")
	frappe.model.rename_field("Item", "parent_website_sitemap", "parent_website_route")
	frappe.model.rename_field("Sales Partner", "parent_website_sitemap",
		 "parent_website_route")
