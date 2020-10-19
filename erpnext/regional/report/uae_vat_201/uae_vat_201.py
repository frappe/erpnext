# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data, emirates, amounts_by_emirate = get_data(filters)
	chart = get_chart(emirates, amounts_by_emirate)

	return columns, data, None, chart

def get_columns():
	"""Creates a list of dictionaries that are used to generate column headers of the data table."""
	return [
		{
			"fieldname": "no",
			"label": _("No"),
			"fieldtype": "Data",
			"width": 50
		},
		{
			"fieldname": "legend",
			"label": _("Legend"),
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "amount",
			"label": _("Amount (AED)"),
			"fieldtype": "Currency",
			"width": 125,
			"options": "currency"
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount (AED)"),
			"fieldtype": "Currency",
			"width": 150,
			"options": "currency"
		}
	]

def get_data(filters = None):
	"""Returns the list of dictionaries. Each dictionary is a row in the datatable and chart data."""
	data = []
	data.append({
		"no": '',
		"legend": _('VAT on Sales and All Other Outputs'),
		"amount": '',
		"vat_amount": ''
		})

	total_emiratewise = get_total_emiratewise(filters)
	emirates = get_emirates()
	amounts_by_emirate = {}
	for d in total_emiratewise:
		emirate, amount, vat= d
		amounts_by_emirate[emirate] = {
				"legend": emirate,
				"raw_amount": amount,
				"raw_vat_amount": vat,
				"amount": frappe.format(amount, 'Currency'),
				"vat_amount": frappe.format(vat, 'Currency'),
			}

	for d, emirate in enumerate(emirates, 97):
		if emirate in amounts_by_emirate:
			amounts_by_emirate[emirate]["no"] = _('1{0}').format(chr(d))
			amounts_by_emirate[emirate]["legend"] = _('Standard rated supplies in {0}').format(emirate)
			data.append(amounts_by_emirate[emirate])
		else:
			data.append(
				{
					"no": _('1{0}').format(chr(d)),
					"legend": _('Standard rated supplies in {0}').format(emirate),
					"amount": frappe.format(0, 'Currency'),
					"vat_amount": frappe.format(0, 'Currency')
				}
			)

	data.append(
		{
			"no": '2',
			"legend": _('Tax Refunds provided to Tourists under the Tax Refunds for Tourists Scheme'),
			"amount": frappe.format((-1) * get_tourist_tax_return_total(filters), 'Currency'),
			"vat_amount": frappe.format((-1) * get_tourist_tax_return_tax(filters), 'Currency')
		}
	)

	data.append(
		{
			"no": '3',
			"legend": _('Supplies subject to the reverse charge provision'),
			"amount": frappe.format(get_reverse_charge_total(filters), 'Currency'),
			"vat_amount": frappe.format(get_reverse_charge_tax(filters), 'Currency')
		}
	)

	data.append(
		{
			"no": '4',
			"legend": _('Zero Rated'),
			"amount": frappe.format(get_zero_rated_total(filters), 'Currency'),
			"vat_amount": "-"
		}
	)

	data.append(
		{
			"no": '5',
			"legend": _('Exempt Supplies'),
			"amount": frappe.format(get_exempt_total(filters), 'Currency'),
			"vat_amount": "-"
		}
	)

	data.append({
		"no": '',
		"legend": '',
		"amount": '',
		"vat_amount": ''
		})

	data.append({
		"no": '',
		"legend": _('VAT on Expenses and All Other Inputs'),
		"amount": '',
		"vat_amount": ''
		})

	data.append(
		{
			"no": '9',
			"legend": _('Standard Rated Expenses'),
			"amount": frappe.format(get_standard_rated_expenses_total(filters), 'Currency'),
			"vat_amount": frappe.format(get_standard_rated_expenses_tax(filters), 'Currency')
		}
	)

	data.append(
		{
			"no": '10',
			"legend": _('Supplies subject to the reverse charge provision'),
			"amount": frappe.format(get_reverse_charge_recoverable_total(filters), 'Currency'),
			"vat_amount": frappe.format(get_reverse_charge_recoverable_tax(filters), 'Currency')
		}
	)

	return data, emirates, amounts_by_emirate


def get_chart(emirates, amounts_by_emirate):
	"""Returns chart data."""
	labels = []
	amount = []
	vat_amount = []
	for d in emirates:
		if d in amounts_by_emirate:
			amount.append(amounts_by_emirate[d]["raw_amount"])
			vat_amount.append(amounts_by_emirate[d]["raw_vat_amount"])
			labels.append(d)

	datasets = []
	datasets.append({'name': _('Amount (AED)'), 'values':  amount})
	datasets.append({'name': _('Vat Amount (AED)'), 'values': vat_amount})

	chart = {
			"data": {
				'labels': labels,
				'datasets': datasets
			}
		}

	chart["type"] = "bar"
	chart["fieldtype"] = "Currency"
	return chart

def get_total_emiratewise(filters):
	"""Returns Emiratewise Amount and Taxes."""
	return frappe.db.sql(f"""
		select emirate, sum(total), sum(total_taxes_and_charges) from `tabSales Invoice`
		where docstatus = 1 {get_conditions(filters)}
		group by `tabSales Invoice`.emirate;
		""", filters)

def get_emirates():
	"""Returns a List of emirates in the order that they are to be displayed."""
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
	"""The conditions to be used to filter data to calculate the total sale."""
	conditions = ""
	for opts in (("company", " and company=%(company)s"),
		("from_date", " and posting_date>=%(from_date)s"),
		("to_date", " and posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]
	return conditions

def get_reverse_charge_total(filters):
	"""Returns the sum of the total of each Purchase invoice made."""
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sum(total)  from
		`tabPurchase Invoice`
		where
		reverse_charge = "Y"
		and docstatus = 1 {where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_reverse_charge_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	conditions = get_conditions_join(filters)
	return frappe.db.sql("""
		select sum(debit)  from
		`tabPurchase Invoice`  inner join `tabGL Entry`
		on `tabGL Entry`.voucher_no = `tabPurchase Invoice`.name
		where
		`tabPurchase Invoice`.reverse_charge = "Y"
		and `tabPurchase Invoice`.docstatus = 1
		and `tabGL Entry`.docstatus = 1
		and account in (select account from `tabUAE VAT Account` where  parent=%(company)s)
		{where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_conditions_join(filters):
	"""The conditions to be used to filter data to calculate the total vat."""
	conditions = ""
	for opts in (("company", " and `tabPurchase Invoice`.company=%(company)s"),
		("from_date", " and `tabPurchase Invoice`.posting_date>=%(from_date)s"),
		("to_date", " and `tabPurchase Invoice`.posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]
	return conditions

def get_reverse_charge_recoverable_total(filters):
	"""Returns the sum of the total of each Purchase invoice made with recoverable reverse charge."""
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sum(total)  from
		`tabPurchase Invoice`
		where
		reverse_charge = "Y"
		and recoverable_reverse_charge > 0
		and docstatus = 1 {where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_reverse_charge_recoverable_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	conditions = get_conditions_join(filters)
	return frappe.db.sql("""
		select sum(debit * `tabPurchase Invoice`.recoverable_reverse_charge / 100)  from
		`tabPurchase Invoice`  inner join `tabGL Entry`
		on `tabGL Entry`.voucher_no = `tabPurchase Invoice`.name
		where
		`tabPurchase Invoice`.reverse_charge = "Y"
		and `tabPurchase Invoice`.docstatus = 1
		and `tabPurchase Invoice`.recoverable_reverse_charge > 0
		and `tabGL Entry`.docstatus = 1
		and account in (select account from `tabUAE VAT Account` where  parent=%(company)s)
		{where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_standard_rated_expenses_total(filters):
	"""Returns the sum of the total of each Purchase invoice made with recoverable reverse charge."""
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sum(total)  from
		`tabPurchase Invoice`
		where
		recoverable_standard_rated_expenses > 0
		and docstatus = 1 {where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_standard_rated_expenses_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sum(recoverable_standard_rated_expenses)  from
		`tabPurchase Invoice`
		where
		recoverable_standard_rated_expenses > 0
		and docstatus = 1 {where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_tourist_tax_return_total(filters):
	"""Returns the sum of the total of each Sales invoice with non zero tourist_tax_return."""
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sum(total)  from
		`tabSales Invoice`
		where
		tourist_tax_return > 0
		and docstatus = 1 {where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_tourist_tax_return_tax(filters):
	"""Returns the sum of the tax of each Sales invoice with non zero tourist_tax_return."""
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sum(tourist_tax_return)  from
		`tabSales Invoice`
		where
		tourist_tax_return > 0
		and docstatus = 1 {where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_zero_rated_total(filters):
	"""Returns the sum of each Sales Invoice Item Amount which is zero rated."""
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sum(i.base_amount) as total from
		`tabSales Invoice Item` i, `tabSales Invoice` s
		where s.docstatus = 1 and i.parent = s.name and i.is_zero_rated = 1
		{where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0

def get_exempt_total(filters):
	"""Returns the sum of each Sales Invoice Item Amount which is Vat Exempt."""
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sum(i.base_amount) as total from
		`tabSales Invoice Item` i, `tabSales Invoice` s
		where s.docstatus = 1 and i.parent = s.name and i.is_exempt = 1
		{where_conditions} ;
		""".format(where_conditions=conditions), filters)[0][0] or 0