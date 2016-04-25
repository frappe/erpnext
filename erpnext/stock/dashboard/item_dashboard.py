from __future__ import unicode_literals

import frappe

@frappe.whitelist()
def get_data(item_code=None, warehouse=None, start=0, sort_by='actual_qty', sort_order='desc'):
	filters = {}
	if item_code:
		filters['item_code'] = item_code
	if warehouse:
		filters['warehouse'] = warehouse
	return frappe.get_list("Bin", filters=filters, fields=['item_code', 'warehouse',
		'projected_qty', 'reserved_qty', 'reserved_qty_for_production', 'actual_qty', 'valuation_rate'],
		order_by='{0} {1}'.format(sort_by, sort_order), start=start, page_length = 21)