# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import json
import os

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
	# end: auto-generated types


def import_account_categories(template_path: str):
	categories_file = os.path.join(template_path, "account_categories.json")

	if not os.path.exists(categories_file):
		return

	with open(categories_file) as f:
		categories = json.load(f, object_hook=frappe._dict)

	create_account_categories(categories)


def create_account_categories(categories: list[dict]):
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
			}
		)
		doc.insert(ignore_permissions=True)
		existing_categories.add(category_name)
