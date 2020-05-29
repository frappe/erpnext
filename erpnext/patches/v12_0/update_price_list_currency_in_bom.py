from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, flt
from erpnext.setup.utils import get_exchange_rate

def execute():
	frappe.reload_doc("manufacturing", "doctype", "bom")
	frappe.reload_doc("manufacturing", "doctype", "bom_item")

	frappe.db.sql(""" UPDATE `tabBOM`, `tabPrice List`
		SET
			`tabBOM`.price_list_currency = `tabPrice List`.currency,
			`tabBOM`.plc_conversion_rate = 1.0
		WHERE
			`tabBOM`.buying_price_list = `tabPrice List`.name AND `tabBOM`.docstatus < 2
			AND `tabBOM`.rm_cost_as_per = 'Price List'
	""")

	for d in frappe.db.sql("""
		SELECT
			bom.creation, bom.name, bom.price_list_currency as currency,
			company.default_currency as company_currency
		FROM
			`tabBOM` as bom, `tabCompany` as company
		WHERE
			bom.company = company.name AND bom.rm_cost_as_per = 'Price List' AND
			bom.price_list_currency != company.default_currency AND bom.docstatus < 2""", as_dict=1):
			plc_conversion_rate = get_exchange_rate(d.currency,
				d.company_currency, getdate(d.creation), "for_buying")

			frappe.db.set_value("BOM", d.name, "plc_conversion_rate", plc_conversion_rate)