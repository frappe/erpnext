import json
from pathlib import Path

import frappe


def execute():
	base_path = Path(frappe.get_app_path("erpnext", "accounts")).resolve()
	categories_file = (base_path / "financial_report_template" / "account_categories.json").resolve()

	if not categories_file.exists():
		return

	categories = json.loads(frappe.read_file(str(categories_file)))

	valid_root_types = set(frappe.get_meta("Account Category").get_field("root_type").options.split("\n"))

	root_type_categories = {}
	for category in categories:
		if (root_type := category.get("root_type")) and root_type in valid_root_types:
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
