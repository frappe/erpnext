# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff, flt, cint
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.report.stock_balance.stock_balance import get_items_for_stock_report,\
	get_stock_ledger_entries_for_stock_report, is_warehouse_included, is_batch_included, is_package_included,\
	get_key, get_key_fields


def execute(filters=None):
	return StockAgeingReport(filters).run()


class StockAgeingReport:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or today())
		self.filters.to_date = getdate(self.filters.to_date or today())

		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date cannot be after To Date"))

	def run(self):
		self.get_columns()

		self.get_items()
		if not self.items and self.items is not None:
			return self.columns, []

		self.get_stock_ledger_entries()
		if not self.sles:
			return self.columns, []

		self.get_item_details_map()
		self.get_fifo_queue_map()
		self.get_packing_slip_map()
		self.get_rows()

		return self.columns, self.rows

	def get_items(self):
		self.items = get_items_for_stock_report(self.filters)
		return self.items

	def get_stock_ledger_entries(self):
		self.sles = get_stock_ledger_entries_for_stock_report(self.filters, self.items)
		return self.sles

	def get_item_details_map(self):
		self.item_map = {}

		if not self.items:
			self.items = list(set([d.item_code for d in self.sles]))
		if not self.items:
			return self.item_map

		item_data = frappe.db.sql("""
			select
				item.name, item.item_name, item.description, item.item_group, item.brand,
				item.stock_uom, item.alt_uom, item.alt_uom_size, item.disabled
			from `tabItem` item
			where item.name in %s
		""", [self.items], as_dict=1)

		for item in item_data:
			self.item_map[item.name] = item

		return self.item_map

	def get_fifo_queue_map(self):
		self.fifo_queue_map = get_fifo_queue(self.sles,
			include_warehouse=self.is_warehouse_included(),
			include_batch=self.is_batch_included(),
			include_package=self.is_package_included(),
		)
		return self.fifo_queue_map

	def get_packing_slip_map(self):
		self.packing_slip_map = {}
		if not self.is_package_included():
			return self.packing_slip_map

		packing_slips = list(set([d['details'].get("packing_slip") for d in self.fifo_queue_map.values()\
			if d['details'].get("packing_slip")]))

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

	def is_warehouse_included(self):
		return is_warehouse_included(self.filters)

	def is_batch_included(self):
		return is_batch_included(self.filters)

	def is_package_included(self):
		return is_package_included(self.filters)

	def get_rows(self):
		self.rows = []

		for key, fifo_dict in self.fifo_queue_map.items():
			fifo_queue = fifo_dict["fifo_queue"]
			if not fifo_queue or (not fifo_dict.get("total_qty")):
				continue

			item_details = self.item_map.get(fifo_dict["details"].item_code, {})
			package_type = self.packing_slip_map.get(fifo_dict["details"].packing_slip, {}).get("package_type") \
				if fifo_dict["details"].packing_slip else None

			row = {
				"item_code": item_details.name,
				"warehouse": fifo_dict["details"].warehouse,
				"batch_no": fifo_dict["details"].batch_no,
				"packing_slip": fifo_dict["details"].packing_slip,

				"package_type": package_type,
				"item_name": item_details.item_name,
				"disable_item_formatter": cint(self.show_item_name),
				"item_group": item_details.item_group,
				"brand": item_details.brand,

				"uom": item_details.stock_uom,
				"bal_qty": fifo_dict.get("total_qty"),
			}

			ageing_details = get_ageing_details(fifo_queue, self.filters.to_date)
			row.update(ageing_details)

			self.rows.append(row)

		return self.rows

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
			{"label": _("Available Qty"), "fieldname": "bal_qty", "fieldtype": "Float",
				"width": 90},
			{"label": _("Average Age"), "fieldname": "average_age", "fieldtype": "Float",
				"width": 90},
			{"label": _("Earliest Age"), "fieldname": "earliest_age", "fieldtype": "Int",
				"width": 80},
			{"label": _("Latest Age"), "fieldname": "latest_age", "fieldtype": "Int",
				"width": 80},
			{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group",
				"width": 100},
			{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand",
				"width": 90},
		]

		if not self.is_warehouse_included():
			self.columns = [c for c in self.columns if c.get("fieldname") not in ("warehouse", "company")]
		if not self.is_batch_included():
			self.columns = [c for c in self.columns if c.get("fieldname") != "batch_no"]
		if not self.is_package_included():
			self.columns = [c for c in self.columns if c.get("fieldname") not in ("packing_slip", "package_type")]

		if not self.show_item_name:
			self.columns = [c for c in self.columns if c.get('fieldname') != 'item_name']

		return self.columns


def get_fifo_queue(sles, include_warehouse, include_batch, include_package):
	fifo_queue_map = {}
	transferred_item_details = {}
	serial_no_batch_purchase_details = {}

	for sle in sles:
		fifo_dict = get_fifo_dict(sle, fifo_queue_map,
			include_warehouse=include_warehouse,
			include_batch=include_batch,
			include_package=include_package,
		)

		fifo_queue = fifo_dict["fifo_queue"]
		transferred_item_details.setdefault((sle.voucher_no, sle.item_code), [])
		serial_no_list = get_serial_nos(sle.serial_no) if sle.serial_no else []

		if sle.actual_qty > 0:
			if transferred_item_details.get((sle.voucher_no, sle.item_code)):
				batch = transferred_item_details[(sle.voucher_no, sle.item_code)][0]
				fifo_queue.append(batch)
				transferred_item_details[((sle.voucher_no, sle.item_code))].pop(0)
			else:
				if serial_no_list:
					for serial_no in serial_no_list:
						if serial_no_batch_purchase_details.get(serial_no):
							fifo_queue.append([serial_no, serial_no_batch_purchase_details.get(serial_no)])
						else:
							serial_no_batch_purchase_details.setdefault(serial_no, sle.posting_date)
							fifo_queue.append([serial_no, sle.posting_date])
				else:
					fifo_queue.append([sle.actual_qty, sle.posting_date])
		else:
			if serial_no_list:
				for serial_no in fifo_queue:
					if serial_no[0] in serial_no_list:
						fifo_queue.remove(serial_no)
			else:
				qty_to_pop = abs(sle.actual_qty)
				while qty_to_pop:
					batch = fifo_queue[0] if fifo_queue else [0, None]
					if 0 < flt(batch[0]) <= qty_to_pop:
						# if batch qty > 0
						# not enough or exactly same qty in current batch, clear batch
						qty_to_pop -= flt(batch[0])
						transferred_item_details[(sle.voucher_no, sle.item_code)].append(fifo_queue.pop(0))
					else:
						# all from current batch
						batch[0] = flt(batch[0]) - qty_to_pop
						transferred_item_details[(sle.voucher_no, sle.item_code)].append([qty_to_pop, batch[1]])
						qty_to_pop = 0

		fifo_dict["qty_after_transaction"] = sle.qty_after_transaction

		if "total_qty" not in fifo_dict:
			fifo_dict["total_qty"] = sle.actual_qty
		else:
			fifo_dict["total_qty"] += sle.actual_qty

	# sort and filter
	sort_key = lambda x: x[1]
	for key in fifo_queue_map:
		fifo_queue_map[key]['fifo_queue'] = sorted(filter(sort_key, fifo_queue_map[key]['fifo_queue']), key=sort_key)

	return fifo_queue_map


def get_fifo_dict(sle, fifo_queue_map, include_warehouse, include_batch, include_package):
	key = get_key(sle,
		include_warehouse=include_warehouse,
		include_batch=include_batch,
		include_package=include_package
	)

	if key not in fifo_queue_map:
		key_fields = get_key_fields(include_warehouse=include_warehouse, include_batch=include_batch, include_package=include_package)
		key_dict = frappe._dict(zip(key_fields, key))

		fifo_queue_map[key] = frappe._dict({
			"details": key_dict, "fifo_queue": []
		})

	return fifo_queue_map[key]


def get_ageing_details(fifo_queue, to_date):
	to_date = getdate(to_date)

	return frappe._dict({
		"average_age": get_average_age(fifo_queue, to_date),
		"earliest_age": date_diff(to_date, fifo_queue[0][1]),
		"latest_age": date_diff(to_date, fifo_queue[-1][1])
	})


def get_average_age(fifo_queue, to_date):
	age_qty = 0.0
	total_qty = 0.0

	for batch in fifo_queue:
		batch_age = date_diff(to_date, batch[1])

		if type(batch[0]) in ['int', 'float']:
			age_qty += batch_age * batch[0]
			total_qty += batch[0]
		else:
			age_qty += batch_age * 1
			total_qty += 1

	return (age_qty / total_qty) if total_qty else 0.0
