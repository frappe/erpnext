# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import get_link_to_form
from lxml import etree


class CommonCode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.dynamic_link.dynamic_link import DynamicLink
		from frappe.types import DF

		additional_data: DF.Code | None
		applies_to: DF.Table[DynamicLink]
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

		self.common_code = xml_element.find(f"./Value[@ColumnRef='{code_column}']/SimpleValue").text

		if title_column:
			simple_value_title = xml_element.find(f"./Value[@ColumnRef='{title_column}']/SimpleValue")
			self.title = simple_value_title.text if simple_value_title is not None else self.common_code

		if description_column:
			simple_value_descr = xml_element.find(f"./Value[@ColumnRef='{description_column}']/SimpleValue")
			self.description = simple_value_descr.text if simple_value_descr is not None else None

		self.additional_data = etree.tostring(xml_element, encoding="unicode", pretty_print=True)


def simple_hash(input_string, length=6):
	return hashlib.blake2b(input_string.encode(), digest_size=length // 2).hexdigest()


def import_genericode(code_list: str, file_name: str, column_map: dict, filters: dict | None = None):
	"""Import genericode file and create Common Code entries"""
	file_path = frappe.utils.file_manager.get_file_path(file_name)
	parser = etree.XMLParser(remove_blank_text=True)
	tree = etree.parse(file_path, parser=parser)
	root = tree.getroot()

	# Construct the XPath expression
	xpath_expr = ".//SimpleCodeList/Row"
	filter_conditions = [
		f"Value[@ColumnRef='{column_ref}']/SimpleValue='{value}'" for column_ref, value in filters.items()
	]
	if filter_conditions:
		xpath_expr += "[" + " and ".join(filter_conditions) + "]"

	elements = root.xpath(xpath_expr)
	total_elements = len(elements)
	for i, xml_element in enumerate(elements, start=1):
		common_code: "CommonCode" = frappe.new_doc("Common Code")
		common_code.code_list = code_list
		common_code.from_genericode(column_map, xml_element)
		common_code.save()
		frappe.publish_progress(i / total_elements * 100, title=_("Importing Common Codes"))

	return total_elements


def on_doctype_update():
	frappe.db.add_index("Common Code", ["code_list", "common_code"])
