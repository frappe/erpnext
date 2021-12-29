# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from operator import itemgetter
from typing import Dict, List, Tuple, Union

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

Filters = frappe._dict

def execute(filters: Filters = None) -> Tuple:
	to_date = filters["to_date"]
	columns = get_columns(filters)

	item_details = FIFOSlots(filters).generate()
	data = format_report_data(filters, item_details, to_date)

	chart_data = get_chart_data(data, filters)

	return columns, data, None, chart_data

def format_report_data(filters: Filters, item_details: Dict, to_date: str) -> List[Dict]:
	"Returns ordered, formatted data with ranges."
	_func = itemgetter(1)
	data = []

	for item, item_dict in item_details.items():
		earliest_age, latest_age = 0, 0
		details = item_dict["details"]

		fifo_queue = sorted(filter(_func, item_dict["fifo_queue"]), key=_func)

		if not fifo_queue: continue

		average_age = get_average_age(fifo_queue, to_date)
		earliest_age = date_diff(to_date, fifo_queue[0][1])
		latest_age = date_diff(to_date, fifo_queue[-1][1])
		range1, range2, range3, above_range3 = get_range_age(filters, fifo_queue, to_date, item_dict)

		row = [details.name, details.item_name, details.description,
			details.item_group, details.brand]

		if filters.get("show_warehouse_wise_stock"):
			row.append(details.warehouse)

		row.extend([item_dict.get("total_qty"), average_age,
			range1, range2, range3, above_range3,
			earliest_age, latest_age,
			details.stock_uom])

		data.append(row)

	return data

def get_average_age(fifo_queue: List, to_date: str) -> float:
	batch_age = age_qty = total_qty = 0.0
	for batch in fifo_queue:
		batch_age = date_diff(to_date, batch[1])

		if isinstance(batch[0], (int, float)):
			age_qty += batch_age * batch[0]
			total_qty += batch[0]
		else:
			age_qty += batch_age * 1
			total_qty += 1

	return flt(age_qty / total_qty, 2) if total_qty else 0.0

def get_range_age(filters: Filters, fifo_queue: List, to_date: str, item_dict: Dict) -> Tuple:
	range1 = range2 = range3 = above_range3 = 0.0

	for item in fifo_queue:
		age = date_diff(to_date, item[1])
		qty = flt(item[0]) if not item_dict["has_serial_no"] else 1.0

		if age <= filters.range1:
			range1 += qty
		elif age <= filters.range2:
			range2 += qty
		elif age <= filters.range3:
			range3 += qty
		else:
			above_range3 += qty

	return range1, range2, range3, above_range3

def get_columns(filters: Filters) -> List[Dict]:
	range_columns = []
	setup_ageing_columns(filters, range_columns)
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 100
		},
		{
			"label": _("Brand"),
			"fieldname": "brand",
			"fieldtype": "Link",
			"options": "Brand",
			"width": 100
		}]

	if filters.get("show_warehouse_wise_stock"):
		columns +=[{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 100
		}]

	columns.extend([
		{
			"label": _("Available Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Average Age"),
			"fieldname": "average_age",
			"fieldtype": "Float",
			"width": 100
		}])
	columns.extend(range_columns)
	columns.extend([
		{
			"label": _("Earliest"),
			"fieldname": "earliest",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("Latest"),
			"fieldname": "latest",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("UOM"),
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100
		}
	])

	return columns

def get_chart_data(data: List, filters: Filters) -> Dict:
	if not data:
		return []

	labels, datapoints = [], []

	if filters.get("show_warehouse_wise_stock"):
		return {}

	data.sort(key = lambda row: row[6], reverse=True)

	if len(data) > 10:
		data = data[:10]

	for row in data:
		labels.append(row[0])
		datapoints.append(row[6])

	return {
		"data" : {
			"labels": labels,
			"datasets": [
				{
					"name": _("Average Age"),
					"values": datapoints
				}
			]
		},
		"type" : "bar"
	}

def setup_ageing_columns(filters: Filters, range_columns: List):
	ranges = [
		f"0 - {filters['range1']}",
		f"{cint(filters['range1']) + 1} - {cint(filters['range2'])}",
		f"{cint(filters['range2']) + 1} - {cint(filters['range3'])}",
		f"{cint(filters['range3']) + 1} - {_('Above')}"
	]
	for i, label in enumerate(ranges):
		fieldname = 'range' + str(i+1)
		add_column(range_columns, label=f"Age ({label})",fieldname=fieldname)

def add_column(range_columns: List, label:str, fieldname: str, fieldtype: str = 'Float', width: int = 140):
	range_columns.append(dict(
		label=label,
		fieldname=fieldname,
		fieldtype=fieldtype,
		width=width
	))


class FIFOSlots:
	"Returns FIFO computed slots of inwarded stock as per date."

	def __init__(self, filters: Dict = None , sle: List = None):
		self.item_details = {}
		self.transferred_item_details = {}
		self.serial_no_batch_purchase_details = {}
		self.filters = filters
		self.sle = sle

	def generate(self) -> Dict:
		"""
			Returns dict of the foll.g structure:
			Key = Item A / (Item A, Warehouse A)
			Key: {
				'details' -> Dict: ** item details **,
				'fifo_queue' -> List: ** list of lists containing entries/slots for existing stock,
					consumed/updated and maintained via FIFO. **
			}
		"""
		if self.sle is None:
			self.sle = self.__get_stock_ledger_entries()

		for d in self.sle:
			key, fifo_queue, transferred_item_key = self.__init_key_stores(d)

			if d.voucher_type == "Stock Reconciliation":
				prev_balance_qty = self.item_details[key].get("qty_after_transaction", 0)
				d.actual_qty = flt(d.qty_after_transaction) - flt(prev_balance_qty)

			serial_nos = get_serial_nos(d.serial_no) if d.serial_no else []

			if d.actual_qty > 0:
				self.__compute_incoming_stock(d, fifo_queue, transferred_item_key, serial_nos)
			else:
				self.__compute_outgoing_stock(d, fifo_queue, transferred_item_key, serial_nos)

			self.__update_balances(d, key)

		return self.item_details

	def __init_key_stores(self, row: Dict) -> Tuple:
		"Initialise keys and FIFO Queue."

		key = (row.name, row.warehouse) if self.filters.get('show_warehouse_wise_stock') else row.name
		self.item_details.setdefault(key, {"details": row, "fifo_queue": []})
		fifo_queue = self.item_details[key]["fifo_queue"]

		transferred_item_key = (row.voucher_no, row.name, row.warehouse)
		self.transferred_item_details.setdefault(transferred_item_key, [])

		return key, fifo_queue, transferred_item_key

	def __compute_incoming_stock(self, row: Dict, fifo_queue: List, transfer_key: Tuple, serial_nos: List):
		"Update FIFO Queue on inward stock."

		if self.transferred_item_details.get(transfer_key):
			# inward/outward from same voucher, item & warehouse
			slot = self.transferred_item_details[transfer_key].pop(0)
			fifo_queue.append(slot)
		else:
			if not serial_nos:
				if fifo_queue and flt(fifo_queue[0][0]) < 0:
					# neutralize negative stock by adding positive stock
					fifo_queue[0][0] += flt(row.actual_qty)
					fifo_queue[0][1] = row.posting_date
				else:
					fifo_queue.append([flt(row.actual_qty), row.posting_date])
				return

			for serial_no in serial_nos:
				if self.serial_no_batch_purchase_details.get(serial_no):
					fifo_queue.append([serial_no, self.serial_no_batch_purchase_details.get(serial_no)])
				else:
					self.serial_no_batch_purchase_details.setdefault(serial_no, row.posting_date)
					fifo_queue.append([serial_no, row.posting_date])

	def __compute_outgoing_stock(self, row: Dict, fifo_queue: List, transfer_key: Tuple, serial_nos: List):
		"Update FIFO Queue on outward stock."
		if serial_nos:
			fifo_queue[:] = [serial_no for serial_no in fifo_queue if serial_no[0] not in serial_nos]
			return

		qty_to_pop = abs(row.actual_qty)
		while qty_to_pop:
			slot = fifo_queue[0] if fifo_queue else [0, None]
			if 0 < flt(slot[0]) <= qty_to_pop:
				# qty to pop >= slot qty
				# if +ve and not enough or exactly same balance in current slot, consume whole slot
				qty_to_pop -= flt(slot[0])
				self.transferred_item_details[transfer_key].append(fifo_queue.pop(0))
			elif not fifo_queue:
				# negative stock, no balance but qty yet to consume
				fifo_queue.append([-(qty_to_pop), row.posting_date])
				self.transferred_item_details[transfer_key].append([row.actual_qty, row.posting_date])
				qty_to_pop = 0
			else:
				# qty to pop < slot qty, ample balance
				# consume actual_qty from first slot
				slot[0] = flt(slot[0]) - qty_to_pop
				self.transferred_item_details[transfer_key].append([qty_to_pop, slot[1]])
				qty_to_pop = 0

	def __update_balances(self, row: Dict, key: Union[Tuple, str]):
		self.item_details[key]["qty_after_transaction"] = row.qty_after_transaction

		if "total_qty" not in self.item_details[key]:
			self.item_details[key]["total_qty"] = row.actual_qty
		else:
			self.item_details[key]["total_qty"] += row.actual_qty

		self.item_details[key]["has_serial_no"] = row.has_serial_no

	def __get_stock_ledger_entries(self) -> List[Dict]:
		sle = frappe.qb.DocType("Stock Ledger Entry")
		item = self.__get_item_query() # used as derived table in sle query

		sle_query = (
			frappe.qb.from_(sle).from_(item)
			.select(
				item.name, item.item_name, item.item_group,
				item.brand, item.description,
				item.stock_uom, item.has_serial_no,
				sle.actual_qty, sle.posting_date,
				sle.voucher_type, sle.voucher_no,
				sle.serial_no, sle.batch_no,
				sle.qty_after_transaction, sle.warehouse
			).where(
				(sle.item_code == item.name)
				& (sle.company == self.filters.get("company"))
				& (sle.posting_date <= self.filters.get("to_date"))
				& (sle.is_cancelled != 1)
			)
		)

		if self.filters.get("warehouse"):
			sle_query = self.__get_warehouse_conditions(sle, sle_query)

		sle_query = sle_query.orderby(
			sle.posting_date, sle.posting_time, sle.creation, sle.actual_qty
		)

		return sle_query.run(as_dict=True)

	def __get_item_query(self) -> str:
		item_table = frappe.qb.DocType("Item")

		item = frappe.qb.from_("Item").select(
			"name", "item_name", "description", "stock_uom",
			"brand", "item_group", "has_serial_no"
		)

		if self.filters.get("item_code"):
			item = item.where(item_table.item_code == self.filters.get("item_code"))

		if self.filters.get("brand"):
			item = item.where(item_table.brand == self.filters.get("brand"))

		return item

	def __get_warehouse_conditions(self, sle, sle_query) -> str:
		warehouse = frappe.qb.DocType("Warehouse")
		lft, rgt = frappe.db.get_value(
			"Warehouse",
			self.filters.get("warehouse"),
			['lft', 'rgt']
		)

		warehouse_results = (
			frappe.qb.from_(warehouse)
			.select("name").where(
				(warehouse.lft >= lft)
				& (warehouse.rgt <= rgt)
			).run()
		)
		warehouse_results = [x[0] for x in warehouse_results]

		return sle_query.where(sle.warehouse.isin(warehouse_results))
