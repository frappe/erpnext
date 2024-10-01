# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import get_link_to_form
from frappe.utils.html_utils import escape_html
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
		title: DF.Data | None
	# end: auto-generated types

	@staticmethod
	def simple_hash(input_string, length=6):
		return hashlib.blake2b(input_string.encode(), digest_size=length // 2).hexdigest()

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

	@staticmethod
	def import_genericode(
		file_name, list_name, code_column, title_column=None, description_column=None, filters=None
	):
		file_path = frappe.utils.file_manager.get_file_path(file_name)
		parser = etree.XMLParser(remove_blank_text=True)
		tree = etree.parse(file_path, parser=parser)
		root = tree.getroot()

		codes = []
		list_hash = CommonCode.simple_hash(list_name)

		# Construct the XPath expression
		xpath_expr = ".//SimpleCodeList/Row"
		filter_conditions = []
		for column_ref, value in filters.items():
			filter_conditions.append(f"Value[@ColumnRef='{column_ref}']/SimpleValue='{value}'")
		if filter_conditions:
			xpath_expr += "[" + " and ".join(filter_conditions) + "]"

		for idx, code in enumerate(root.xpath(xpath_expr)):
			content = etree.tostring(code, encoding="unicode", pretty_print=True)

			code_value = code.find(f"./Value[@ColumnRef='{code_column}']/SimpleValue").text
			code_hash = CommonCode.simple_hash(code_value, 10)

			title = None
			if title_column:
				title = code.find(f"./Value[@ColumnRef='{title_column}']/SimpleValue").text

			description = None
			if description_column:
				description = code.find(f"./Value[@ColumnRef='{description_column}']/SimpleValue").text

			codes.append(
				{
					"name": f"{list_hash}|{idx}|{code_hash}",
					"code_list": list_name,
					"common_code": code_value,
					"title": title,
					"description": description,
					"additional_data": content,
				}
			)

		return codes


def on_doctype_update():
	frappe.db.add_index("Common Code", ["code_list", "common_code"])
