# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, today, cstr, combine_datetime
from erpnext.stock.utils import update_included_uom_in_dict_report, has_valuation_read_permission
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from frappe.desk.reportview import build_match_conditions
from collections import OrderedDict


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
			frappe.throw(_("From Date cannot be after To Date"))

	def run(self):
		self.validate_filters()
		self.get_columns()

		self.get_items()
		if not self.items and self.items is not None:
			return self.columns, []

		self.get_stock_ledger_entries()
		if not self.sles:
			return self.columns, []

		self.get_item_details_map()
		self.get_item_reorder_map()
		self.get_purchase_order_map()
		self.get_ageing_fifo_queue()
		self.get_stock_balance_map()
		self.clean_stock_balance_map()
		self.get_packing_slip_map()

		self.get_rows()
		self.get_columns()

		update_included_uom_in_dict_report(self.columns, self.rows, self.filters.get("include_uom"), self.conversion_factors)

		return self.columns, self.rows

	def validate_filters(self):
		if self.filters.get("show_projected_qty"):
			if self.is_batch_included():
				frappe.throw(_("Cannot get Projected Qty for Batch Wise Stock"))
			if self.is_package_included():
				frappe.throw(_("Cannot get Projected Qty for Package Wise Stock"))

	def get_items(self):
		self.items = get_items_for_stock_report(self.filters)
		return self.items

	def get_stock_ledger_entries(self):
		self.sles = get_stock_ledger_entries_for_stock_report(self.filters, self.items)
		return self.sles

	def get_purchase_order_map(self):
		self.purchase_order_map = {}

		if self.include_purchase_order_details():
			po_data = frappe.db.sql("""
				select po_item.item_code, po_item.warehouse, po.company,
					sum((po_item.qty - po_item.received_qty)*po_item.conversion_factor) as ordered_qty
				from `tabPurchase Order` po
				inner join `tabPurchase Order Item` po_item on po.name = po_item.parent
				where po.docstatus = 1 and po.status not in ('Closed', 'Delivered')
					and po_item.qty > po_item.received_qty and po_item.delivered_by_supplier = 0
					and po.transaction_date <= %s
				group by item_code, warehouse, company
			""", [self.filters.to_date], as_dict=1)

			for d in po_data:
				key = self.get_balance_key(d)
				self.purchase_order_map.setdefault(key, 0)
				self.purchase_order_map[key] += d.ordered_qty

		return self.purchase_order_map

	def get_ageing_fifo_queue(self):
		from erpnext.stock.report.stock_ageing.stock_ageing import get_fifo_queue

		if self.include_stock_ageing_data():
			self.fifo_queue_map = get_fifo_queue(self.sles,
				include_warehouse=self.is_warehouse_included(),
				include_batch=self.is_batch_included(),
				include_package=self.is_package_included(),
			)
			return self.fifo_queue_map

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
			self.item_map[item.name] = item

		return self.item_map

	def get_item_reorder_map(self):
		self.item_reorder_map = frappe._dict()

		if self.include_reorder_details() and self.items:
			item_reorder_details = frappe.db.sql("""
				select parent as item_code, warehouse, warehouse_reorder_qty, warehouse_reorder_level
				from `tabItem Reorder`
				where parent in %s
			""", [self.items], as_dict=1)

			for d in item_reorder_details:
				self.item_reorder_map[(d.item_code, d.warehouse)] = d

		return self.item_reorder_map

	def get_packing_slip_map(self):
		self.packing_slip_map = {}
		if not self.is_package_included():
			return self.packing_slip_map

		packing_slips = list(set([d.get("packing_slip") for d in self.stock_balance_map.values() if d.get("packing_slip")]))

		packing_slip_data = []
		if packing_slips:
			packing_slip_data = frappe.db.sql("""
				select name, package_type
				from `tabPacking Slip`
				where name in %s
			""", [packing_slips], as_dict=1)

		self.packing_slip_map = {}
		for d in packing_slip_data:
			self.packing_slip_map[d.name] = d

		return self.packing_slip_map

	def get_stock_balance_map(self):
		self.stock_balance_map = OrderedDict()
		precision = self.get_precision()

		for sle in self.sles:
			key = self.get_balance_key(sle)
			stock_balance = self.get_balance_dict(key)

			if not stock_balance.received_date:
				stock_balance.received_dt = combine_datetime(sle.posting_date, sle.posting_time)

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

			stock_balance.bal_qty += qty_diff
			stock_balance.bal_val += value_diff

			if flt(stock_balance.bal_qty, precision):
				stock_balance.val_rate = stock_balance.bal_val / flt(stock_balance.bal_qty, precision)
				stock_balance.val_rate = flt(stock_balance.val_rate, precision)

		if self.purchase_order_map:
			for key, ordered_qty in self.purchase_order_map.items():
				stock_balance = self.get_balance_dict(key)
				stock_balance.ordered_qty = ordered_qty

		return self.stock_balance_map

	def clean_stock_balance_map(self):
		precision = self.get_precision()
		to_remove = []

		for key in self.stock_balance_map:
			stock_balance = self.stock_balance_map[key]
			item_details = self.item_map.get(stock_balance.item_code) or {}

			is_empty_balance = True
			for field in self.balance_value_fields:
				val = flt(stock_balance.get(field), precision)
				stock_balance[field] = val
				if field != "val_rate" and val:
					is_empty_balance = False

			if is_empty_balance and (not self.filters.get("show_zero_qty_rows") or item_details.get('disabled')):
				to_remove.append(key)

		for d in to_remove:
			self.stock_balance_map.pop(d)

		sorted_stock_balance = sorted(list(self.stock_balance_map.items()), key=lambda d: (
			not d[1].packing_slip,
			cstr(d[1].packing_slip),
			d[1].item_code,
			cstr(d[1].warehouse)
		))
		self.stock_balance_map = OrderedDict(sorted_stock_balance)

		return self.stock_balance_map

	def get_rows(self):
		from erpnext.stock.report.stock_ageing.stock_ageing import get_ageing_details

		self.rows = []
		self.conversion_factors = []

		for key, stock_balance in self.stock_balance_map.items():
			item_details = self.item_map.get(stock_balance.item_code)
			if item_details:
				use_alt_uom = self.filters.qty_field == "Contents Qty" and item_details["alt_uom"]
				alt_uom_size = item_details["alt_uom_size"] if use_alt_uom else 1.0

				package_type = self.packing_slip_map.get(stock_balance.packing_slip, {}).get("package_type")\
					if stock_balance.packing_slip else None

				reorder_details = self.item_reorder_map.get((stock_balance.item_code, stock_balance.warehouse)) or {}\
					if self.include_reorder_details() else {}

				item_reorder_level = flt(reorder_details.get("warehouse_reorder_level"))
				item_reorder_qty = flt(reorder_details.get("warehouse_reorder_qty"))

				row = {
					"item_code": stock_balance.item_code,
					"warehouse": stock_balance.warehouse,
					"company": stock_balance.company,
					"batch_no": stock_balance.batch_no,
					"packing_slip": stock_balance.packing_slip,

					"item_name": item_details["item_name"],
					"disable_item_formatter": cint(self.show_item_name),
					"item_group": item_details["item_group"],
					"brand": item_details["brand"],
					"description": item_details["description"],

					"package_type": package_type,

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

				if self.include_stock_ageing_data():
					fifo_queue = self.fifo_queue_map.get(key, {}).get('fifo_queue')
					if fifo_queue:
						ageing_details = get_ageing_details(fifo_queue, self.filters.to_date)
						row.update(ageing_details)

				self.rows.append(row)

		return self.rows

	def get_balance_dict(self, key):
		if key not in self.stock_balance_map:
			balance_key_fields = self.get_balance_fields()
			balance_key_dict = dict(zip(balance_key_fields, key))

			empty_balance = {f: 0 for f in self.balance_value_fields}
			self.stock_balance_map[key] = frappe._dict(empty_balance)
			self.stock_balance_map[key].update(balance_key_dict)

		return self.stock_balance_map[key]

	balance_value_fields = [
		"opening_qty", "opening_val",
		"in_qty", "in_val",
		"purchase_qty", "purchase_val",
		"purchase_return_qty", "purchase_return_val",
		"out_qty", "out_val",
		"sales_qty", "sales_val",
		"sales_return_qty", "sales_return_val",
		"reconcile_qty", "reconcile_val",
		"bal_qty", "bal_val",
		"ordered_qty", "projected_qty",
		"val_rate"
	]

	def get_balance_key(self, d):
		return get_key(d,
			include_warehouse=self.is_warehouse_included(),
			include_batch=self.is_batch_included(),
			include_package=self.is_package_included()
		)

	def get_balance_fields(self):
		return get_key_fields(
			include_warehouse=self.is_warehouse_included(),
			include_batch=self.is_batch_included(),
			include_package=self.is_package_included()
		)

	def include_reorder_details(self):
		return self.is_warehouse_included() and not self.is_batch_included() and not self.is_package_included()

	def include_purchase_order_details(self):
		return self.filters.get("show_projected_qty") and not self.is_batch_included() and not self.is_package_included()

	def include_stock_ageing_data(self):
		return self.filters.get('show_stock_ageing_data')

	def is_warehouse_included(self):
		return is_warehouse_included(self.filters)

	def is_batch_included(self):
		return is_batch_included(self.filters)

	def is_package_included(self):
		return is_package_included(self.filters)

	def get_precision(self):
		return 6 if cint(frappe.db.get_default("float_precision")) <= 6 else 9

	def get_columns(self):
		self.columns = [
			{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item",
				"width": 100 if self.show_item_name else 150},
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data",
				"width": 150},
			{"label": _("Package"), "fieldname": "packing_slip", "fieldtype": "Link", "options": "Packing Slip",
				"width": 120},
			{"label": _("Package Type"), "fieldname": "package_type", "fieldtype": "Link", "options": "Package Type",
				"width": 100},
			{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse",
				"width": 120},
			{"label": _("Batch No"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch",
				"width": 140},
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
				"width": 90, "convertible": "qty", "is_reorder": True},
			{"label": _("Reorder Qty"), "fieldname": "reorder_qty", "fieldtype": "Float",
				"width": 85, "convertible": "qty", "is_reorder": True},
			{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group",
				"width": 100},
			{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand",
				"width": 90},
			{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company",
				"width": 100},
			{'label': _('Average Age'), 'fieldname': 'average_age', 'fieldtype': 'Float',
				'width': 90, "is_ageing": True},
			{'label': _('Earliest Age'), 'fieldname': 'earliest_age', 'fieldtype': 'Int',
				'width': 80, "is_ageing": True},
			{'label': _('Latest Age'), 'fieldname': 'latest_age', 'fieldtype': 'Int',
				'width': 80, "is_ageing": True},
		]

		if not self.is_warehouse_included():
			self.columns = [c for c in self.columns if c.get("fieldname") not in ("warehouse", "company")]
		if not self.is_batch_included():
			self.columns = [c for c in self.columns if c.get("fieldname") != "batch_no"]
		if not self.is_package_included():
			self.columns = [c for c in self.columns if c.get("fieldname") not in ("packing_slip", "package_type")]

		if not self.show_item_name:
			self.columns = [c for c in self.columns if c.get("fieldname") != "item_name"]

		if not self.show_amounts:
			self.columns = [c for c in self.columns if not c.get("is_value")]

		if not self.include_purchase_order_details():
			self.columns = [c for c in self.columns if not c.get("projected_column")]

		if not self.include_reorder_details():
			self.columns = [c for c in self.columns if not c.get("is_reorder")]

		if not self.include_stock_ageing_data():
			self.columns = [c for c in self.columns if not c.get("is_ageing")]

		if not self.filters.get("show_returns_separately"):
			self.columns = [c for c in self.columns if not c.get("is_return")]
			self.columns = [c for c in self.columns if not c.get("is_return")]

		if not hasattr(self, "rows") or not any(d.get("alt_uom_size") for d in self.rows):
			self.columns = [c for c in self.columns if c.get("fieldname") != "alt_uom_size"]

		return self.columns


def get_items_for_stock_report(filters):
	conditions = []
	if filters.get("item_code"):
		is_template = frappe.db.get_value("Item", filters.get('item_code'), 'has_variants')
		if is_template:
			conditions.append("item.variant_of = %(item_code)s")
		else:
			conditions.append("item.name = %(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand = %(brand)s")
		if filters.get("item_source"):
			conditions.append("item.item_source = %(item_source)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = None
	if conditions:
		items = frappe.db.sql_list("""
			select name
			from `tabItem` item
			where {0}
		""".format(" and ".join(conditions)), filters)

	return items


def get_stock_ledger_entries_for_stock_report(filters, item_list=None):
	item_conditions = ""
	if item_list:
		item_conditions = " and item_code in ({0})".format(
			', '.join([frappe.db.escape(i, percent=False) for i in item_list]))

	sle_conditions = get_sle_conditions(filters)

	sles = frappe.db.sql("""
		select
			item_code, warehouse, company, batch_no, packing_slip, serial_no,
			actual_qty, valuation_rate, qty_after_transaction, stock_value_difference,
			posting_date, posting_time, voucher_type, voucher_no
		from `tabStock Ledger Entry` force index (posting_sort_index)
		where docstatus < 2 {0} {1}
		order by posting_date, posting_time, creation, actual_qty
	""".format(item_conditions, sle_conditions), as_dict=1)

	return sles


def get_sle_conditions(filters):
	conditions = []

	if filters.get("company"):
		conditions.append("company = {0}".format(frappe.db.escape(filters.get("company"))))

	if filters.get("to_date"):
		conditions.append("posting_date <= {0}".format(frappe.db.escape(filters.get("to_date"))))

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if not warehouse_details:
			frappe.throw(_("Warehouse {0} does not exist").format(filters.get("warehouse")))

		conditions.append("""exists (select wh.name from `tabWarehouse` wh
			where wh.lft >= {0} and wh.rgt <= {1} and `tabStock Ledger Entry`.warehouse = wh.name)
		""".format(warehouse_details.lft, warehouse_details.rgt))

	elif filters.get("warehouse_type"):
		conditions.append("""exists (select name from `tabWarehouse` wh \
			where wh.warehouse_type = {0} and `tabStock Ledger Entry`.warehouse = wh.name)
		""".format(frappe.db.escape(filters.get("warehouse_type"))))

	if filters.get("batch_no"):
		conditions.append("batch_no = {0}".format(frappe.db.escape(filters.get("batch_no"))))

	if filters.get("packing_slip"):
		conditions.append("packing_slip = {0}".format(frappe.db.escape(filters.get("packing_slip"))))

	if filters.get("package_wise_stock") == "Packed Stock":
		conditions.append("(packing_slip != '' and packing_slip is not null)")
	elif filters.get("package_wise_stock") == "Unpacked Stock":
		conditions.append("(packing_slip = '' or packing_slip is null)")

	match_conditions = build_match_conditions("Stock Ledger Entry")
	if match_conditions:
		conditions.append(match_conditions)

	return " and {0}".format(" and ".join(conditions)) if conditions else ""


def is_warehouse_included(filters):
	return not cint(filters.get("consolidate_warehouse"))


def is_batch_included(filters):
	return cint(filters.get("batch_wise_stock"))


def is_package_included(filters):
	return filters.get("package_wise_stock")


def get_key(d, include_warehouse, include_batch, include_package):
	fields = get_key_fields(include_warehouse, include_batch, include_package)
	return tuple(d.get(f) or None for f in fields)


def get_key_fields(include_warehouse, include_batch, include_package):
	fields = ["item_code"]
	if include_warehouse:
		fields += ["warehouse", "company"]
	if include_batch:
		fields.append("batch_no")
	if include_package:
		fields.append("packing_slip")

	return fields
