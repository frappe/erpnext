# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_data(filters):
	data = []
	data1 = []
	query = """
		select 
			name as transporter_invoice, branch, cost_center, posting_date, equipment, total_trip, gross_amount, pol_amount,
			other_deductions, amount_payable, journal_entry, equipment_category, status, supplier
		from `tabTransporter Invoice` 
		where docstatus =1
	"""

	if filters.cost_center:
		query += " and cost_center = '{0}'".format(filters.get("cost_center"))
	if filters.get("from_date") and filters.get("to_date"):
		query += " and ((from_date between '{0}' and '{1}') or (to_date between '{0}' and '{1}'))".format(filters.get("from_date"), filters.get("to_date"))
	data = []
	for d in frappe.db.sql(query, as_dict =1):
		if d.journal_entry:
			je = frappe.get_doc("Journal Entry",d.journal_entry)
			d["mode_of_payment"] = je.mode_of_payment
			if je.mode_of_payment == "Cheque":
				d['cheque_no'] 		= je.cheque_no
				d['cheque_date'] 	= je.check_date
			elif je.mode_of_payment == "ePayment":
				d['cheque_no'] 		= je.bank_payment
		supplier = frappe.get_doc("Supplier",d.supplier)
		d["bank_name"] = supplier.bank
		d["account_number"] = supplier.account_number
		d["ifs_code"]		= supplier.ifs_code
		d["bank"]		= supplier.bank_name
		d["bank_branch"]		= supplier.bank_branch
		data.append(d)
	return data
def get_columns():
	return [
		{"fieldname":"transporter_invoice", "label": ("Transporter Invoice"), "fieldtype": "Link",	"options": "Transporter Invoice", "width": 130},
		{"fieldname":"branch", "label": ("Branch"), "fieldtype": "Link","options": "Branch", "width": 150},
		{"fieldname":"cost_center", "label": ("Cost Center"), "fieldtype": "Link",	"options": "Cost Center", "width": 150},
		{"fieldname":"posting_date", "label": ("Posting Date"), "fieldtype": "Date", "width": 100},
		{"fieldname":"equipment", "label": ("Equipment"), "fieldtype": "Link",	"options": "Equipment", "width": 100},
		{"fieldname":"equipment_category", "label": ("Equipment Category"), "fieldtype": "Link","options": "Equipment Category", "width": 130},
		{"fieldname":"total_trip", "label": ("Total Trip"), "fieldtype": "Float","width": 100},
		{"fieldname":"gross_amount", "label": ("Gross Amount"), "fieldtype": "Currency","width": 120},
		{"fieldname":"pol_amount", "label": ("POL Amount"), "fieldtype": "Currency","width": 120},
		{"fieldname":"other_deductions", "label": ("Other Deductions"), "fieldtype": "Currency","width": 100},
		{"fieldname":"amount_payable", "label": ("Amount Payable"), "fieldtype": "Currency","width": 100},
		{"fieldname":"mode_of_payment", "label": ("Mode Of Payment"), "fieldtype": "Link", "options":"Mode Of Payment","width": 120},
		{"fieldname":"cheque_no", "label": ("Cheque No/Ref/Jnrl"), "fieldtype": "Data","width": 100},
		{"fieldname":"cheque_date", "label": ("Cheque Date"), "fieldtype": "Date","width": 100},
		{"fieldname":"supplier", "label": ("Equipment Owner"), "fieldtype": "Link", "options":"Supplier","width": 150},
		{"fieldname":"bank", "label": ("Bank"), "fieldtype": "Link", "options":"Financial Institution","width": 80},
		{"fieldname":"bank_name", "label": ("Bank Name"), "fieldtype": "Data","width": 130},
		{"fieldname":"bank_branch", "label": ("Bank Branch"), "fieldtype": "Link", "options":"Financial Institution Branch","width": 150},
		{"fieldname":"account_number", "label": ("Account Number"), "fieldtype": "Data", "width": 120},
		{"fieldname":"ifs_code", "label": ("IFS Code"), "fieldtype": "Data","width": 100},
		{"fieldname":"status", "label": ("Status"), "fieldtype": "Data","width": 80},
]