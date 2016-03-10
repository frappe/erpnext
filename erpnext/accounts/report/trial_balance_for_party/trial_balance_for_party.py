# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.accounts.report.trial_balance.trial_balance import validate_filters


def execute(filters=None):
	validate_filters(filters)
	
	show_party_name = is_party_name_visible(filters)
	
	columns = get_columns(filters, show_party_name)
	data = get_data(filters, show_party_name)

	return columns, data
	
def get_data(filters, show_party_name):
	party_name_field = "customer_name" if filters.get("party_type")=="Customer" else "supplier_name"
	parties = frappe.get_all(filters.get("party_type"), fields = ["name", party_name_field], order_by="name")
	
	opening_balances = get_opening_balances(filters)
	balances_within_period = get_balances_within_period(filters)
	
	data = []
	total_debit, total_credit = 0, 0
	for party in parties:
		row = { "party": party.name }
		if show_party_name:
			row["party_name"] = party.get(party_name_field)
		
		# opening
		opening_debit, opening_credit = opening_balances.get(party.name, [0, 0])
		row.update({
			"opening_debit": opening_debit,
			"opening_credit": opening_credit
		})
		
		# within period
		debit, credit = balances_within_period.get(party.name, [0, 0])
		row.update({
			"debit": debit,
			"credit": credit
		})
		
		# totals
		total_debit += debit
		total_credit += credit
		
		# closing
		closing_debit, closing_credit = toggle_debit_credit(opening_debit + debit, opening_credit + credit)
		row.update({
			"closing_debit": closing_debit,
			"closing_credit": closing_credit
		})
		
		has_value = False
		if (opening_debit or opening_credit or debit or credit or closing_debit or closing_credit):
			has_value  =True
		
		if cint(filters.show_zero_values) or has_value:
			data.append(row)
		
	# Add total row
	if total_debit or total_credit:
		data.append({
			"party": "'" + _("Totals") + "'",
			"debit": total_debit,
			"credit": total_credit
		})
	
	return data
	
def get_opening_balances(filters):
	gle = frappe.db.sql("""
		select party, sum(debit) as opening_debit, sum(credit) as opening_credit 
		from `tabGL Entry`
		where company=%(company)s 
			and ifnull(party_type, '') = %(party_type)s and ifnull(party, '') != ''
			and (posting_date < %(from_date)s or ifnull(is_opening, 'No') = 'Yes')
		group by party""", {
			"company": filters.company,
			"from_date": filters.from_date,
			"party_type": filters.party_type
		}, as_dict=True)
		
	opening = frappe._dict()
	for d in gle:
		opening_debit, opening_credit = toggle_debit_credit(d.opening_debit, d.opening_credit)
		opening.setdefault(d.party, [opening_debit, opening_credit])
		
	return opening
	
def get_balances_within_period(filters):
	gle = frappe.db.sql("""
		select party, sum(debit) as debit, sum(credit) as credit 
		from `tabGL Entry`
		where company=%(company)s 
			and ifnull(party_type, '') = %(party_type)s and ifnull(party, '') != ''
			and posting_date >= %(from_date)s and posting_date <= %(to_date)s 
			and ifnull(is_opening, 'No') = 'No'
		group by party""", {
			"company": filters.company,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"party_type": filters.party_type
		}, as_dict=True)
		
	balances_within_period = frappe._dict()
	for d in gle:
		balances_within_period.setdefault(d.party, [d.debit, d.credit])
		
	return balances_within_period
	
def toggle_debit_credit(debit, credit):
	if flt(debit) > flt(credit):
		debit = flt(debit) - flt(credit)
		credit = 0.0
	else:
		credit = flt(credit) - flt(debit)
		debit = 0.0
		
	return debit, credit
	
def get_columns(filters, show_party_name):
	columns = [
		{
			"fieldname": "party",
			"label": _(filters.party_type),
			"fieldtype": "Link",
			"options": filters.party_type,
			"width": 200
		},
		{
			"fieldname": "opening_debit",
			"label": _("Opening (Dr)"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "opening_credit",
			"label": _("Opening (Cr)"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "closing_debit",
			"label": _("Closing (Dr)"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "closing_credit",
			"label": _("Closing (Cr)"),
			"fieldtype": "Currency",
			"width": 120
		}
	]
	
	if show_party_name:
		columns.insert(1, {
			"fieldname": "party_name",
			"label": _(filters.party_type) + " Name",
			"fieldtype": "Data",
			"width": 200
		})
		
	return columns
		
def is_party_name_visible(filters):
	show_party_name = False
	if filters.get("party_type") == "Customer":
		party_naming_by = frappe.db.get_single_value("Selling Settings", "cust_master_name")
	else:
		party_naming_by = frappe.db.get_single_value("Buying Settings", "supp_master_name")
		
	if party_naming_by == "Naming Series":
		show_party_name = True
		
	return show_party_name