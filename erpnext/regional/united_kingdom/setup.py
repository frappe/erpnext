# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import make_records


def setup(company=None, patch=True):
	add_custom_roles_for_reports()


def update_regional_tax_settings(country=None, company=None):
	"""Create UK VAT Tax Rules:-

	- UK Standard Rated Purchases
	- UK Reduced Rate Purchases
	- UK Zero Rated Purchases
	- UK Standard Rated Sales
	- UK Reduced Rate Sales
	- UK Zero Rated Sales
	- UK to EU Sales
	- UK to Rest of World Sales
	"""
	abbr = "UK"
	if company is not None:
		abbr = frappe.get_cached_value("Company", company, "abbr")
	tax_rules = [
		{
			"doctype": "Tax Rule",
			"name": "UK Standard Rated Purchases - " + abbr,
			"tax_type": "Purchase",
			"purchase_tax_template": frappe.db.get_value(
				"Purchase Taxes and Charges Template",
				{"title": "UK VAT Standard Rated", "company": company},
			),
			"use_for_shopping_cart": "1",
			"priority": "10",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"name": "UK Reduced Rate Purchases - " + abbr,
			"tax_type": "Purchase",
			"purchase_tax_template": frappe.db.get_value(
				"Purchase Taxes and Charges Template",
				{"title": "UK VAT Reduced Rate", "company": company},
			),
			"use_for_shopping_cart": "1",
			"priority": "20",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"name": "UK Zero Rated Purchases - " + abbr,
			"tax_type": "Purchase",
			"purchase_tax_template": frappe.db.get_value(
				"Purchase Taxes and Charges Template",
				{"title": "UK VAT Zero-Rated", "company": company},
			),
			"use_for_shopping_cart": "1",
			"priority": "30",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"name": "UK Standard Rated Sales - " + abbr,
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "UK VAT Standard Rated", "company": company},
			),
			"use_for_shopping_cart": "1",
			"priority": "10",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"name": "UK Reduced Rate Sales - " + abbr,
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "UK VAT Reduced Rate", "company": company},
			),
			"use_for_shopping_cart": "1",
			"priority": "20",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"name": "UK Zero Rated Sales - " + abbr,
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "UK VAT Zero-Rated", "company": company},
			),
			"use_for_shopping_cart": "1",
			"priority": "30",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"name": "UK to EU Sales - " + abbr,
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "UK VAT Outside Scope", "company": company},
			),
			"use_for_shopping_cart": "1",
			"tax_category": "VAT - EU Address",
			"priority": "40",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"name": "UK to Rest of World Sales - " + abbr,
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "UK VAT Outside Scope", "company": company},
			),
			"use_for_shopping_cart": "1",
			"tax_category": "VAT - Rest of World Address",
			"priority": "50",
			"company": company,
		},
	]
	# Setting the `in_import` flag to True allows us to apply the `name`
	frappe.flags.in_import = True
	try:
		make_records(tax_rules)
	finally:
		frappe.flags.in_import = False


def add_custom_roles_for_reports():
	"""Add Access Control to HMRC VAT Report."""
	if not frappe.db.get_value("Custom Role", dict(report="HMRC VAT")):
		frappe.get_doc(
			dict(
				doctype="Custom Role",
				report="HMRC VAT",
				roles=[dict(role="Accounts User"), dict(role="Accounts Manager"), dict(role="Auditor")],
			)
		).insert()
