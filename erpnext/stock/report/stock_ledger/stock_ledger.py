# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import cint
from erpnext.stock.utils import update_included_uom_in_dict_report
from erpnext.accounts.party import set_party_name_in_list
from frappe.desk.query_report import group_report_data, hide_columns_if_filtered
from six import iteritems

def execute(filters=None):
	show_amounts_role = frappe.db.get_single_value("Stock Settings", "restrict_amounts_in_report_to_role")
	show_amounts = not show_amounts_role or show_amounts_role in frappe.get_roles()

	show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

	include_uom = filters.get("include_uom")
	columns = get_columns(filters, show_amounts, show_item_name)
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sl_entries, include_uom)
	opening_row = get_opening_balance(filters.item_code, filters.warehouse, filters.from_date)

	data = []
	conversion_factors = []
	if opening_row:
		data.append(opening_row)

	actual_qty = stock_value = 0

	for sle in sl_entries:
		item_detail = item_details[sle.item_code]
		alt_uom_size = item_detail.alt_uom_size if filters.qty_field == "Contents Qty" and item_detail.alt_uom else 1.0

		row = frappe._dict({
			"date": sle.date,
			"item_code": sle.item_code,
			"item_name": item_detail.item_name,
			"disable_item_formatter": cint(show_item_name),
			"item_group": item_detail.item_group,
			"brand": item_detail.brand,
			"description": item_detail.description,
			"warehouse": sle.warehouse,
			"party_type": sle.party_type,
			"party": sle.party,
			"uom": item_detail.alt_uom or item_detail.stock_uom if filters.qty_field == "Contents Qty" else item_detail.stock_uom,
			"actual_qty": sle.actual_qty * alt_uom_size,
			"qty_after_transaction": sle.qty_after_transaction * alt_uom_size,
			"batch_qty_after_transaction": sle.batch_qty_after_transaction * alt_uom_size,
			"voucher_type": sle.voucher_type,
			"voucher_no": sle.voucher_no,
			"batch_no": sle.batch_no,
			"serial_no": sle.serial_no,
			"project": sle.project,
			"company": sle.company
		})

		if show_amounts:
			row.update({
				"valuation_rate": sle.valuation_rate / alt_uom_size,
				"batch_valuation_rate": sle.batch_valuation_rate / alt_uom_size,
				"stock_value": sle.stock_value,
				"batch_stock_value": sle.batch_stock_value,
				"stock_value_difference": sle.stock_value_difference,
			})

			if sle.actual_qty:
				if sle.actual_qty > 0:
					row['transaction_rate'] = sle.incoming_rate
				else:
					row['transaction_rate'] = sle.stock_value_difference / sle.actual_qty
				row['transaction_rate'] /= alt_uom_size

		data.append(row)

		if include_uom:
			conversion_factors.append(item_detail.conversion_factor)

	update_included_uom_in_dict_report(columns, data, include_uom, conversion_factors)

	set_party_name_in_list(data)

	data = get_grouped_data(filters, data)
	return columns, data

def get_columns(filters, show_amounts=True, show_item_name=True):
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 95},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 110},
		{"label": _("Voucher #"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 100},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100 if show_item_name else 150, "hide_if_filtered": 1},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150, "hide_if_filtered": 1},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100, "hide_if_filtered": 1, "filter_fieldname": "item_code"},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 100, "hide_if_filtered": 1},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 50},
		{"label": _("Qty"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 60, "convertible": "qty"},
		{"label": _("Balance Qty"), "fieldname": "qty_after_transaction", "fieldtype": "Float", "width": 90, "convertible": "qty"},
		{"label": _("Batch Qty"), "fieldname": "batch_qty_after_transaction", "fieldtype": "Float", "width": 90, "convertible": "qty"},
	]

	if show_amounts:
		columns += [
			{"label": _("In/Out Rate"), "fieldname": "transaction_rate", "fieldtype": "Currency", "width": 100,
				"options": "Company:company:default_currency", "convertible": "rate"},
			{"label": _("In/Out Amount"), "fieldname": "stock_value_difference", "fieldtype": "Currency", "width": 100,
				"options": "Company:company:default_currency"},
			{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 100,
				"options": "Company:company:default_currency", "convertible": "rate"},
			{"label": _("Batch Valuation Rate"), "fieldname": "batch_valuation_rate", "fieldtype": "Currency", "width": 100,
				"options": "Company:company:default_currency", "convertible": "rate"},
			{"label": _("Balance Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 110,
				"options": "Company:company:default_currency"},
			{"label": _("Batch Value"), "fieldname": "batch_stock_value", "fieldtype": "Currency", "width": 110,
				"options": "Company:company:default_currency"},
		]

	columns += [
		{"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Data", "width": 70, "hide_if_filtered": 1},
		{"label": _("Party"), "fieldname": "party", "fieldtype": "Dynamic Link", "options": "party_type", "width": 150, "hide_if_filtered": 1},
		{"label": _("Batch"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 100},
		{"label": _("Serial #"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 100},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 100, "hide_if_filtered": 1},
		{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 100, "hide_if_filtered": 1, "filter_fieldname": "item_code"},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 110}
	]

	if not show_item_name:
		columns = [c for c in columns if c.get('fieldname') != 'item_name']

	return columns

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = 'and sle.item_code in ({})'\
			.format(', '.join([frappe.db.escape(i) for i in items]))

	return frappe.db.sql("""select concat_ws(" ", posting_date, posting_time) as date,
			item_code, warehouse, actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
			stock_value, voucher_type, voucher_no, batch_no, serial_no, company, project, stock_value_difference,
			party_type, party,
			batch_qty_after_transaction, batch_stock_value, batch_valuation_rate
		from `tabStock Ledger Entry` sle
		where company = %(company)s and
			posting_date between %(from_date)s and %(to_date)s
			{sle_conditions}
			{item_conditions_sql}
			order by posting_date asc, posting_time asc, creation asc"""\
		.format(
			sle_conditions=get_sle_conditions(filters),
			item_conditions_sql = item_conditions_sql
		), filters, as_dict=1)

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

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	return items

def get_item_details(items, sl_entries, include_uom):
	item_details = {}
	if not items:
		items = list(set([d.item_code for d in sl_entries]))

	if not items:
		return item_details

	cf_field = cf_join = ""
	if include_uom:
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%s" \
			% frappe.db.escape(include_uom)

	res = frappe.db.sql("""
		select
			item.name, item.item_name, item.description, item.item_group, item.brand,
			item.stock_uom, item.alt_uom, item.alt_uom_size {cf_field}
		from
			`tabItem` item
			{cf_join}
		where
			item.name in ({item_codes})
	""".format(cf_field=cf_field, cf_join=cf_join, item_codes=','.join(['%s'] *len(items))), items, as_dict=1)

	for item in res:
		item_details.setdefault(item.name, item)

	return item_details

def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		warehouse_condition = get_warehouse_condition(filters.get("warehouse"))
		if warehouse_condition:
			conditions.append(warehouse_condition)
	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")
	if filters.get("batch_no"):
		conditions.append("batch_no=%(batch_no)s")
	if filters.get("project"):
		conditions.append("project=%(project)s")
	if filters.get("party_type"):
		conditions.append("party_type=%(party_type)s")
	if filters.get("party"):
		conditions.append("party=%(party)s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""

def get_opening_balance(item_code, warehouse, from_date, from_time="00:00:00"):
	if not (item_code and warehouse and from_date):
		return frappe._dict()

	from erpnext.stock.stock_ledger import get_previous_sle
	last_entry = get_previous_sle({
		"item_code": item_code,
		"warehouse_condition": get_warehouse_condition(warehouse),
		"posting_date": from_date,
		"posting_time": from_time
	})
	row = frappe._dict()
	row["voucher_type"] = _("Opening")
	for f in ('qty_after_transaction', 'valuation_rate', 'stock_value'):
		row[f] = last_entry.get(f, 0)

	return row

def get_grouped_data(filters, data):
	if not filters.get("group_by") or filters.get("group_by") == "Ungrouped":
		return data

	group_by = []
	group_by_label = filters.group_by.replace("Group by ", "")
	if group_by_label == "Item-Warehouse":
		group_by += ['item_code', 'warehouse']
	elif group_by_label == "Item":
		group_by.append('item_code')
	elif group_by_label == "Party":
		group_by += ['party', 'party_type']
	elif group_by_label == "Voucher":
		group_by.append(('voucher_no', 'voucher_type'))
	else:
		group_by.append(scrub(group_by_label))

	def postprocess_group(group_object, grouped_by):
		if group_by_label in ["Item-Warehouse", "Party"] and len(grouped_by) < 2:
			return

		group_header = frappe._dict({})
		if 'item_code' in grouped_by and 'warehouse' in grouped_by and filters.from_date:
			opening_dt = frappe.utils.get_datetime(group_object.rows[0].date)
			opening_dt -= opening_dt.resolution
			group_header = get_opening_balance(group_object.item_code, group_object.warehouse, opening_dt.date(), opening_dt.time())

		if 'item_code' in grouped_by:
			group_object.item_name = group_object.rows[0].get('item_name')

		if 'party' in grouped_by:
			group_object.party_name = group_object.rows[0].get('party_name')

		for f, g in iteritems(grouped_by):
			group_header[f] = g

		group_header._bold = True
		group_header._isGroupTotal = True
		group_object.rows.insert(0, group_header)

	return group_report_data(data, group_by, postprocess_group=postprocess_group)

def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return " exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and warehouse = wh.name)"%(warehouse_details.lft,
			warehouse_details.rgt)

	return ''

def get_item_group_condition(item_group):
	item_group_details = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=1)
	if item_group_details:
		return "item.item_group in (select ig.name from `tabItem Group` ig \
			where ig.lft >= %s and ig.rgt <= %s and item.item_group = ig.name)"%(item_group_details.lft,
			item_group_details.rgt)

	return ''
