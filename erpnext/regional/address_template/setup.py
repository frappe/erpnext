"""Import Address Templates from ./templates directory."""
import os
import frappe


def set_up_address_templates(default_country=None):
	for country, html in get_address_templates():
		is_default = 1 if country == default_country else 0
		update_address_template(country, html, is_default)


def get_address_templates():
	"""
	Return country and path for all HTML files in this directory.

	Returns a list of dicts.
	"""

	def country(file_name):
		"""Convert 'united_states.html' to 'United States'."""
		suffix_pos = file_name.find(".html")
		country_snake_case = file_name[:suffix_pos]
		country_title_case = " ".join(country_snake_case.split("_")).title()
		return country_title_case

	def get_file_content(file_name):
		"""Convert 'united_states.html' to '/path/to/united_states.html'."""
		full_path = os.path.join(template_dir, file_name)
		with open(full_path, "r") as f:
			content = f.read()
		return content

	dir_name = os.path.dirname(__file__)
	template_dir = os.path.join(dir_name, "templates")
	file_names = os.listdir(template_dir)
	html_files = [file for file in file_names if file.endswith(".html")]

	return [(country(file_name), get_file_content(file_name)) for file_name in html_files]


def update_address_template(country, html, is_default=0):
	"""Update existing Address Template or create a new one."""
	if not frappe.db.exists("Country", country):
		frappe.log_error("Country {} for regional Address Template does not exist.".format(country))
		return

	if frappe.db.exists("Address Template", country):
		frappe.db.set_value("Address Template", country, "template", html)
		frappe.db.set_value("Address Template", country, "is_default", is_default)
	else:
		frappe.get_doc(
			dict(doctype="Address Template", country=country, is_default=is_default, template=html)
		).insert()
