import os
import frappe


def setup(company=None, patch=True):
	if not patch:
		update_address_template()


def update_address_template():
	"""
	Read address template from file. Update existing Address Template or create a
	new one.
	"""
	dir_name = os.path.dirname(__file__)
	template_path = os.path.join(dir_name, 'address_template.html')

	with open(template_path, 'r') as template_file:
		template_html = template_file.read()

	address_template = frappe.db.get_value('Address Template', 'Germany')

	if address_template:
		frappe.db.set_value('Address Template', 'Germany', 'template', template_html)
	else:
		# make new html template for Germany
		frappe.get_doc(dict(
			doctype='Address Template',
			country='Germany',
			template=template_html
		)).insert()
