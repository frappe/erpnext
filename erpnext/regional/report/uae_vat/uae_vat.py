# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.regional.united_arab_emirates.utils import get_tax_accounts

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def get_columns():
	"""Creates a list of dictionaries that are used to generate column headers of the data table

	Returns:
		List(Dict): list of dictionaries that are used to generate column headers of the data table
	"""
	return [
		{
			"fieldname": "no",
			"label": "No",
			"fieldtype": "Data",
			"width": 50
		},
		{
			"fieldname": "legend",
			"label": "Legend",
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "amount",
			"label": "Amount (AED)",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "vat_amount",
			"label": "VAT Amount (AED)",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "adjustment",
			"label": "Adjustment (AED)",
			"fieldtype": "Currency",
			"width": 100
		}
	]

def get_data(filters = None):
	"""Returns the list of dictionaries. Each dictionary is a row in the datatable

	Args:
		filters (Dict, optional): Dictionary consisting of the filters selected by the user. Defaults to None.

	Returns:
		List(Dict): Each dictionary is a row in the datatable
	"""
	data = []
	total_emiratewise = get_total_emiratewise(filters)
	emirates = get_emirates()
	amounts_by_emirate = {}
	for d in total_emiratewise:
		emirate, amount, vat= d
		amounts_by_emirate[emirate] = {
				"legend": emirate,
				"amount": amount,
				"vat_amount": vat
			}
	for d, emirate in enumerate(emirates, 97):
		if emirate in amounts_by_emirate:
			amounts_by_emirate[emirate]["no"] = f'1{chr(d)}'
			amounts_by_emirate[emirate]["legend"] = f'Standard rated supplies in {emirate}'
			data.append(amounts_by_emirate[emirate])
		else:
			data.append(
				{
					"no": f'1{chr(d)}',
					"legend": f'Standard rated supplies in {emirate}',
					"amount": 0,
					"vat_amount": 0
				}
			)
	data.append(
		{
			"no": '3',
			"legend": f'Supplies subject to the reverse charge provision',
			"amount": get_reverse_charge_total(filters),
			"vat_amount": get_reverse_charge_tax(filters)
		}
	)
	return data


def get_total_emiratewise(filters):
	return frappe.db.sql(f"""
		select emirate, sum(total), sum(total_taxes_and_charges) from `tabSales Invoice`
		where docstatus = 1 {get_conditions(filters)}
		group by `tabSales Invoice`.emirate;
		""", filters)

def get_emirates():
	"""Returns a List of emirates in the order that they are to be displayed

	Returns:
		List(String): List of emirates in the order that they are to be displayed
	"""
	return [
		'Abu Dhabi',
		'Dubai',
		'Sharjah',
		'Ajman',
		'Umm Al Quwain',
		'Ras Al Khaimah',
		'Fujairah'
	]

def get_conditions(filters):
	"""The conditions to be used to filter data to calculate the total sale

	Args:
		filters (Dict, optional): Dictionary consisting of the filters selected by the user. Defaults to None.

	Returns:
		String: Concatenated list of conditions to be applied to calculate the total sale
	"""
	conditions = ""
	for opts in (("company", f' and company="{filters.get("company")}"'),
		("from_date",  f' and posting_date>="{filters.get("from_date")}"'),
		("to_date", f' and posting_date<="{filters.get("to_date")}"')):
			if filters.get(opts[0]):
				conditions += opts[1]
	return conditions

def get_reverse_charge_total(filters):
	"""Returns the sum of the total of each Purchase invoice made

	Args:
		filters (Dict, optional): Dictionary consisting of the filters selected by the user. Defaults to None.

	Returns:
		Float: sum of the total of each Purchase invoice made
	"""
	conditions = """
	for opts in (("company", f' and company="{filters.get("company")}"'),
		("from_date",  f' and posting_date>="{filters.get("from_date")}"'),
		("to_date", f' and posting_date<="{filters.get("to_date")}"')):
			if filters.get(opts[0]):
				conditions += opts[1]
	return conditions
	"""
	return frappe.db.sql(f"""
		select sum(total)  from
		`tabPurchase Invoice`
		where
		reverse_charge = "Y"
		and docstatus = 1 {get_conditions(filters)} ;
		""")[0][0]

def get_reverse_charge_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made

	Args:
		filters (Dict, optional): Dictionary consisting of the filters selected by the user. Defaults to None.

	Returns:
		Float: sum of the tax of each Purchase invoice made
	"""
	return frappe.db.sql(f"""
		select sum(debit)  from
		`tabPurchase Invoice`  inner join `tabGL Entry`
		on `tabGL Entry`.voucher_no = `tabPurchase Invoice`.name
		where
		`tabPurchase Invoice`.reverse_charge = "Y"
		and `tabPurchase Invoice`.docstatus = 1
		and `tabGL Entry`.docstatus = 1  {get_conditions_join(filters)}
		and account in ("{'", "'.join(get_tax_accounts(filters['company']))}");
		""")[0][0]



def get_conditions_join(filters):
	"""The conditions to be used to filter data to calculate the total vat

	Args:
		filters (Dict, optional): Dictionary consisting of the filters selected by the user. Defaults to None.

	Returns:
		String: Concatenated list of conditions to be applied to calculate the total vat
	"""
	conditions = ""
	for opts in (("company", f' and `tabPurchase Invoice`.company="{filters.get("company")}"'),
		("from_date", f' and `tabPurchase Invoice`.posting_date>="{filters.get("from_date")}"'),
		("to_date", f' and `tabPurchase Invoice`.posting_date<="{filters.get("to_date")}"')):
			if filters.get(opts[0]):
				conditions += opts[1]
	return conditions