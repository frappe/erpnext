# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AccountCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_category_name: DF.Data
		description: DF.SmallText | None
		is_system_generated: DF.Check
		module: DF.Link | None
	# end: auto-generated types

	pass


def create_default_account_categories():
	default_categories = frappe.get_file_json(
		frappe.get_app_path(
			"erpnext", "accounts", "doctype", "account_category", "default_account_categories.json"
		)
	)

	create_account_categories(default_categories, is_system_generated=True)


def create_account_categories(categories: list[dict], is_system_generated: bool = True):
	if not categories:
		return

	existing_categories = set(frappe.get_all("Account Category", pluck="name"))

	for category_data in categories:
		category_name = category_data.get("account_category_name")
		if not category_name or category_name in existing_categories:
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Account Category",
				**category_data,
				"is_system_generated": is_system_generated,
			}
		)
		doc.insert(ignore_permissions=True)
		existing_categories.add(category_name)
