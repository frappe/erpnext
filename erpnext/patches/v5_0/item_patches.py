import frappe

def execute():
	frappe.db.sql("update `tabItem` set end_of_life='2099-12-31' where ifnull(end_of_life, '0000-00-00')='0000-00-00'")
	frappe.db.sql("update `tabItem` set website_image = image where ifnull(website_image, '') = 'attach_files:'")
