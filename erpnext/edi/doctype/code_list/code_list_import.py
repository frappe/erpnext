import json
from urllib.parse import urlsplit

import frappe
import requests
from frappe import _
from frappe.utils import escape_html
from lxml import etree

GENERICODE_FETCH_TIMEOUT = 15
LOCAL_FILE_PREFIXES = ("/files/", "/private/files/")


class RemoteGenericodeUrlNotAllowedError(Exception):
	pass


class CodeListSelectionMismatchError(Exception):
	pass


@frappe.whitelist()
def import_genericode():
	try:
		content, file_name, file_url = get_uploaded_genericode_file()

		return import_genericode_content(
			doctype=frappe.form_dict.doctype,
			docname=frappe.form_dict.docname,
			content=content,
			file_name=file_name,
			file_url=file_url,
		)
	except RemoteGenericodeUrlNotAllowedError:
		frappe.throw(
			_("Importing Code Lists from remote URLs is not allowed."),
			title=_("Invalid Upload"),
		)
	except CodeListSelectionMismatchError:
		frappe.throw(_("The uploaded file does not match the selected Code List."))
	except etree.XMLSyntaxError:
		frappe.throw(
			_("The uploaded file could not be parsed as a genericode XML document."),
			title=_("Parsing Error"),
		)


def import_genericode_from_url(
	url: str,
	doctype: str = "Code List",
	docname: str | None = None,
):
	"""Import a Code List from a trusted backend URL."""
	content = fetch_genericode_from_url(url)
	file_name = urlsplit(url).path.rsplit("/", 1)[-1] or "genericode.xml"

	return import_genericode_content(
		doctype=doctype,
		docname=docname,
		content=content,
		file_name=file_name,
		file_url=None,
	)


def get_uploaded_genericode_file() -> tuple[bytes, str | None, str | None]:
	content = frappe.local.uploaded_file
	file_name = frappe.local.uploaded_filename
	file_url = frappe.local.uploaded_file_url

	if file_url and not is_local_file_url(file_url):
		raise RemoteGenericodeUrlNotAllowedError

	if file_url:
		file_path = frappe.utils.file_manager.get_file_path(file_url)
		with open(file_path, mode="rb") as file:
			content = file.read()

	return content, file_name, file_url


def is_local_file_url(file_url: str | None) -> bool:
	if not file_url:
		return False

	parsed = urlsplit(file_url.strip())
	return not parsed.scheme and not parsed.netloc and parsed.path.startswith(LOCAL_FILE_PREFIXES)


def fetch_genericode_from_url(url: str) -> bytes:
	response = requests.get(url, timeout=GENERICODE_FETCH_TIMEOUT)
	response.raise_for_status()
	return response.content


def import_genericode_content(
	doctype: str,
	docname: str | None,
	content: bytes,
	file_name: str | None,
	file_url: str | None,
):
	root = parse_genericode_content(content)

	# Extract the name (CanonicalVersionUri) from the parsed XML
	name = root.find(".//CanonicalVersionUri").text
	docname = docname or name

	if frappe.db.exists(doctype, docname):
		code_list = frappe.get_doc(doctype, docname)
		if code_list.name != name:
			raise CodeListSelectionMismatchError
	else:
		# Create a new Code List document with the extracted name
		code_list = frappe.new_doc(doctype)
		code_list.name = name

	code_list.from_genericode(root)
	code_list.save()

	file_doc = attach_import_file(
		doctype=doctype,
		docname=code_list.name,
		file_name=file_name,
		file_url=file_url,
		content=content,
	)

	# Get available columns and example values
	columns, example_values, filterable_columns = get_genericode_columns_and_examples(root)

	return {
		"code_list": code_list.name,
		"code_list_title": code_list.title,
		"file": file_doc.name,
		"columns": columns,
		"example_values": example_values,
		"filterable_columns": filterable_columns,
	}


def parse_genericode_content(content: bytes):
	parser = etree.XMLParser(
		remove_blank_text=True,
		resolve_entities=False,
		load_dtd=False,
		no_network=True,
	)
	return etree.fromstring(content, parser=parser)


def attach_import_file(
	doctype: str,
	docname: str,
	file_name: str | None,
	file_url: str | None,
	content: bytes,
):
	# Attach the file and provide a recoverable identifier.
	return frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
			"folder": frappe.db.get_value("File", {"is_attachments_folder": 1}),
			"file_name": file_name or "genericode.xml",
			"file_url": file_url,
			"is_private": 1,
			"content": content,
		}
	).save()


@frappe.whitelist()
def process_genericode_import(
	code_list_name: str,
	file_name: str,
	code_column: str,
	title_column: str | None = None,
	description_column: str | None = None,
	filters: str | None = None,
):
	from erpnext.edi.doctype.common_code.common_code import import_genericode

	column_map = {"code": code_column, "title": title_column, "description": description_column}

	return import_genericode(code_list_name, file_name, column_map, json.loads(filters) if filters else None)


def get_genericode_columns_and_examples(root):
	columns = []
	example_values = {}
	filterable_columns = {}

	# Get column names
	for column in root.findall(".//Column"):
		column_id = escape_html(column.get("Id"))
		columns.append(column_id)
		example_values[column_id] = []
		filterable_columns[column_id] = set()

	# Get all values and count unique occurrences
	for row in root.findall(".//SimpleCodeList/Row"):
		for value in row.findall("Value"):
			column_id = escape_html(value.get("ColumnRef"))
			if column_id not in columns:
				# Handle undeclared column
				columns.append(column_id)
				example_values[column_id] = []
				filterable_columns[column_id] = set()

			simple_value = value.find("./SimpleValue")
			if simple_value is None:
				continue

			filterable_columns[column_id].add(escape_html(simple_value.text))

	# Get example values (up to 3) and filter columns with cardinality <= 5
	for row in root.findall(".//SimpleCodeList/Row")[:3]:
		for value in row.findall("Value"):
			column_id = value.get("ColumnRef")
			simple_value = value.find("./SimpleValue")
			if simple_value is None:
				continue

			example_values[column_id].append(escape_html(simple_value.text))

	filterable_columns = {k: list(v) for k, v in filterable_columns.items() if len(v) <= 5}

	return columns, example_values, filterable_columns
