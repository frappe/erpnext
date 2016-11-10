from __future__ import unicode_literals

import frappe

@frappe.whitelist()
def get_data(item_code=None, warehouse=None, item_group=None,
	start=0, sort_by='actual_qty', sort_order='desc'):
	'''Return data to render the item dashboard'''
	conditions = []
	values = []
	if item_code:
		conditions.append('b.item_code=%s')
		values.append(item_code)
	if warehouse:
		conditions.append('b.warehouse=%s')
		values.append(warehouse)
	if item_group:
		conditions.append('i.item_group=%s')
		values.append(item_group)

	if conditions:
		conditions = ' and ' + ' and '.join(conditions)
	else:
		conditions = ''

	return frappe.db.sql('''
	select
		b.item_code, b.warehouse, b.projected_qty, b.reserved_qty,
		b.reserved_qty_for_production, b.actual_qty, b.valuation_rate, i.item_name
	from
		tabBin b, tabItem i
	where
		b.item_code = i.name
		{conditions}
	order by
		{sort_by} {sort_order}
	limit
		{start}, 21
	'''.format(conditions=conditions, sort_by=sort_by, sort_order=sort_order,
		start=start), values, as_dict=True)
