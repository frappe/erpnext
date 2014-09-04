import frappe
from frappe.templates.pages.style_settings import default_properties

def execute():
	style_settings = frappe.get_doc("Style Settings", "Style Settings")
	if not style_settings.apply_style:
		style_settings.update(default_properties)
		style_settings.apply_style = 1
		style_settings.save()
