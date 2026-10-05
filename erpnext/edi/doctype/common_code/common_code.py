# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import get_link_to_form
from lxml import etree

from erpnext.edi.doctype.code_list.code_list_import import parse_genericode_content


class CommonCode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.dynamic_link.dynamic_link import DynamicLink
		from frappe.types import DF

		additional_data: DF.Code | None
		applies_to: DF.Table[DynamicLink]
		canonical_uri: DF.Data | None
		code_list: DF.Link
		common_code: DF.Data
		description: DF.SmallText | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_distinct_references()

	def validate_distinct_references(self):
		"""Ensure no two Common Codes of the same Code List are linked to the same document."""
		for link in self.applies_to:
			existing_links = frappe.get_all(
				"Common Code",
				filters=[
					["name", "!=", self.name],
					["code_list", "=", self.code_list],
					["Dynamic Link", "link_doctype", "=", link.link_doctype],
					["Dynamic Link", "link_name", "=", link.link_name],
				],
				fields=["name", "common_code"],
			)

			if existing_links:
				existing_link = existing_links[0]
				frappe.throw(
					_("{0} {1} is already linked to Common Code {2}.").format(
						link.link_doctype,
						link.link_name,
						get_link_to_form("Common Code", existing_link["name"], existing_link["common_code"]),
					)
				)

	def from_genericode(self, column_map: dict, xml_element: "etree.Element"):
		"""Populate the Common Code document from a genericode XML element

		Args:
		    column_map (dict): A mapping of column names to XML column references. Keys: code, title, description
		    code (etree.Element): The XML element representing a code in the genericode file
		"""
		title_column = column_map.get("title")
		code_column = column_map["code"]
		description_column = column_map.get("description")

		self.common_code = get_simple_value(xml_element, code_column).text

		if title_column:
			simple_value_title = get_simple_value(xml_element, title_column)
			self.title = simple_value_title.text if simple_value_title is not None else self.common_code

		if description_column:
			simple_value_descr = get_simple_value(xml_element, description_column)
			self.description = simple_value_descr.text if simple_value_descr is not None else None

		self.additional_data = etree.tostring(xml_element, encoding="unicode", pretty_print=True)


def simple_hash(input_string, length=6):
	return hashlib.blake2b(input_string.encode(), digest_size=length // 2).hexdigest()


def import_genericode(code_list: str, file_name: str, column_map: dict, filters: dict | None = None):
	"""Import genericode file and create Common Code entries"""
	file_doc = frappe.get_doc("File", file_name)
	file_doc.check_permission("read")
	root = parse_genericode_content(file_doc.get_content(encodings=()))

	elements = get_filtered_rows(root, filters or {})
	total_elements = len(elements)
	for i, xml_element in enumerate(elements, start=1):
		code = get_row_code(xml_element, column_map["code"], i)
		common_code = get_common_code(code_list, code)
		common_code.from_genericode(column_map, xml_element)
		common_code.save()
		frappe.publish_progress(i / total_elements * 100, title=_("Importing Common Codes"))

	return total_elements


def get_row_code(xml_element: "etree.Element", code_column: str, row_number: int) -> str:
	code = getattr(get_simple_value(xml_element, code_column), "text", None)
	if not code:
		frappe.throw(
			_("Row {0} has no value in the code column {1}").format(row_number, frappe.bold(code_column))
		)

	return code


def get_common_code(code_list: str, code: str) -> CommonCode:
	"""Return the list's existing Common Code for the code, so a re-import updates it."""
	if name := frappe.db.get_value("Common Code", {"code_list": code_list, "common_code": code}):
		return frappe.get_doc("Common Code", name)

	common_code = frappe.new_doc("Common Code")
	common_code.code_list = code_list
	return common_code


def get_filtered_rows(root: "etree.Element", filters: dict) -> list:
	"""Return the rows matching every column = value filter, passed as XPath variables."""
	conditions, variables = [], {}
	for i, (column_ref, value) in enumerate(filters.items()):
		conditions.append(f"Value[@ColumnRef=$column{i}]/SimpleValue=$value{i}")
		variables.update({f"column{i}": column_ref, f"value{i}": value})

	predicate = "[" + " and ".join(conditions) + "]" if conditions else ""
	return root.xpath(f".//SimpleCodeList/Row{predicate}", **variables)


def get_simple_value(xml_element: "etree.Element", column_ref: str) -> "etree.Element | None":
	values = xml_element.xpath("./Value[@ColumnRef=$column]/SimpleValue", column=column_ref)
	return values[0] if values else None


def on_doctype_update():
	frappe.db.add_index("Common Code", ["code_list", "common_code"])
