import json

import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from lxml import etree


@frappe.whitelist()
def import_genericode():
	doctype = frappe.form_dict.doctype
	docname = frappe.form_dict.docname

	# Parse the uploaded file content
	parser = etree.XMLParser(remove_blank_text=True)
	try:
		root = etree.fromstring(frappe.local.uploaded_file, parser=parser)
	except Exception as e:
		frappe.throw(f"<pre>{e!s}</pre>", title=_("Parsing Error"))

	# Extract the name (CanonicalVersionUri) from the parsed XML
	name = root.find(".//CanonicalVersionUri").text

	if docname:
		code_list = frappe.get_doc(doctype, docname)
		if code_list.name != name:
			frappe.throw(_("The uploaded file does not match the selected Code List."))
	else:
		# Create a new Code List document with the extracted name
		code_list = frappe.new_doc(doctype)
		code_list.name = name
		code_list.insert(ignore_permissions=True)

	# Save the file using save_file utility
	file_doc = save_file(
		fname=frappe.local.uploaded_filename,
		content=frappe.local.uploaded_file,
		dt="Code List",
		dn=code_list.name,
		folder="Home/Attachments",
		is_private=1,
	)
	file_path = file_doc.get_full_path()

	# Get available columns and example values
	columns, example_values, filterable_columns = get_columns_and_examples(file_path)

	return {
		"code_list": code_list.name,
		"file_path": file_path,
		"columns": columns,
		"example_values": example_values,
		"filterable_columns": filterable_columns,
	}


@frappe.whitelist()
def process_genericode_import(
	code_list_name, file_path, code_column, title_column=None, description_column=None, filters=None
):
	code_list = frappe.get_doc("Code List", code_list_name)
	return code_list.import_genericode(
		file_path, code_column, title_column, description_column, filters and json.loads(filters)
	)


def get_columns_and_examples(file_path):
	parser = etree.XMLParser(remove_blank_text=True)
	tree = etree.parse(file_path, parser=parser)
	root = tree.getroot()

	columns = []
	example_values = {}
	filterable_columns = {}

	# Get column names
	for column in root.findall(".//Column"):
		column_id = column.get("Id")
		columns.append(column_id)
		example_values[column_id] = []
		filterable_columns[column_id] = set()

	# Get all values and count unique occurrences
	for row in root.findall(".//SimpleCodeList/Row"):
		for value in row.findall("Value"):
			column_id = value.get("ColumnRef")
			if column_id not in columns:
				# Handle undeclared column
				columns.append(column_id)
				example_values[column_id] = []
				filterable_columns[column_id] = set()

			value_text = value.find("./SimpleValue").text
			filterable_columns[column_id].add(value_text)

	# Get example values (up to 3) and filter columns with cardinality <= 5
	for row in root.findall(".//SimpleCodeList/Row")[:3]:
		for value in row.findall("Value"):
			column_id = value.get("ColumnRef")
			example_values[column_id].append(value.find("./SimpleValue").text)

	filterable_columns = {k: list(v) for k, v in filterable_columns.items() if len(v) <= 5}

	return columns, example_values, filterable_columns
