"""Import Address Templates from ./templates directory."""
import os
import frappe

def setup(installation_country):
	for template in get_address_templates():
		html = get_file_content(template.get("path"))
		update_address_template(template.get("country"), html)

	if frappe.db.exists("Address Template", installation_country):
		# make this the default template
		doc = frappe.get_doc("Address Template", installation_country)
		doc.is_default = 1
		doc.save()
	else:
		# use erpnext's default template
		doc = frappe.new_doc("Address Template")
		doc.country = installation_country
		doc.is_default = 1
		doc.insert()

def get_address_templates():
	"""
	Return country and path for all HTML files in this directory.
	
	Returns a list of dicts.
	"""
	def full_path(file):
		# united_states.html -> /path/to/united_states.html
		return os.path.join(template_dir, file)

	def country(file):
		# united_states.html -> United States
		return " ".join(file[:file.find(".html")].split("_")).title()

	dir_name = os.path.dirname(__file__)
	template_dir = os.path.join(dir_name, "templates")
	file_names = os.listdir(template_dir)
	html_files = [file for file in file_names if file.endswith(".html")]

	return [dict(
		country=country(file),
		path=full_path(file)
	 ) for file in html_files]

def get_file_content(path):
	"""Return the content of the file at path."""
	with open(path, "r") as f:
		content = f.read()

	return content

def update_address_template(country, html):
	"""Update existing Address Template or create a new one."""
	if frappe.db.exists("Address Template", country):
		frappe.db.set_value("Address Template", country, "template", html)
	else:
		frappe.get_doc(dict(
			doctype="Address Template",
			country=country,
			html=html,
			is_default=0
		)).insert()
