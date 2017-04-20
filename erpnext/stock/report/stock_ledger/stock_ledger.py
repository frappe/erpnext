# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	sl_entries = get_stock_ledger_entries(filters)
	item_details = get_item_details(filters)
	opening_row = get_opening_balance(filters, columns)

	data = []

	if opening_row:
		data.append(opening_row)

	for sle in sl_entries:
		item_detail = item_details[sle.item_code]

		data.append([sle.date, sle.item_code, item_detail.item_name, item_detail.item_group,
			item_detail.brand, item_detail.description, sle.warehouse,
			item_detail.stock_uom, sle.actual_qty, sle.qty_after_transaction,
			(sle.incoming_rate if sle.actual_qty > 0 else 0.0),
			sle.valuation_rate, sle.stock_value, sle.voucher_type, sle.voucher_no,
			sle.batch_no, sle.serial_no, sle.company])

	return columns, data

def get_columns():
	return [_("Date") + ":Datetime:95", _("Item") + ":Link/Item:130", _("Item Name") + "::100", _("Item Group") + ":Link/Item Group:100",
		_("Brand") + ":Link/Brand:100", _("Description") + "::200", _("Warehouse") + ":Link/Warehouse:100",
		_("Stock UOM") + ":Link/UOM:100", _("Qty") + ":Float:50", _("Balance Qty") + ":Float:100",
		_("Incoming Rate") + ":Currency:110", _("Valuation Rate") + ":Currency:110", _("Balance Value") + ":Currency:110",
		_("Voucher Type") + "::110", _("Voucher #") + ":Dynamic Link/"+_("Voucher Type")+":100", _("Batch") + ":Link/Batch:100",
		_("Serial #") + ":Link/Serial No:100", _("Company") + ":Link/Company:100"
	]

def get_stock_ledger_entries(filters):
	return frappe.db.sql("""select concat_ws(" ", posting_date, posting_time) as date,
			item_code, warehouse, actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
			stock_value, voucher_type, voucher_no, batch_no, serial_no, company
		from `tabStock Ledger Entry` sle
		where company = %(company)s and
			posting_date between %(from_date)s and %(to_date)s
			{sle_conditions}
			order by posting_date asc, posting_time asc, name asc"""\
		.format(sle_conditions=get_sle_conditions(filters)), filters, as_dict=1)

def get_item_details(filters):
	item_details = {}
	for item in frappe.db.sql("""select name, item_name, description, item_group,
			brand, stock_uom from `tabItem` {item_conditions}"""\
			.format(item_conditions=get_item_conditions(filters)), filters, as_dict=1):
		item_details.setdefault(item.name, item)

	return item_details

def get_item_conditions(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("name=%(item_code)s")
	if filters.get("brand"):
		conditions.append("brand=%(brand)s")

	return "where {}".format(" and ".join(conditions)) if conditions else ""

def get_sle_conditions(filters):
	conditions = []
	item_conditions=get_item_conditions(filters)
	if item_conditions:
		conditions.append("""item_code in (select name from tabItem
			{item_conditions})""".format(item_conditions=item_conditions))
	if filters.get("warehouse"):
		conditions.append(get_warehouse_condition(filters.get("warehouse")))
	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")
	if filters.get("batch_no"):
		conditions.append("batch_no=%(batch_no)s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""

def get_opening_balance(filters, columns):
	if not (filters.item_code and filters.warehouse and filters.from_date):
		return

	from erpnext.stock.stock_ledger import get_previous_sle
	last_entry = get_previous_sle({
		"item_code": filters.item_code,
		"warehouse": get_warehouse_condition(filters.warehouse),
		"posting_date": filters.from_date,
		"posting_time": "00:00:00"
	})

	row = [""]*len(columns)
	row[1] = _("'Opening'")
	for i, v in ((9, 'qty_after_transaction'), (11, 'valuation_rate'), (12, 'stock_value')):
			row[i] = last_entry.get(v, 0)

	return row

def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return " exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
			warehouse_details.rgt)

	return ''
