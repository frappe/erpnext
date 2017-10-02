import frappe

def execute():
	item_settings = frappe.get_single('Item Settings')
	item_settings.clean_description_html = 0
	item_settings.save()
