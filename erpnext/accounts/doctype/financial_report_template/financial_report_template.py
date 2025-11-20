# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import shutil

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.accounts.doctype.account_category.account_category import import_account_categories
from erpnext.accounts.doctype.financial_report_template.financial_report_validation import TemplateValidator


class FinancialReportTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.financial_report_row.financial_report_row import FinancialReportRow

		disabled: DF.Check
		module: DF.Link | None
		report_type: DF.Literal[
			"", "Profit and Loss Statement", "Balance Sheet", "Cash Flow", "Custom Financial Statement"
		]
		rows: DF.Table[FinancialReportRow]
		template_name: DF.Data
	# end: auto-generated types

	def validate(self):
		validator = TemplateValidator(self)
		result = validator.validate()
		result.notify_user()

	def on_update(self):
		self._export_template()

	def on_trash(self):
		self._delete_template()

	def _export_template(self):
		from frappe.modules.utils import export_module_json

		if not self.module:
			return

		export_module_json(self, True, self.module)
		self._export_account_categories()

	def _delete_template(self):
		if not self.module or not frappe.conf.developer_mode:
			return

		module_path = frappe.get_module_path(self.module)
		dir_path = os.path.join(module_path, "financial_report_template", frappe.scrub(self.name))

		shutil.rmtree(dir_path, ignore_errors=True)

	def _export_account_categories(self):
		import json

		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			FormulaFieldExtractor,
		)

		if not self.module or not frappe.conf.developer_mode or frappe.flags.in_import:
			return

		# Extract category from rows
		extractor = FormulaFieldExtractor(
			field_name="account_category", exclude_operators=["like", "not like"]
		)
		account_data_rows = [row for row in self.rows if row.data_source == "Account Data"]
		category_names = extractor.extract_from_rows(account_data_rows)

		if not category_names:
			return

		# Get path
		module_path = frappe.get_module_path(self.module)
		categories_file = os.path.join(module_path, "financial_report_template", "account_categories.json")

		# Load existing categories
		existing_categories = {}
		if os.path.exists(categories_file):
			try:
				with open(categories_file) as f:
					existing_data = json.load(f)
					existing_categories = {cat["account_category_name"]: cat for cat in existing_data}
			except (json.JSONDecodeError, KeyError):
				pass  # Create new file

		# Fetch categories from database
		if category_names:
			db_categories = frappe.get_all(
				"Account Category",
				filters={"account_category_name": ["in", list(category_names)]},
				fields=["account_category_name", "description"],
			)

			for cat in db_categories:
				existing_categories[cat["account_category_name"]] = cat

		# Sort by category name
		sorted_categories = sorted(existing_categories.values(), key=lambda x: x["account_category_name"])

		# Write to file
		os.makedirs(os.path.dirname(categories_file), exist_ok=True)
		with open(categories_file, "w") as f:
			json.dump(sorted_categories, f, indent=2)


def sync_financial_report_templates(chart_of_accounts=None, existing_company=None):
	from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import get_chart

	# If COA is being created for an existing company,
	# skip syncing templates as they are likely already present
	if existing_company:
		return

	# Allow regional templates to completely override ERPNext
	# templates based on the chart of accounts selected
	disable_default_financial_report_template = False
	if chart_of_accounts:
		coa = get_chart(chart_of_accounts)
		if coa.get("disable_default_financial_report_template", False):
			disable_default_financial_report_template = True

	installed_apps = frappe.get_installed_apps()

	for app in installed_apps:
		if disable_default_financial_report_template and app == "erpnext":
			continue

		_sync_templates_for(app)


def _sync_templates_for(app_name):
	templates = []

	for module_name in frappe.local.app_modules.get(app_name) or []:
		module_path = frappe.get_module_path(module_name)
		template_path = os.path.join(module_path, "financial_report_template")

		if not os.path.isdir(template_path):
			continue

		import_account_categories(template_path)

		for template_dir in os.listdir(template_path):
			json_file = os.path.join(template_path, template_dir, f"{template_dir}.json")
			if os.path.isfile(json_file):
				templates.append(json_file)

	if not templates:
		return

	# ensure files are not exported
	frappe.flags.in_import = True

	for template_path in templates:
		with open(template_path) as f:
			template_data = frappe._dict(frappe.parse_json(f.read()))

		template_name = template_data.get("name")

		if not frappe.db.exists("Financial Report Template", template_name):
			doc = frappe.get_doc(template_data)
			doc.flags.ignore_mandatory = True
			doc.flags.ignore_permissions = True
			doc.flags.ignore_validate = True
			doc.insert()

	frappe.flags.in_import = False
