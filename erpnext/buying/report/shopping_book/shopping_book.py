# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _, msgprint

def execute(filters=None):
	if not filters: filters = {}

	columns = [
		_("Date") + "::100", _("RTN") + "::120", _("Supplier") + "::140", _("Document") + "::140", _("Print Authorization Code") + "::140",
		_("Total") + ":Currency:110", _("Total Exempt") + ":Currency:110", _("Base ISV 15%") + ":Currency:110", _("ISV 15%") + ":Currency:110", 
		_("Base ISV 18%") + ":Currency:110", _("ISV 18%") + ":Currency:110"
	]

	data = []
	conditions = return_filters(filters)
	shopping = frappe.get_all("Purchase Invoice", ["name", "posting_date", "supplier", "rtn_supplier", "bill_no", "cai", "grand_total"], filters = conditions)
	for item in shopping:
		result_tax_18 = 0
		taxes_calculate_15 = 0
		taxes_calculate_18 = 0
		base_15 = 0
		base_18 = 0
		total_exepmt = 0
		items = frappe.get_all("Purchase Invoice Item", ["item_tax_template", "amount"], filters = {"parent": item.name})
		for invoice_item in items:
			if invoice_item.item_tax_template == None:
				total_exepmt = item.grand_total
			tax_template = frappe.get_all("Item Tax Template", "name", filters = {"name": invoice_item.item_tax_template})
			for item_tax in tax_template:
				tax_rate = frappe.get_all("Item Tax Template Detail", filters = {"parent": item_tax.name}, fields={"tax_rate"})
				for rate in tax_rate:
					if rate.tax_rate == 15:
						taxes_calculate_15 += rate.tax_rate * invoice_item.amount / 100
						base_15 = item.grand_total - taxes_calculate_15
					elif rate.tax_rate == 18:
						taxes_calculate_18 += rate.tax_rate * invoice_item.amount / 100
						base_18 = item.grand_total - taxes_calculate_18

		row = [
			item.posting_date,
			item.rtn_supplier,
			item.supplier,
			item.bill_no,
			item.cai,
			item.grand_total,
			total_exepmt,
			base_15,
			taxes_calculate_15,
			base_18,
			taxes_calculate_18,
		]
		data.append(row)
	return columns, data

def return_filters(filters):
	conditions = ''

	conditions += "{"
	if filters.get("company"): conditions += '"company": "{}"'.format(filters.get("company"))
	if filters.get("from_date") and filters.get("to_date"):conditions += ', "posting_date": [">=", "{}"], "modified": ["<=", "{}"]'.format(filters.get("from_date"), filters.get("to_date"))
	conditions += '}'

	return conditions
