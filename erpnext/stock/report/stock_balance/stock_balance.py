# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, now, date_diff
from erpnext.stock.utils import update_included_uom_in_dict_report
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition

from erpnext.stock.report.stock_ageing.stock_ageing import get_fifo_queue, get_average_age

from six import iteritems

template = frappe._dict({
	"opening_qty": 0.0, "opening_val": 0.0,
	"in_qty": 0.0, "in_val": 0.0,
	"purchase_qty": 0.0, "purchase_val": 0.0,
	"out_qty": 0.0, "out_val": 0.0,
	"sales_qty": 0.0, "sales_val": 0.0,
	"bal_qty": 0.0, "bal_val": 0.0,
	"val_rate": 0.0
})

def execute(filters=None):
	if not filters: filters = {}

	validate_filters(filters)

	show_amounts_role = frappe.db.get_single_value("Stock Settings", "restrict_amounts_in_report_to_role")
	show_amounts = not show_amounts_role or show_amounts_role in frappe.get_roles()

	show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

	include_uom = filters.get("include_uom")
	columns = get_columns(filters, show_amounts, show_item_name)
	items = get_items(filters)

	# if no items in filter found return
	if isinstance(items, list) and not items:
		return columns, []

	sle = get_stock_ledger_entries(filters, items)

	if filters.get('show_stock_ageing_data'):
		filters['show_warehouse_wise_stock'] = True
		item_wise_fifo_queue = get_fifo_queue(filters, sle)

	# if no stock ledger entry found return
	if not sle:
		return columns, []

	iwb_map = get_item_warehouse_map(filters, sle)
	item_map = get_item_details(items, sle, filters)
	item_reorder_detail_map = get_item_reorder_details(item_map.keys())

	data = []
	conversion_factors = {}

	_func = lambda x: x[1]

	for (company, item, warehouse) in sorted(iwb_map):
		if item_map.get(item):
			qty_dict = iwb_map[(company, item, warehouse)]
			alt_uom_size = item_map[item]["alt_uom_size"] if filters.qty_field == "Contents Qty" and item_map[item]["alt_uom"] else 1.0
			item_reorder_level = 0
			item_reorder_qty = 0
			if item + warehouse in item_reorder_detail_map:
				item_reorder_level = item_reorder_detail_map[item + warehouse]["warehouse_reorder_level"]
				item_reorder_qty = item_reorder_detail_map[item + warehouse]["warehouse_reorder_qty"]

			report_data = {
				"item_code": item,
				"item_name": item_map[item]["item_name"],
				"disable_item_formatter": cint(show_item_name),
				"item_group": item_map[item]["item_group"],
				"brand": item_map[item]["brand"],
				"description": item_map[item]["description"],
				"warehouse": warehouse,
				"uom": item_map[item]["alt_uom"] or item_map[item]["stock_uom"] if filters.qty_field == "Contents Qty" else item_map[item]["stock_uom"],
				"opening_qty": qty_dict.opening_qty * alt_uom_size,
				"in_qty": qty_dict.in_qty * alt_uom_size,
				"purchase_qty": qty_dict.purchase_qty * alt_uom_size,
				"out_qty": qty_dict.out_qty * alt_uom_size,
				"sales_qty": qty_dict.sales_qty * alt_uom_size,
				"bal_qty": qty_dict.bal_qty * alt_uom_size,
				"reorder_level": item_reorder_level * alt_uom_size,
				"reorder_qty": item_reorder_qty * alt_uom_size,
				"company": company
			}

			if item_map[item]["alt_uom"]:
				report_data["alt_uom_size"] = item_map[item]["alt_uom_size"]

			if show_amounts:
				report_data.update({
					"opening_val": qty_dict.opening_val,
					"in_val": qty_dict.in_val,
					"purchase_val": qty_dict.purchase_val,
					"out_val": qty_dict.out_val,
					"sales_val": qty_dict.sales_val,
					"bal_val": qty_dict.bal_val,
					"val_rate": qty_dict.val_rate / alt_uom_size,
				})

			if filters.get('show_variant_attributes', 0) == 1:
				for i, v in enumerate(get_variants_attributes()):
					report_data["variant_{}".format(i)] = item_map[item].get(v)

			if include_uom:
				conversion_factors.setdefault(item, item_map[item].conversion_factor)

			if filters.get('show_stock_ageing_data'):
				fifo_queue = item_wise_fifo_queue[(item, warehouse)].get('fifo_queue')

			data.append(report_data)

	if filters.get('show_variant_attributes', 0) == 1:
		for i, v in enumerate(get_variants_attributes()):
			columns.append({"label": v, "fieldname": "variant_{}".format(i), "fieldtype": "Data", "width": 100, "is_variant_attribute": True}),

	update_included_uom_in_dict_report(columns, data, include_uom, conversion_factors)
	return columns, data

def get_columns(filters, show_amounts=True, show_item_name=True):
	"""return columns"""

	columns = [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100 if show_item_name else 200},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100},
		{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 90},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 100},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 50},
		{"label": _("Size"), "fieldname": "alt_uom_size", "fieldtype": "Float", "width": 50},
		{"label": _("Open Qty"), "fieldname": "opening_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Open Value"), "fieldname": "opening_val", "fieldtype": "Currency", "width": 90, "is_value": True},
		{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("In Value"), "fieldname": "in_val", "fieldtype": "Currency", "width": 90, "is_value": True},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Out Value"), "fieldname": "out_val", "fieldtype": "Currency", "width": 90, "is_value": True},
		{"label": _("Bal Qty"), "fieldname": "bal_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Bal Value"), "fieldname": "bal_val", "fieldtype": "Currency", "width": 90, "is_value": True},
		{"label": _("Avg Rate"), "fieldname": "val_rate", "fieldtype": "Currency", "width": 100, "convertible": "rate", "is_value": True},
		{"label": _("Purchase Qty"), "fieldname": "purchase_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Purchase Value"), "fieldname": "purchase_val", "fieldtype": "Currency", "width": 90, "is_value": True},
		{"label": _("Sales Qty"), "fieldname": "sales_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Sales Value"), "fieldname": "sales_val", "fieldtype": "Currency", "width": 90, "is_value": True},
		{"label": _("Reorder Level"), "fieldname": "reorder_level", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Reorder Qty"), "fieldname": "reorder_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 100}
	]

	if filters.get('show_stock_ageing_data'):
		columns += [{'label': _('Average Age'), 'fieldname': 'average_age', 'width': 100},
		{'label': _('Earliest Age'), 'fieldname': 'earliest_age', 'width': 100},
		{'label': _('Latest Age'), 'fieldname': 'latest_age', 'width': 100}]

	if filters.get('show_variant_attributes'):
		columns += [{'label': att_name, 'fieldname': att_name, 'width': 100} for att_name in get_variants_attributes()]

	if not show_item_name:
		columns = [c for c in columns if c.get('fieldname') != 'item_name']

	if not show_amounts:
		columns = list(filter(lambda d: not d.get("is_value"), columns))

	if cint(filters.consolidated):
		columns = list(filter(lambda d: d.get('fieldname') not in ['warehouse', 'company'], columns))

	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and sle.posting_date <= %s" % frappe.db.escape(filters.get("to_date"))
	else:
		frappe.throw(_("'To Date' is required"))

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse",
			filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt)

	if filters.get("warehouse_type") and not filters.get("warehouse"):
		conditions += " and exists (select name from `tabWarehouse` wh \
			where wh.warehouse_type = '%s' and sle.warehouse = wh.name)"%(filters.get("warehouse_type"))

	return conditions

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = ' and sle.item_code in ({})'\
			.format(', '.join([frappe.db.escape(i, percent=False) for i in items]))

	conditions = get_conditions(filters)

	return frappe.db.sql("""
		select
			sle.item_code, warehouse, sle.posting_date, sle.actual_qty, sle.valuation_rate,
			sle.company, sle.voucher_type, sle.qty_after_transaction, sle.stock_value_difference,
			sle.item_code as name, sle.voucher_no
		from
			`tabStock Ledger Entry` sle force index (posting_sort_index)
		where sle.docstatus < 2 %s %s
		order by sle.posting_date, sle.posting_time, sle.creation, sle.actual_qty""" % #nosec
		(item_conditions_sql, conditions), as_dict=1)

def get_item_warehouse_map(filters, sle):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	for d in sle:
		key = (d.company, d.item_code, d.warehouse)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict(template.copy())

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

			if d.voucher_type in ["Purchase Receipt", "Purchase Invoice"]:
				qty_dict.purchase_qty += qty_diff
				qty_dict.purchase_val += value_diff
			elif d.voucher_type in ["Delivery Note", "Sales Invoice"]:
				qty_dict.sales_qty -= qty_diff
				qty_dict.sales_val -= value_diff

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	if cint(filters.filter_item_without_transactions):
		iwb_map = filter_items_with_no_transactions(iwb_map)

	if cint(filters.consolidated):
		iwb_map = consolidate_values(iwb_map)

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

def consolidate_values(iwb_map):
	item_map = frappe._dict()

	for (company, item, warehouse), qty_dict in iteritems(iwb_map):
		key = ("", item, "")
		if key not in item_map:
			item_map[key] = frappe._dict(template.copy())

		for k, value in iteritems(qty_dict):
			item_map[key][k] += value

	for k, qty_dict in iteritems(item_map):
		qty_dict.val_rate = qty_dict.bal_val / qty_dict.bal_qty if qty_dict.bal_qty else 0.0

	return item_map

def get_items(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand=%(brand)s")
		if filters.get("item_source"):
			conditions.append("item.item_source=%(item_source)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = None
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	return items

def get_item_details(items, sle, filters):
	item_details = {}
	if not items:
		items = list(set([d.item_code for d in sle]))

	if not items:
		return item_details

	cf_field = cf_join = ""
	if filters.get("include_uom"):
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%s" \
			% frappe.db.escape(filters.get("include_uom"))

	res = frappe.db.sql("""
		select
			item.name, item.item_name, item.description, item.item_group, item.brand,
			item.stock_uom, item.alt_uom, item.alt_uom_size {cf_field}
		from
			`tabItem` item
			{cf_join}
		where
			item.name in %s and ifnull(item.disabled, 0) = 0
	""".format(cf_field=cf_field, cf_join=cf_join), [items], as_dict=1)

	for item in res:
		item_details.setdefault(item.name, item)

	if filters.get('show_variant_attributes', 0) == 1:
		variant_values = get_variant_values_for(list(item_details))
		item_details = {k: v.update(variant_values.get(k, {})) for k, v in iteritems(item_details)}

	return item_details

def get_item_reorder_details(items):
	item_reorder_details = frappe._dict()

	if items:
		item_reorder_details = frappe.db.sql("""
			select parent, warehouse, warehouse_reorder_qty, warehouse_reorder_level
			from `tabItem Reorder`
			where parent in ({0})
		""".format(', '.join([frappe.db.escape(i, percent=False) for i in items])), as_dict=1)

	return dict((d.parent + d.warehouse, d) for d in item_reorder_details)

def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse due to a large amount of entries."))

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
			attribute_map[attr['parent']].update({attr['attribute']: attr['attribute_value']})

	return attribute_map
