import frappe
from frappe.desk.page.setup_wizard.setup_wizard import make_records


def setup(company=None, patch=True):
	pass


def update_regional_tax_settings(country=None, company=None):
	# tax rules
	records = [
		{
			"doctype": "Tax Rule",
			"tax_type": "Purchase",
			"purchase_tax_template": frappe.db.get_value(
				"Purchase Taxes and Charges Template",
				{"title": "AU Capital Purchase - GST", "company": company},
			),
			"use_for_shopping_cart": "1",
			"tax_category": "Capital Goods Supplier",
			"priority": "10",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"tax_type": "Purchase",
			"purchase_tax_template": frappe.db.get_value(
				"Purchase Taxes and Charges Template",
				{"title": "Import & GST-Free Purchase", "company": company},
			),
			"use_for_shopping_cart": "1",
			"tax_category": "Import / GST Free Supplier",
			"priority": "20",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"tax_type": "Purchase",
			"purchase_tax_template": frappe.db.get_value(
				"Purchase Taxes and Charges Template",
				{"title": "AU Non Capital Purchase - GST", "company": company},
			),
			"use_for_shopping_cart": "1",
			"tax_category": "Domestic GST Supplier",
			"priority": "30",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "AU Sales - GST", "company": company},
			),
			"use_for_shopping_cart": "1",
			"tax_category": "Domestic GST Customer",
			"priority": "30",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "Export Sales - GST Free", "company": company},
			),
			"use_for_shopping_cart": "1",
			"tax_category": "Export Customer",
			"priority": "20",
			"company": company,
		},
		{
			"doctype": "Tax Rule",
			"tax_type": "Sales",
			"sales_tax_template": frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"title": "AU Sales - GST Free", "company": company},
			),
			"use_for_shopping_cart": "1",
			"tax_category": "GST Free Customer",
			"priority": "10",
			"company": company,
		},
	]

	make_records(records)
