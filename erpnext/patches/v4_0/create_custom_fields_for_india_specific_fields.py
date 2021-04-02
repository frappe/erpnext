# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field_if_values_exist

def execute():
	frappe.reload_doc("stock", "doctype", "purchase_receipt")
	frappe.reload_doc("hr", "doctype", "employee")
	frappe.reload_doc("hr", "doctype", "salary_slip")

	india_specific_fields = {
		"Purchase Receipt": [{
			"label": "Supplier Shipment No",
			"fieldname": "challan_no",
			"fieldtype": "Data",
			"insert_after": "is_subcontracted"
		}, {
			"label": "Supplier Shipment Date",
			"fieldname": "challan_date",
			"fieldtype": "Date",
			"insert_after": "is_subcontracted"
		}],
		"Employee": [{
			"label": "PAN Number",
			"fieldname": "pan_number",
			"fieldtype": "Data",
			"insert_after": "company_email"
		}, {
			"label": "Gratuity LIC Id",
			"fieldname": "gratuity_lic_id",
			"fieldtype": "Data",
			"insert_after": "company_email"
		}, {
			"label": "Esic Card No",
			"fieldname": "esic_card_no",
			"fieldtype": "Data",
			"insert_after": "bank_ac_no"
		}, {
			"label": "PF Number",
			"fieldname": "pf_number",
			"fieldtype": "Data",
			"insert_after": "bank_ac_no"
		}],
		"Salary Slip": [{
			"label": "Esic No",
			"fieldname": "esic_no",
			"fieldtype": "Data",
			"insert_after": "letter_head",
			"permlevel": 1
		}, {
			"label": "PF Number",
			"fieldname": "pf_no",
			"fieldtype": "Data",
			"insert_after": "letter_head",
			"permlevel": 1
		}]
	}

	for dt, docfields in india_specific_fields.items():
		for df in docfields:
			create_custom_field_if_values_exist(dt, df)
