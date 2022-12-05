# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr, rounded
from erpnext.accounts.report.financial_statements_emines \
	import filter_accounts, filter_out_zero_value_rows
from erpnext.accounts.accounts_custom_functions import get_child_cost_centers

activity_list = ("total_exp", 'mining_expenses', 'crushing_plant_expenses1', 'crushing_plant_expenses2', 'washed_expenses', 'transportation', 's_and_d')

def execute(filters=None):
	data = get_data(filters)
	columns = get_columns()
	return columns, data
def get_columns():
	return [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 250
		},
		{
			"fieldname": "total_exp",
			"label": _("Total Expense"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "mining_expenses",
			"label": _("Mining Expense"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "crushing_plant_expenses1",
			"label": _("Crushing Plant 1"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "crushing_plant_expenses2",
			"label": _("Crushing Plant 2"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "washed_expenses",
			"label": _("Washed"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "transportation",
			"label": _("Transportation"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "s_and_d",
			"label": _("Sales & Distribution"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total",
			"label": _("COP"),
			"fieldtype": "Currency",
			"width": 120
		}
	]

def get_data(filters):
	accounts = frappe.db.sql("""select name,  parent_account, account_name, root_type, report_type, lft, rgt
			from `tabAccount` where company= '{0}'  and root_type = 'Expense' and 
			(name in (select ci.account from `tabCOP Item` ci where ci.name = name) or is_group = 1) order by lft
		""".format(filters.company) ,  as_dict=True)
	if not accounts:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)
	gl_entries_by_account = {}
	for root in frappe.db.sql("""
			select lft, rgt 
			from tabAccount
			where root_type= 'Expense' 
			and ifnull(parent_account, '') = ''
			""", as_dict=1):
		set_gl_entries_by_account(filters, filters.cost_center, filters.company, filters.from_date, filters.to_date, root.lft, root.rgt,
		gl_entries_by_account, ignore_closing_entries=False)
		calculate_values(filters, accounts_by_name, gl_entries_by_account)
		accumulate_values_into_parents(accounts, accounts_by_name)
		out = prepare_data(filters, accounts)
		out = filter_out_zero_value_rows(out, parent_children_map)
	return out

def calculate_values(filters, accounts_by_name, gl_entries_by_account):	
	mining_qty = production_qty(filters, 'Mining Expense')[0].qty
	crush_qty1 = production_qty(filters, 'Crushing Plant 1')[0].qty
	crush_qty2 = production_qty(filters, 'Crushing Plant 2')[0].qty
	washed_qty = production_qty(filters, 'Washed')[0].qty
	trans_qty = stock_transfer(filters, 'Transportation')[0].qty
	sales_qty = qty_sold(filters, 'Sales & Distribution')[0].qty
	
	if filters.detail_cop:
		mining_qty = crush_qty1 = crush_qty2 = washed_qty = trans_qty = sales_qty = 1
	
	for entries in gl_entries_by_account.values():
		for entry in entries:
			d = accounts_by_name.get(entry.account)
			tot_exps = flt(entry.debit) - flt(entry.credit)
			d['total_exp'] = d.get('total_exp', 0.0) + flt(entry.debit) - flt(entry.credit)
			cop_per = cop_per_dic(filters, entry.account, entry.posting_date)[0]
			d['mining_expenses'] = d.get('mining_expenses', 0.0) + (cop_per.mining_expenses * 0.01 * tot_exps)/flt(mining_qty)
			d['crushing_plant_expenses1'] = d.get('crushing_plant_expenses1', 0.0) +  (cop_per.crushing_plant_expenses1 * 0.01 * tot_exps)/flt(crush_qty1)
			d['crushing_plant_expenses2'] = d.get('crushing_plant_expenses2', 0.0) +  (cop_per.crushing_plant_expenses2 * 0.01 * tot_exps)/flt(crush_qty2)
			d['washed_expenses'] = d.get('washed_expenses', 0.0) +  (cop_per.washed_expenses * 0.01 * tot_exps)/flt(washed_qty)
			d['transportation'] = d.get('transportation', 0.0) +  (cop_per.transportation * 0.01 * tot_exps)/flt(trans_qty)
			d['s_and_d'] = d.get('s_and_d', 0.0) +  (cop_per.s_and_d * 0.01 * tot_exps)/flt(sales_qty)

def cop_per_dic(filters, account, posting_date):
	query = """ select ifnull(c.mining_expenses, 0) as mining_expenses, ifnull(c.crushing_plant_expenses1, 0) as crushing_plant_expenses1, 
			ifnull(c.crushing_plant_expenses2, 0) as crushing_plant_expenses2, ifnull(c.washed_expenses, 0) as washed_expenses,
			ifnull(c.transportation,0) as transportation, ifnull(c.s_and_d, 0) as s_and_d from `tabCOP Item` c, `tabCOP` p 
			where c.parent = p.name and '{0}' between p.from_date and p.to_date and 
			p.cost_center = "{1}" and c.account = "{2}" 
		""".format(posting_date, filters.cost_center, account)	
	
	return frappe.db.sql(query, as_dict =1)


def production_qty(filters, activity_name):
	query = """ select ifnull(sum(c.qty), 1) as qty from `tabProduction Product Item` c, `tabProduction` p 
			where c.parent = p.name and p.posting_date between '{0}' and '{1}' and p.cost_center = "{2}" and 
			p.docstatus = 1 and c.item_code in (select ai.item from `tabActivity Item` ai 
			where ai.parent = "{3}") 
		""".format(filters.from_date, filters.to_date, filters.cost_center, activity_name)
	return frappe.db.sql(query, as_dict = 1)

def stock_transfer1(filters, activity_name):
	query = """select ifnull(sum(c.qty), 1) as qty from `tabStock Entry` p, `tabStock Entry Detail` c 
			where c.parent = p.name and p.purpose = 'Material Transfer' and  c.cost_center = "{0}"  
			and p.posting_date between '{1}' and '{2}' and p.docstatus = 1 
			and c.item_code in (select ai.item from  `tabActivity Item` ai
					where ai.parent  = "{3}") and exists ( select name from `tabWarehouse` w where w.name = p.to_warehouse and w.is_stockyard = 1)
		""".format(filters.cost_center, filters.from_date, filters.to_date, activity_name)
		
	return frappe.db.sql(query, as_dict =1)

def stock_transfer(filters, activity_name):
		query = """select ifnull(sum(c.qty), 1) as qty from `tabStock Entry` p, `tabStock Entry Detail` c 
						where c.parent = p.name and p.purpose = 'Material Transfer' and  c.t_warehouse in (select wb.parent from `tabWarehouse Branch` wb where wb.branch in (select b.name from `tabBranch` b where b.cost_center = '{0}'))
						and p.posting_date between '{1}' and '{2}' and p.docstatus = 1 
						and c.item_code in (select ai.item from  `tabActivity Item` ai
						where ai.parent  = "{3}")
				""".format(filters.cost_center, filters.from_date, filters.to_date, activity_name)

		return frappe.db.sql(query, as_dict =1, debug = 1)

def qty_sold(filters, activity_name):
	query = """select ifnull(sum(c.qty), 1) as qty from `tabDelivery Note` p, `tabDelivery Note Item` c where c.parent = p.name
			and p.docstatus = 1 and p.posting_date between '{0}' and '{1}' and c.cost_center = "{2}" and 
			c.item_code in (select ai.item from `tabActivity Item` ai where ai.parent = "{3}")
		""".format(filters.from_date, filters.to_date, filters.cost_center, activity_name)
	
	return frappe.db.sql(query, as_dict = 1)
		
def accumulate_values_into_parents(accounts, accounts_by_name):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			for activity in activity_list:
				accounts_by_name[d.parent_account][activity] = accounts_by_name[d.parent_account].get(activity, 0.0) + d.get(activity, 0.0)

def prepare_data(filters, accounts):
	data = []
	for d in accounts:
		has_value = False
		total = 0
		row = frappe._dict({
			"account_name": d.account_name,
			"account": d.name,
			"is_group": d.is_group,
			"parent_account": d.parent_account,
			"indent": flt(d.indent),
			"year_start_date": filters.from_date,
			"year_end_date": filters.to__date
		})
		for activity in activity_list:
			if d.get(activity):
				row[activity] = flt(d.get(activity, 0.0), 3)
				total += flt(d.get(activity, 0.0), 3)
				has_value = True
		row["has_value"] = has_value
		row["total"] = flt(total) - flt(d.get('total_exp', 0.0), 3)
		data.append(row)

	return data

def set_gl_entries_by_account(filters, cost_center, company, from_date, to_date, root_lft, root_rgt, gl_entries_by_account, ignore_closing_entries=True, open_date=None):
	"""Returns a dict like { "account": [gl entries], ... }"""
	additional_conditions = []

	if ignore_closing_entries:
		additional_conditions.append(" and ifnull(voucher_type, '')!='Period Closing Voucher' ")

	if from_date and to_date:
		if open_date:
			#Getting openning balance
			additional_conditions.append(" and posting_date < \'" + str(open_date) + "\' and docstatus = 1 ")
		else:
			additional_conditions.append(" and posting_date BETWEEN %(from_date)s AND %(to_date)s and docstatus = 1 ")
	
	gl_entries = frappe.db.sql("""select posting_date, 
					account, sum(debit) as debit, 
					sum(credit) as credit, 
					is_opening 
					from `tabGL Entry` 
					where company=%(company)s {additional_conditions}
					and account in (select name from `tabAccount` where lft >= %(lft)s and rgt <= %(rgt)s) 
					and cost_center = %(cost_center)s 
					and account in ( select c.account from `tabCOP Item` c, `tabCOP` p where c.parent = p.name and p.cost_center = %(cost_center)s and posting_date between p.from_date and p.to_date)
					group by account, posting_date order by account, posting_date
		""".format(additional_conditions="\n".join(additional_conditions)),
			{
				"cost_center": filters.cost_center,
				"company": company,
				"from_date": from_date,
				"to_date": to_date,
				"lft": root_lft,
				"rgt": root_rgt
			},
			as_dict=True)
	for entry in gl_entries:
		gl_entries_by_account.setdefault(entry.account, []).append(entry)
	return gl_entries_by_account

