# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, today
from erpnext.stock.utils import update_included_uom_in_dict_report, has_valuation_read_permission
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from frappe.desk.reportview import build_match_conditions

from erpnext.stock.report.stock_ageing.stock_ageing import get_fifo_queue, get_average_age


template = frappe._dict({
	"opening_qty": 0.0, "opening_val": 0.0,
	"in_qty": 0.0, "in_val": 0.0,
	"purchase_qty": 0.0, "purchase_val": 0.0,
	"purchase_return_qty": 0.0, "purchase_return_val": 0.0,
	"out_qty": 0.0, "out_val": 0.0,
	"sales_qty": 0.0, "sales_val": 0.0,
	"sales_return_qty": 0.0, "sales_return_val": 0.0,
	"reconcile_qty": 0.0, "reconcile_val": 0.0,
	"bal_qty": 0.0, "bal_val": 0.0,
	"ordered_qty": 0.0, "projected_qty": 0.0,
	"val_rate": 0.0
})


def execute(filters=None):
	return StockBalanceReport(filters).run()


class StockBalanceReport:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or today())
		self.filters.to_date = getdate(self.filters.to_date or today())

		self.show_amounts = has_valuation_read_permission()
		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("Date Range is incorrect"))

	def run(self):
		columns = self.get_columns()

		self.get_items()
		if not self.items and self.items is not None:
			return columns, []

		self.get_stock_ledger_entries()
		if not self.sles:
			return columns, []

		if self.filters.get('show_stock_ageing_data'):
			self.filters['show_warehouse_wise_stock'] = True
			self.item_wise_fifo_queue = get_fifo_queue(self.filters, self.sles)

		self.get_item_details_map()
		self.get_item_reorder_map()
		self.get_purchase_order_map()
		self.get_item_warehouse_map()

		rows = self.get_rows()

		update_included_uom_in_dict_report(columns, rows, self.filters.get("include_uom"), self.conversion_factors)

		return columns, self.rows

	def get_items(self):
		conditions = []
		if self.filters.get("item_code"):
			is_template = frappe.db.get_value("Item", self.filters.get('item_code'), 'has_variants')
			if is_template:
				conditions.append("item.variant_of = %(item_code)s")
			else:
				conditions.append("item.name = %(item_code)s")
		else:
			if self.filters.get("brand"):
				conditions.append("item.brand = %(brand)s")
			if self.filters.get("item_source"):
				conditions.append("item.item_source = %(item_source)s")
			if self.filters.get("item_group"):
				conditions.append(get_item_group_condition(self.filters.get("item_group")))

		self.items = None
		if conditions:
			self.items = frappe.db.sql_list("""
				select name
				from `tabItem` item
				where {0}
			""".format(" and ".join(conditions)), self.filters)

		return self.items

	def get_stock_ledger_entries(self):
		items_condition = ""
		if self.items:
			items_condition = " and item_code in ({})".format(
				', '.join([frappe.db.escape(i, percent=False) for i in self.items])
			)

		sle_conditions = self.get_sle_conditions()

		self.sles = frappe.db.sql("""
			select
				item_code, warehouse, item_code as name,
				posting_date, actual_qty, valuation_rate,
				company, voucher_type, qty_after_transaction, stock_value_difference,
				voucher_no
			from `tabStock Ledger Entry` force index (posting_sort_index)
			where docstatus < 2 {0} {1}
			order by posting_date, posting_time, creation, actual_qty
		""".format(items_condition, sle_conditions), as_dict=1)

	def get_sle_conditions(self):
		conditions = []

		if self.filters.get("to_date"):
			conditions.append("posting_date <= {0}".format(frappe.db.escape(self.filters.get("to_date"))))

		if self.filters.get("warehouse"):
			warehouse_details = frappe.db.get_value("Warehouse", self.filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
			if not warehouse_details:
				frappe.throw(_("Warehouse {0} does not exist").format(self.filters.get("warehouse")))

			conditions.append("""exists (select wh.name from `tabWarehouse` wh
				where wh.lft >= {0} and wh.rgt <= {1} and `tabStock Ledger Entry`.warehouse = wh.name)
			""".format(warehouse_details.lft, warehouse_details.rgt))

		elif self.filters.get("warehouse_type"):
			conditions.append(""" and exists (select name from `tabWarehouse` wh \
				where wh.warehouse_type = {0} and `tabStock Ledger Entry`.warehouse = wh.name)
			""".format(frappe.db.escape(self.filters.get("warehouse_type"))))

		match_conditions = build_match_conditions("Stock Ledger Entry")
		if match_conditions:
			conditions.append(match_conditions)

		return " and {0}".format(" and ".join(conditions)) if conditions else ""

	def get_purchase_order_map(self):
		self.purchase_order_map = {}

		if self.filters.get("show_projected_qty"):
			po_data = frappe.db.sql("""
				select po.company, po_item.item_code, po_item.warehouse,
					sum((po_item.qty - po_item.received_qty)*po_item.conversion_factor) as ordered_qty
				from `tabPurchase Order` po
				inner join `tabPurchase Order Item` po_item on po.name = po_item.parent
				where po.docstatus = 1 and po.status not in ('Closed', 'Delivered')
					and po_item.qty > po_item.received_qty and po_item.delivered_by_supplier = 0
					and po.transaction_date <= %s
				group by company, item_code, warehouse
			""", [self.filters.to_date], as_dict=1)

			for d in po_data:
				self.purchase_order_map[(d.company, d.item_code, d.warehouse)] = d.ordered_qty

		return self.purchase_order_map

	def get_item_details_map(self):
		self.item_map = {}

		if not self.items:
			self.items = list(set([d.item_code for d in self.sles]))
		if not self.items:
			return self.item_map

		cf_field = ""
		cf_join = ""
		if self.filters.get("include_uom"):
			cf_field = ", ucd.conversion_factor"
			cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent = item.name and ucd.uom = {0}".format(
				frappe.db.escape(self.filters.get("include_uom"))
			)

		item_data = frappe.db.sql("""
			select
				item.name, item.item_name, item.description, item.item_group, item.brand,
				item.stock_uom, item.alt_uom, item.alt_uom_size, item.disabled {cf_field}
			from `tabItem` item
			{cf_join}
			where item.name in %s
		""".format(cf_field=cf_field, cf_join=cf_join), [self.items], as_dict=1)

		for item in item_data:
			self.item_map.setdefault(item.name, item)

		return self.item_map

	def get_item_reorder_map(self):
		self.item_reorder_map = frappe._dict()

		if self.items:
			item_reorder_details = frappe.db.sql("""
				select parent as item_code, warehouse, warehouse_reorder_qty, warehouse_reorder_level
				from `tabItem Reorder`
				where parent in %s
			""", [self.items], as_dict=1)

			for d in item_reorder_details:
				self.item_reorder_map[(d.item_code, d.warehouse)] = d

		return self.item_reorder_map

	def get_item_warehouse_map(self):
		self.iwb_map = {}

		for sle in self.sles:
			key = (sle.company, sle.item_code, sle.warehouse)
			if key not in self.iwb_map:
				self.iwb_map[key] = frappe._dict(template.copy())

			stock_balance = self.iwb_map[(sle.company, sle.item_code, sle.warehouse)]

			if sle.voucher_type == "Stock Reconciliation":
				qty_diff = flt(sle.qty_after_transaction) - stock_balance.bal_qty
			else:
				qty_diff = flt(sle.actual_qty)

			value_diff = flt(sle.stock_value_difference)

			if sle.posting_date < self.filters.from_date:
				stock_balance.opening_qty += qty_diff
				stock_balance.opening_val += value_diff

			elif self.filters.from_date <= sle.posting_date <= self.filters.to_date:
				if qty_diff > 0:
					stock_balance.in_qty += qty_diff
					stock_balance.in_val += value_diff
				else:
					stock_balance.out_qty += abs(qty_diff)
					stock_balance.out_val += abs(value_diff)

				if sle.voucher_type in ["Purchase Receipt", "Purchase Invoice"]:
					if qty_diff < 0 and self.filters.get("separate_returns_qty"):
						stock_balance.purchase_return_qty -= qty_diff
						stock_balance.purchase_return_val -= value_diff
					else:
						stock_balance.purchase_qty += qty_diff
						stock_balance.purchase_val += value_diff

				elif sle.voucher_type in ["Delivery Note", "Sales Invoice"]:
					if qty_diff > 0 and self.filters.get("separate_returns_qty"):
						stock_balance.sales_return_qty += qty_diff
						stock_balance.sales_return_val += value_diff
					else:
						stock_balance.sales_qty -= qty_diff
						stock_balance.sales_val -= value_diff

				elif sle.voucher_type == "Stock Reconciliation":
					stock_balance.reconcile_qty += qty_diff
					stock_balance.reconcile_val += value_diff

			stock_balance.val_rate = sle.valuation_rate
			stock_balance.bal_qty += qty_diff
			stock_balance.bal_val += value_diff

		if self.purchase_order_map:
			for key, ordered_qty in self.purchase_order_map.items():
				if key not in self.iwb_map:
					self.iwb_map[key] = frappe._dict(template.copy())

				stock_balance = self.iwb_map[key]
				stock_balance.ordered_qty = ordered_qty

		self.iwb_map = self.filter_items_with_no_transactions()

		if cint(self.filters.get("consolidated")):
			self.iwb_map = self.consolidate_values()

		return self.iwb_map

	def filter_items_with_no_transactions(self):
		precision = self.get_precision()
		to_remove = []

		for (company, item, warehouse) in self.iwb_map:
			item_dict = self.item_map.get(item, {})

			if cint(self.filters.get("filter_item_without_transactions")) or item_dict.get('disabled'):
				stock_balance = self.iwb_map[(company, item, warehouse)]
				no_transactions = True

				for key, val in stock_balance.items():
					val = flt(val, precision)
					stock_balance[key] = val
					if key != "val_rate" and val:
						no_transactions = False

				if no_transactions:
					to_remove.append((company, item, warehouse))

		for d in to_remove:
			self.iwb_map.pop(d)

		return self.iwb_map

	def consolidate_values(self):
		item_map = frappe._dict()

		for (company, item, warehouse), stock_balance in self.iwb_map.items():
			key = ("", item, "")
			if key not in item_map:
				item_map[key] = frappe._dict(template.copy())

			for k, value in stock_balance.items():
				item_map[key][k] += value

		for k, stock_balance in item_map.items():
			stock_balance.val_rate = stock_balance.bal_val / stock_balance.bal_qty if stock_balance.bal_qty else 0.0

		return item_map

	def get_rows(self):
		self.rows = []
		self.conversion_factors = []

		for (company, item_code, warehouse) in sorted(self.iwb_map):
			if self.item_map.get(item_code):
				stock_balance = self.iwb_map[(company, item_code, warehouse)]
				item_details = self.item_map[item_code]

				use_alt_uom = self.filters.qty_field == "Contents Qty" and self.item_map[item_code]["alt_uom"]
				alt_uom_size = self.item_map[item_code]["alt_uom_size"] if use_alt_uom else 1.0

				reorder_details = self.item_reorder_map.get((item_code, warehouse)) or {}
				item_reorder_level = flt(reorder_details.get("warehouse_reorder_level"))
				item_reorder_qty = flt(reorder_details.get("warehouse_reorder_qty"))

				row = {
					"item_code": item_code,
					"item_name": item_details["item_name"],
					"disable_item_formatter": cint(self.show_item_name),
					"item_group": item_details["item_group"],
					"brand": item_details["brand"],
					"description": item_details["description"],

					"warehouse": warehouse,
					"company": company,
					"uom": item_details["alt_uom"] if use_alt_uom else item_details["stock_uom"],
					"alt_uom_size": item_details["alt_uom_size"] if item_details["alt_uom"] else None,

					"opening_qty": stock_balance.opening_qty * alt_uom_size,
					"in_qty": stock_balance.in_qty * alt_uom_size,
					"purchase_qty": stock_balance.purchase_qty * alt_uom_size,
					"purchase_return_qty": stock_balance.purchase_return_qty * alt_uom_size,
					"out_qty": stock_balance.out_qty * alt_uom_size,
					"sales_qty": stock_balance.sales_qty * alt_uom_size,
					"sales_return_qty": stock_balance.sales_return_qty * alt_uom_size,
					"bal_qty": stock_balance.bal_qty * alt_uom_size,
					"reconcile_qty": stock_balance.reconcile_qty * alt_uom_size,
					"reorder_level": item_reorder_level * alt_uom_size,
					"reorder_qty": item_reorder_qty * alt_uom_size,
					"ordered_qty": stock_balance.ordered_qty * alt_uom_size,
					"projected_qty": (stock_balance.ordered_qty + stock_balance.bal_qty) * alt_uom_size,
				}

				if self.show_amounts:
					row.update({
						"opening_val": stock_balance.opening_val,
						"in_val": stock_balance.in_val,
						"purchase_val": stock_balance.purchase_val,
						"purchase_return_val": stock_balance.purchase_return_val,
						"out_val": stock_balance.out_val,
						"sales_val": stock_balance.sales_val,
						"sales_return_val": stock_balance.sales_return_val,
						"bal_val": stock_balance.bal_val,
						"reconcile_val": stock_balance.reconcile_val,
						"val_rate": stock_balance.val_rate / alt_uom_size,
					})

				if self.filters.get("include_uom"):
					self.conversion_factors.append(flt(item_details.conversion_factor) * alt_uom_size)

				if self.filters.get('show_stock_ageing_data'):
					fifo_queue = self.item_wise_fifo_queue[(item_code, warehouse)].get('fifo_queue')

				self.rows.append(row)

		return self.rows

	def get_precision(self):
		return 6 if cint(frappe.db.get_default("float_precision")) <= 6 else 9

	def get_columns(self):
		columns = [
			{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item",
				"width": 100 if self.show_item_name else 150},
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data",
				"width": 150},
			{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse",
				"width": 100},
			{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM",
				"width": 50},
			{"label": _("Per Unit"), "fieldname": "alt_uom_size", "fieldtype": "Float",
				"width": 60},
			{"label": _("Balance Qty"), "fieldname": "bal_qty", "fieldtype": "Float",
				"width": 80, "convertible": "qty"},
			{"label": _("Balance Value"), "fieldname": "bal_val", "fieldtype": "Currency",
				"width": 95, "is_value": True},
			{"label": _("Ordered Qty"), "fieldname": "ordered_qty", "fieldtype": "Float",
				"width": 80, "convertible": "qty", "projected_column": 1},
			{"label": _("Projected Qty"), "fieldname": "projected_qty", "fieldtype": "Float",
				"width": 80, "convertible": "qty", "projected_column": 1},
			{"label": _("Open Qty"), "fieldname": "opening_qty", "fieldtype": "Float",
				"width": 80, "convertible": "qty"},
			{"label": _("Open Value"), "fieldname": "opening_val", "fieldtype": "Currency",
				"width": 90, "is_value": True},
			{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float",
				"width": 80, "convertible": "qty"},
			{"label": _("In Value"), "fieldname": "in_val", "fieldtype": "Currency",
				"width": 90, "is_value": True},
			{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float",
				"width": 80, "convertible": "qty"},
			{"label": _("Out Value"), "fieldname": "out_val", "fieldtype": "Currency",
				"width": 90, "is_value": True},
			{"label": _("Average Rate"), "fieldname": "val_rate", "fieldtype": "Currency",
				"width": 100, "convertible": "rate", "is_value": True},
			{"label": _("Purchase Qty"), "fieldname": "purchase_qty", "fieldtype": "Float",
				"width": 105, "convertible": "qty"},
			{"label": _("Purchase Value"), "fieldname": "purchase_val", "fieldtype": "Currency",
				"width": 105, "is_value": True},
			{"label": _("Sales Qty"), "fieldname": "sales_qty", "fieldtype": "Float",
				"width": 80, "convertible": "qty"},
			{"label": _("Sales Value"), "fieldname": "sales_val", "fieldtype": "Currency",
				"width": 90, "is_value": True},
			{"label": _("Purchase Return Qty"), "fieldname": "purchase_return_qty", "fieldtype": "Float",
				"width": 140, "convertible": "qty", "is_return": True},
			{"label": _("Purchase Return Value"), "fieldname": "purchase_return_val", "fieldtype": "Currency",
				"width": 140, "is_value": True, "is_return": True},
			{"label": _("Sales Return Qty"), "fieldname": "sales_return_qty", "fieldtype": "Float",
				"width": 120, "convertible": "qty", "is_return": True},
			{"label": _("Sales Return Value"), "fieldname": "sales_return_val", "fieldtype": "Currency",
				"width": 130, "is_value": True, "is_return": True},
			{"label": _("Reconciled Qty"), "fieldname": "reconcile_qty", "fieldtype": "Float",
				"width": 100, "convertible": "qty"},
			{"label": _("Reconciled Value"), "fieldname": "reconcile_val", "fieldtype": "Currency",
				"width": 110, "is_value": True},
			{"label": _("Reorder Level"), "fieldname": "reorder_level", "fieldtype": "Float",
				"width": 90, "convertible": "qty"},
			{"label": _("Reorder Qty"), "fieldname": "reorder_qty", "fieldtype": "Float",
				"width": 85, "convertible": "qty"},
			{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group",
				"width": 100},
			{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand",
				"width": 90},
			{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company",
				"width": 100},
			{'label': _('Average Age'), 'fieldname': 'average_age', 'fieldtype': 'Int',
				'width': 100, "is_ageing": True},
			{'label': _('Earliest Age'), 'fieldname': 'earliest_age', 'fieldtype': 'Int',
				'width': 80, "is_ageing": True},
			{'label': _('Latest Age'), 'fieldname': 'latest_age', 'fieldtype': 'Int',
				'width': 80, "is_ageing": True},
		]

		if not self.show_item_name:
			columns = [c for c in columns if c.get("fieldname") != "item_name"]

		if not self.show_amounts:
			columns = [c for c in columns if not c.get("is_value")]

		if cint(self.filters.consolidated):
			columns = [c for c in columns if c.get("fieldname") not in ["warehouse", "company"]]

		if not cint(self.filters.show_projected_qty):
			columns = [c for c in columns if not c.get("projected_column")]

		if not self.filters.get("show_stock_ageing_data"):
			columns = [c for c in columns if not c.get("is_ageing")]

		if not self.filters.get("separate_returns_qty"):
			columns = [c for c in columns if not c.get("is_return")]

		return columns
