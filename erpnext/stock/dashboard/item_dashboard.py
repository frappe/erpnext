
import frappe
from frappe.model.db_query import DatabaseQuery
from frappe.utils import cint, flt


@frappe.whitelist()
def get_data(item_code=None, warehouse=None, item_group=None, brand=None,
	start=0, sort_by='actual_qty', sort_order='desc', limit_page_length=20):
	'''Self Modification of Return data to render the item dashboard'''
	item_code_filter = ""
	if item_code:
		item_code_filter = 'and bin.item_code = "{}"'.format(item_code)
	warehouse_filter = ""
	if warehouse:
		warehouse_filter = 'and bin.warehouse = "{}"'.format(warehouse)
	brand_filter = ""
	if brand:
		brand_filter = 'and item.brand = "{}"'.format(brand)

	item_group_filter = ""
	if item_group:
		lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])
		items = frappe.db.sql_list("""
			select i.name from `tabItem` i
			where exists(select name from `tabItem Group`
				where name=i.item_group and lft >=%s and rgt<=%s)
		""", (lft, rgt))
		item_group_filter = "and bin.item_code in ({})".format(",".join(items))
	try:
		# check if user has any restrictions based on user permissions on warehouse
		if DatabaseQuery('Warehouse', user=frappe.session.user).build_match_conditions():
			warehouse_string = ', '.join([ ('\'' + w.name + '\'') for w in frappe.get_list('Warehouse')])
			warehouse_filter += "and bin.warehouse in ({})".format(warehouse_string)
	except frappe.PermissionError:
		# user does not have access on warehouse
		return []

	## This is probably a good project to modify, since we just need to use SQL to rewrite
	SQL_query = """
		Select 	bin.item_code, 
				bin.warehouse, 
				bin.projected_qty, 
				bin.reserved_qty,
				bin.reserved_qty_for_production,
				bin.reserved_qty_for_sub_contract,
				bin.actual_qty,
				bin.valuation_rate,
				item.brand
		From `tabBin` bin
			Left Join `tabItem` item on bin.item_code = item.name
		Where 	(bin.projected_qty != 0.0 or
				bin.reserved_qty != 0.0 or
				bin.reserved_qty_for_production != 0.0 or
				bin.reserved_qty_for_sub_contract != 0.0 or
				bin.actual_qty != 0.0)
				{item_code_filter}
				{warehouse_filter}
				{item_group_filter}
				{brand_filter}
		Order By {sort_by} {sort_order}
		Limit {limit_page_length} offset {limit_start}
	""".format(
		item_code_filter	=	item_code_filter,
		warehouse_filter	=	warehouse_filter,
		item_group_filter	=	item_group_filter,
		brand_filter		=	brand_filter,
		sort_by				=	sort_by,
		sort_order			=	sort_order,
		limit_page_length	=	limit_page_length,
		limit_start			=	start,
	)

	"""
				%(item_code_filter)s
				%(warehouse_filter)s
				%(item_group_filter)s
				%(brand_filter)s


				{
		"item_code_filter": item_code_filter,
		"warehouse_filter": warehouse_filter,
		"item_group_filter": item_group_filter,
		"brand_filter": brand_filter,
	}, 
	"""
	items = frappe.db.sql(SQL_query, as_dict=1, debug=0)
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))

	for item in items:
		item.update({
			'item_name': frappe.get_cached_value(
				"Item", item.item_code, 'item_name'),
			'disable_quick_entry': frappe.get_cached_value(
				"Item", item.item_code, 'has_batch_no')
			or frappe.get_cached_value(
				"Item", item.item_code, 'has_serial_no'),
			'projected_qty': flt(item.projected_qty, precision),
			'reserved_qty': flt(item.reserved_qty, precision),
			'reserved_qty_for_production': flt(item.reserved_qty_for_production, precision),
			'reserved_qty_for_sub_contract': flt(item.reserved_qty_for_sub_contract, precision),
			'actual_qty': flt(item.actual_qty, precision),
		})
	return items
