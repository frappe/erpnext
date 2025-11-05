# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import make_records


def setup(company=None, patch=True):
	pass


def update_regional_tax_settings(country=None, company=None):
	"""Create UK VAT Tax Rules:-

	- UK Domestic Purchases
	- UK Domestic Sales
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
			"tax_category": "UK Export Customer - EU",
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
			"tax_category": "UK Export Customer - Rest of World",
			"priority": "50",
			"company": company,
		},
	]
	make_records(tax_rules)
	# The names aren't applied, as Tax Rule has an Autoname rule. However,
	# renaming is allowed...
	docs = frappe.get_all("Tax Rule", filters={"company": company}, fields=["name"], order_by="creation asc")
	for i, tax_rule in enumerate(tax_rules):
		frappe.rename_doc("Tax Rule", docs[i].name, tax_rule["name"])
