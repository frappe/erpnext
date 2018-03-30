import frappe
import erpnext

def execute():
	frappe.reload_doc('portal', 'doctype', 'homepage_featured_product')
	frappe.reload_doc('portal', 'doctype', 'homepage')
	frappe.reload_doc('portal', 'doctype', 'products_settings')
	frappe.reload_doctype('Item')
	frappe.reload_doctype('Item Group')

	website_settings = frappe.get_doc('Website Settings', 'Website Settings')
	if frappe.db.exists('Web Page', website_settings.home_page):
		header = frappe.db.get_value('Web Page', website_settings.home_page, 'header')
		if header and header.startswith("<div class='hero text-center'>"):
			homepage = frappe.get_doc('Homepage', 'Homepage')
			homepage.company = erpnext.get_default_company() or frappe.get_all("Company")[0].name
			if '<h1>' in header:
				homepage.tag_line = header.split('<h1>')[1].split('</h1>')[0] or 'Default Website'
			else:
				homepage.tag_line = 'Default Website'
			homepage.setup_items()
			homepage.save()

			website_settings.home_page = 'home'
			website_settings.save()

