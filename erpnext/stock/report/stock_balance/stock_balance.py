# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, now
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition

from six import iteritems

def execute(filters=None):
	if not filters: filters = {}

	validate_filters(filters)

	include_uom = filters.get("include_uom")
	columns, qty_columns, rate_columns = get_columns(include_uom)
	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)

	# if no stock ledger entry found return
	if not sle:
		return columns, []

	iwb_map = get_item_warehouse_map(filters, sle)
	item_map = get_item_details(items, sle, filters)
	item_reorder_detail_map = get_item_reorder_details(item_map.keys())

	def update_converted_qty_rate(row, conversion_factor):
		if include_uom and conversion_factor:
			for c in qty_columns:
				row[c + "_alt"] = flt(row[c] / conversion_factor)
			for c in rate_columns:
				row[c + "_alt"] = flt(row[c] * conversion_factor)

	data = []
	for (company, item, warehouse) in sorted(iwb_map):
		if item_map.get(item):
			qty_dict = iwb_map[(company, item, warehouse)]
			item_reorder_level = 0
			item_reorder_qty = 0
			if item + warehouse in item_reorder_detail_map:
				item_reorder_level = item_reorder_detail_map[item + warehouse]["warehouse_reorder_level"]
				item_reorder_qty = item_reorder_detail_map[item + warehouse]["warehouse_reorder_qty"]

			report_data = frappe._dict(qty_dict)
			report_data.company = company
			report_data.reorder_level = item_reorder_level
			report_data.reorder_qty = item_reorder_qty
			report_data.warehouse = warehouse
			report_data.item_code = item
			for col in ['item_name', 'description', 'item_group', 'brand', 'stock_uom']:
				report_data[col] = item_map[item][col]

			update_converted_qty_rate(report_data, item_map[item].get("conversion_factor"))

			data.append(report_data)

	if filters.get('show_variant_attributes', 0) == 1:
		columns += [{"label": "{}".format(i), "fieldname": "attr_{}".format(i), "fieldtype": "Data", "width": 100}
			for i in get_variants_attributes()]

	return columns, data

def get_columns(include_uom=None):
	"""return columns"""

	columns = [
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
		{"label": _("Item Name"), "fieldname": "item_name", "width": 150},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100},
		{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 90},
		{"label": _("Description"), "fieldname": "description", "width": 140},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 100},
		{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
		{"label": _("Opening Qty"), "fieldname": "opening_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Opening Value"), "fieldname": "opening_val", "fieldtype": "Float", "width": 110},
		{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 80},
		{"label": _("In Value"), "fieldname": "in_val", "fieldtype": "Float", "width": 80},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 80},
		{"label": _("Out Value"), "fieldname": "out_val", "fieldtype": "Float", "width": 80},
		{"label": _("Balance Qty"), "fieldname": "bal_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Balance Value"), "fieldname": "bal_val", "fieldtype": "Currency", "width": 100,
			"options": "Company:company:default_currency"},
		{"label": _("Valuation Rate"), "fieldname": "val_rate", "fieldtype": "Currency", "width": 90,
			"options": "Company:company:default_currency"},
		{"label": _("Reorder Level"), "fieldname": "reorder_level", "fieldtype": "Float", "width": 80},
		{"label": _("Reorder Qty"), "fieldname": "reorder_qty", "fieldtype": "Float", "width": 80},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 100}
	]

	qty_columns = ["opening_qty", "in_qty", "out_qty", "bal_qty", "reorder_level", "reorder_qty"]
	rate_columns = ["val_rate"]

	# Insert alternate uom column for each qty column
	if include_uom:
		i = len(columns) - 1
		while i >= 0:
			if columns[i].get("fieldname") in qty_columns:
				columns.insert(i + 1, dict(columns[i]))
				columns[i + 1]['fieldname'] = columns[i + 1]['fieldname'] + "_alt"
				columns[i + 1]['label'] += " ({})".format(include_uom)
			elif columns[i].get("fieldname") in rate_columns:
				columns.insert(i + 1, dict(columns[i]))
				columns[i + 1]['fieldname'] = columns[i + 1]['fieldname'] + "_alt"
				columns[i + 1]['label'] += " (per {})".format(include_uom)
			i -= 1

	return columns, qty_columns, rate_columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and sle.posting_date <= '%s'" % frappe.db.escape(filters.get("to_date"))
	else:
		frappe.throw(_("'To Date' is required"))

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse",
			filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt)

	return conditions

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = ' and sle.item_code in ({})'\
			.format(', '.join(['"' + frappe.db.escape(i, percent=False) + '"' for i in items]))

	conditions = get_conditions(filters)

	return frappe.db.sql("""
		select
			sle.item_code, warehouse, sle.posting_date, sle.actual_qty, sle.valuation_rate,
			sle.company, sle.voucher_type, sle.qty_after_transaction, sle.stock_value_difference
		from
			`tabStock Ledger Entry` sle force index (posting_sort_index)
		where sle.docstatus < 2 %s %s
		order by sle.posting_date, sle.posting_time, sle.name""" %
		(item_conditions_sql, conditions), as_dict=1)

def get_item_warehouse_map(filters, sle):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	for d in sle:
		key = (d.company, d.item_code, d.warehouse)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"opening_qty": 0.0, "opening_val": 0.0,
				"in_qty": 0.0, "in_val": 0.0,
				"out_qty": 0.0, "out_val": 0.0,
				"bal_qty": 0.0, "bal_val": 0.0,
				"val_rate": 0.0
			})

		qty_dict = iwb_map[(d.company, d.item_code, d.warehouse)]

		if d.voucher_type == "Stock Reconciliation":
			qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
		else:
			qty_diff = flt(d.actual_qty)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date:
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if qty_diff > 0:
				qty_dict.in_qty += qty_diff
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff
		
	iwb_map = filter_items_with_no_transactions(iwb_map)

	return iwb_map
	
def filter_items_with_no_transactions(iwb_map):
	for (company, item, warehouse) in sorted(iwb_map):
		qty_dict = iwb_map[(company, item, warehouse)]
		
		no_transactions = True
		float_precision = cint(frappe.db.get_default("float_precision")) or 3
		for key, val in iteritems(qty_dict):
			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False
		
		if no_transactions:
			iwb_map.pop((company, item, warehouse))

	return iwb_map

def get_items(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand=%(brand)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	return items

def get_item_details(items, sle, filters):
	item_details = {}
	if not items:
		items = list(set([d.item_code for d in sle]))

	if items:
		for item in frappe.db.sql("""
			select name, item_name, description, item_group, brand, stock_uom
			from `tabItem`
			where name in ({0}) and ifnull(disabled, 0) = 0
			""".format(', '.join(['"' + frappe.db.escape(i, percent=False) + '"' for i in items])), as_dict=1):
				item_details.setdefault(item.name, item)

	if filters.get("include_uom"):
		for item in frappe.db.sql("""
			select item.name, ucd.conversion_factor from `tabItem` item
			inner join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%s
			where item.name in ({0})
			""".format(', '.join(['"' + frappe.db.escape(i, percent=False) + '"' for i in items])),
			filters.get("include_uom"), as_dict=1):
				item_details[item.name].conversion_factor = item.conversion_factor

	if filters.get('show_variant_attributes', 0) == 1:
		variant_values = get_variant_values_for(list(item_details))
		item_details = {item: v.update(variant_values.get(item, {})) for item, v in iteritems(item_details)}

	return item_details

def get_item_reorder_details(items):
	item_reorder_details = frappe._dict()

	if items:
		item_reorder_details = frappe.db.sql("""
			select parent, warehouse, warehouse_reorder_qty, warehouse_reorder_level
			from `tabItem Reorder`
			where parent in ({0})
		""".format(', '.join(['"' + frappe.db.escape(i, percent=False) + '"' for i in items])), as_dict=1)

	return dict((d.parent + d.warehouse, d) for d in item_reorder_details)

def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse"))

def get_variants_attributes():
	'''Return all item variant attributes.'''
	return [i.name for i in frappe.get_all('Item Attribute')]

def get_variant_values_for(items):
	'''Returns variant values for items.'''
	attribute_map = {}
	for attr in frappe.db.sql('''select parent, attribute, attribute_value
		from `tabItem Variant Attribute` where parent in (%s)
		''' % ", ".join(["%s"] * len(items)), tuple(items), as_dict=1):
			attribute_map.setdefault(attr['parent'], {})
			attribute_map[attr['parent']].update({"attr_"+attr['attribute']: attr['attribute_value']})

	return attribute_map