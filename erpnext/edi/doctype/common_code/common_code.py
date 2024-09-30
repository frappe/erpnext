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
		title: DF.Data | None
	# end: auto-generated types

	@staticmethod
	def simple_hash(input_string, length=6):
		return hashlib.blake2b(input_string.encode(), digest_size=length // 2).hexdigest()

	def autoname(self):
		self.name = self.simple_hash(self.code_list) + "|" + self.simple_hash(self.common_code, 10)

	def validate(self):
		self.validate_unique_code()
		self.validate_distinct_references()

	def validate_unique_code(self):
		"""Ensure the same Common Code does not appear twice in the same Code List."""
		if frappe.db.exists(
			"Common Code",
			{"code_list": self.code_list, "common_code": self.common_code, "name": ("!=", self.name)},
		):
			frappe.throw(
				_("Common Code {0} already exists in Code List {1}").format(self.common_code, self.code_list)
			)

	def validate_distinct_references(self):
		"""Ensure the same reference is not used on a different Common Code of the same Code List."""
		for link in self.applies_to:
			existing_links = frappe.get_all(
				"Common Code",
				filters=[
					["common_code", "!=", self.common_code],
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
	def import_genericode(file_path, list_name, code_column, title_column=None, filters=None):
		parser = etree.XMLParser(remove_blank_text=True)
		tree = etree.parse(file_path, parser=parser)
		root = tree.getroot()

		codes = []
		seen_common_codes = set()
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
			if code_value in seen_common_codes:
				frappe.throw(
					_(
						"Duplicate value found for '{}':\n\n<pre><code class='language-xml'>{}</code></pre>"
					).format(code_column, escape_html(content))
				)
			seen_common_codes.add(code_value)
			code_hash = CommonCode.simple_hash(code_value, 10)

			title = None
			if title_column:
				title = code.find(f"./Value[@ColumnRef='{title_column}']/SimpleValue").text

			codes.append(
				{
					"name": f"{list_hash}|{code_hash}|{idx}",  # according to autoname + row index
					"code_list": list_name,
					"common_code": code_value,
					"title": title,
					"additional_data": content,
				}
			)

		return codes


def on_doctype_update():
	frappe.db.add_unique(
		"Common Code", ["code_list", "common_code"], constraint_name="unique_code_list_common_code"
	)
	frappe.db.add_index("Common Code", ["code_list", "common_code"])
