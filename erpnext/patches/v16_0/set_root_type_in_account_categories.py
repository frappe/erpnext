import json
import os

import frappe


def execute():
	module_path = frappe.get_module_path("Accounts")
	categories_file = os.path.join(module_path, "financial_report_template", "account_categories.json")

	if not os.path.exists(categories_file):
		return

	with open(categories_file) as f:
		categories = json.load(f)

	root_type_categories = {}
	for category in categories:
		if root_type := category.get("root_type"):
			root_type_categories.setdefault(root_type, []).append(category["account_category_name"])

	if not root_type_categories:
		return

	for root_type, category_names in root_type_categories.items():
		frappe.db.set_value(
			"Account Category",
			{"name": ["in", category_names], "root_type": ["is", "not set"]},
			"root_type",
			root_type,
		)
