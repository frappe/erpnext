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
    tax_rules = [
		{
			"doctype": "Tax Rule",
            "title": "UK Standard Rated Purchases",
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
            "title": "UK Reduced Rate Purchases",
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
            "title": "UK Zero Rated Purchases",
			"tax_type": "Purchase",
			"purchase_tax_template": frappe.db.get_value(
				"Purchase Taxes and Charges Template",
				{"title": "UK VAT Zero Rated", "company": company},
			),
			"use_for_shopping_cart": "1",
			"priority": "30",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
            "title": "UK Standard Rated Sales",
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
            "title": "UK Reduced Rate Sales",
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
            "title": "UK Zero Rated Sales",
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "UK VAT Zero Rated", "company": company},
			),
			"use_for_shopping_cart": "1",
			"priority": "30",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
            "title": "UK to EU Sales",
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
            "title": "UK to Rest of World Sales",
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
