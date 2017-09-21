# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
import frappe

def execute(filters=None):
	data = []

#	columns = [
#		{
#			"fieldname": "payment_type",
#			"label": "Tipo de Movimiento",
#			"fieldtype": "Select",
#			"options": ["Receive", "Pay", "Internal Transfer"],
#			"width": 300
#		},
#		{
#			"fieldname": "paid_amount",
#			"label": "Monto",
#			"fieldtype": "Currency",
#			"options": "currency",
#			"width": 150
#		}
#
#	]
	columns = ["Fecha:Date:100",_("Concepto") + ":Select:300", "Ingresos:Currency/currency:150","Egresos:Currency/currency:150", "Saldo:Currency/currency:150",_("Mode of Payment") + "::150"]

	total_income = 0
	total_expenditure = 0
	current_payment_mode = ""
	result = frappe.db.sql("""select posting_date, title, party_type, payment_type, paid_amount, mode_of_payment as payment_mode from `tabPayment Entry` where payment_type <> 'Internal Transfer' and posting_date =%(target_date)s {conditions} order by mode_of_payment""".format(conditions=get_conditions(filters)), filters, as_dict=1)
	for row in result:
		if current_payment_mode != row.payment_mode:
			if current_payment_mode != "":
				data.append([filters.get("target_date"), "Total ", total_income, total_expenditure,
						 total_income - total_expenditure, current_payment_mode])
				data.append([])
			total_expenditure = 0
			total_income = 0
			current_payment_mode = row.payment_mode
		income = 0
		expenditure = 0
		concept = ""
		if row.payment_type == "Receive":
			concept = "Cobro "
			income = row.paid_amount
			total_income += income
		if row.payment_type == "Pay":
			concept = "Pago "
			expenditure = row.paid_amount
			total_expenditure+= expenditure
		if row.party_type == "Customer":
			concept+= _("Customer") + " " + row.title
		if row.party_type == "Supplier":
			concept+= _("Supplier") + " " + row.title
		d = [row.posting_date,concept,income, expenditure,total_income - total_expenditure,row.payment_mode]
		data.append(d)
	if result:
		data.append([filters.get("target_date"), "Total ", total_income, total_expenditure,
					 total_income - total_expenditure, current_payment_mode])
	return columns, data

def get_conditions(filters):
	conditions = []
	if filters.get("mode_of_payment"):
		conditions.append("mode_of_payment=%(mode_of_payment)s")
	return "and {}".format(" and ".join(conditions)) if conditions else ""