from __future__ import unicode_literals
import frappe
from erpnext import get_default_currency

def execute():
	frappe.reload_doc("manufacturing", "doctype", "bom")
	frappe.reload_doc("manufacturing", "doctype", "bom_item")
	frappe.reload_doc("manufacturing", "doctype", "bom_explosion_item")
	frappe.reload_doc("manufacturing", "doctype", "bom_operation")
	frappe.reload_doc("manufacturing", "doctype", "bom_scrap_item")

	frappe.db.sql(""" update `tabBOM Operation` set base_hour_rate = hour_rate,
		base_operating_cost = operating_cost """)

	frappe.db.sql(""" update `tabBOM Item` set base_rate = rate, base_amount = amount """)
	frappe.db.sql(""" update `tabBOM Scrap Item` set base_rate = rate, base_amount = amount """)

	frappe.db.sql(""" update `tabBOM` set `tabBOM`.base_operating_cost = `tabBOM`.operating_cost, 
		`tabBOM`.base_raw_material_cost = `tabBOM`.raw_material_cost,
		`tabBOM`.currency = (select default_currency from `tabCompany` where name = `tabBOM`.company)""")
