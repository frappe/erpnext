# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff
from collections import OrderedDict
from erpnext.accounts.report.general_ledger.general_ledger import get_gl_entries


def execute(filters=None):
	print(filters)
	validate_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def validate_filters(filters):
	if not filters.get("from_date") and not filters.get("to_date"):
		frappe.throw(_("{0} and {1} are mandatory").format(frappe.bold(_("From Date")), frappe.bold(_("To Date"))))

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))


def get_columns():
	return [
		{
			'label': 'Item Group',
			'fieldname': 'item_group',
			'fieldtype': 'Data',
			'width': '200'
		},
		{
			'label': 'COGS Debit',
			'fieldname': 'cogs_debit',
			'fieldtype': 'Currency',
			'width': '200'
		}
	]


def get_data(filters):
	entries = get_filtered_entries(filters)
	item_groups_list = frappe.get_all("Item Group", fields=("name", "is_group", "lft", "rgt"))
	item_groups_dict = get_item_groups_dict(item_groups_list)
	levels_dict = get_levels_dict(item_groups_dict)

	update_levels_dict(levels_dict)
	assign_self_values(levels_dict, entries)
	assign_agg_values(levels_dict)
	
	data = []
	for _, i in levels_dict.items():
		if i['agg_value'] == 0:
			continue
		data.append(get_row(i['name'], i['agg_value'], i['is_group'], i['level']))
		if i['self_value'] < i['agg_value'] and i['self_value'] > 0:
			data.append(get_row(i['name'], i['self_value'], 0, i['level'] + 1))
	return data


def get_filtered_entries(filters):
	gl_entries = get_gl_entries(filters, [])
	entries = [frappe.get_doc(gle.voucher_type, gle.voucher_no)for gle in gl_entries]
	filtered_entries = []
	for entry in entries:
		posting_date = entry.get("posting_date")
		from_date = filters.get("from_date")
		if date_diff(from_date, posting_date) > 0:
			continue
		filtered_entries.append(entry)
	return filtered_entries


def append_blank(data):
	if len(data) == 0:
		data.append(get_row("", 0, 0, 0))


def get_item_groups_dict(item_groups_list):
	return { (i['lft'],i['rgt']):{'name':i['name'], 'is_group':i['is_group']}
		for i in item_groups_list }


def get_levels_dict(item_groups_dict):
	lr_list = sorted(item_groups_dict, key=lambda x : x[0])
	levels = OrderedDict()
	current_level = 0
	nesting_r = []
	for l,r in lr_list:
		while current_level > 0 and nesting_r[-1] < l:
			nesting_r.pop()
			current_level -= 1

		levels[(l,r)] = {
			'level' : current_level,
			'name' : item_groups_dict[(l,r)]['name'],
			'is_group' : item_groups_dict[(l,r)]['is_group']
		}

		if r - l > 1:
			current_level += 1
			nesting_r.append(r)
	return levels

			
def update_levels_dict(levels_dict):
	for k in levels_dict: levels_dict[k].update({'self_value':0, 'agg_value':0})


def assign_self_values(levels_dict, entries):
	names_dict = {v['name']:k for k, v in levels_dict.items()}
	for entry in entries:
		items = entry.get("items")
		items = [] if items is None else items
		for item in items:
			qty = item.get("qty")
			incoming_rate = item.get("incoming_rate")
			item_group = item.get("item_group")
			key = names_dict[item_group]
			levels_dict[key]['self_value'] += (incoming_rate * qty)


def assign_agg_values(levels_dict):
	keys = list(levels_dict.keys())[::-1]
	prev_level = levels_dict[keys[-1]]['level']
	accu = [0]
	for k in keys[:-1]:
		curr_level = levels_dict[k]['level']
		if curr_level == prev_level:
			accu[-1] += levels_dict[k]['self_value']
			levels_dict[k]['agg_value'] = levels_dict[k]['self_value']

		elif curr_level > prev_level:
			accu.append(levels_dict[k]['self_value'])
			levels_dict[k]['agg_value'] = accu[-1]

		elif curr_level < prev_level:
			accu[-1] += levels_dict[k]['self_value']
			levels_dict[k]['agg_value'] = accu[-1]

		prev_level = curr_level

	# root node
	rk = keys[-1]
	levels_dict[rk]['agg_value'] = sum(accu) + levels_dict[rk]['self_value']


def get_row(name:str, value:float, is_bold:int, indent:int):
	item_group = name
	if is_bold:
		item_group = frappe.bold(item_group)
	return frappe._dict(item_group=item_group, cogs_debit=value, indent=indent)
