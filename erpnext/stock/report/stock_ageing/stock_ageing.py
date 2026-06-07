# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from collections.abc import Iterator
from operator import itemgetter

import frappe
from frappe import _
from frappe.query_builder.functions import Abs, Count
from frappe.utils import cint, date_diff, flt, get_datetime

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.valuation import round_off_if_near_zero

Filters = frappe._dict

FIFO_POSTING_DATE_INDEX = -2
FIFO_QTY_INDEX = 0
FIFO_DATE_INDEX = 1
FIFO_VALUE_INDEX = 2

BATCH_SLOT_SIZE = 5
BATCH_SLOT_BATCH_INDEX = 0
BATCH_SLOT_VALUATION_INDEX = 1
BATCH_SLOT_QTY_INDEX = 2
BATCH_SLOT_DATE_INDEX = 3
BATCH_SLOT_VALUE_INDEX = 4

AVERAGE_AGE_COLUMN = 6
MAX_CHART_ITEMS = 10


def execute(filters: Filters = None) -> tuple:
	to_date = filters["to_date"]
	filters.ranges = get_age_ranges(filters.range)
	columns = get_columns(filters)

	item_details = FIFOSlots(filters).generate()
	data = format_report_data(filters, item_details, to_date)

	chart_data = get_chart_data(data, filters)

	return columns, data, None, chart_data


def get_age_ranges(age_range: str) -> list[str]:
	return [num.strip() for num in age_range.split(",") if num.strip().isdigit()]


def get_float_precision() -> int:
	return cint(frappe.db.get_single_value("System Settings", "float_precision", cache=True))


def format_report_data(filters: Filters, item_details: dict, to_date: str) -> list[list]:
	"Returns ordered, formatted data with ranges."
	data = []

	precision = get_float_precision()

	for _item, item_dict in item_details.items():
		if not flt(item_dict.get("total_qty"), precision):
			continue

		details = item_dict["details"]
		fifo_queue = get_report_fifo_queue(item_dict["fifo_queue"], details.has_batch_no)
		if not fifo_queue:
			continue

		data.append(get_report_row(filters, item_dict, fifo_queue, to_date, precision))

	return data


def get_report_fifo_queue(fifo_queue: list, has_batch_no: bool) -> list:
	get_posting_date = itemgetter(FIFO_POSTING_DATE_INDEX)
	fifo_queue = sorted([slot for slot in fifo_queue if get_posting_date(slot)], key=get_posting_date)

	if has_batch_no:
		return [get_batch_report_slot(slot) for slot in fifo_queue]

	return fifo_queue


def get_batch_report_slot(slot: list) -> list:
	if is_batch_slot(slot):
		return slot[BATCH_SLOT_QTY_INDEX:]

	return slot


def get_report_row(filters: Filters, item_dict: dict, fifo_queue: list, to_date: str, precision: int) -> list:
	details = item_dict["details"]
	range_values = get_range_age(filters, fifo_queue, to_date, item_dict, precision)
	row = [details.name, details.item_name, details.description, details.item_group, details.brand]

	if filters.get("show_warehouse_wise_stock"):
		row.append(details.warehouse)

	row.extend(
		[
			flt(item_dict.get("total_qty"), precision),
			get_average_age(fifo_queue, to_date),
			*range_values,
			date_diff(to_date, fifo_queue[0][FIFO_DATE_INDEX]),
			date_diff(to_date, fifo_queue[-1][FIFO_DATE_INDEX]),
			details.stock_uom,
		]
	)

	return row


def get_average_age(fifo_queue: list, to_date: str) -> float:
	age_qty = total_qty = 0.0
	for slot in fifo_queue:
		qty = get_slot_qty(slot)
		age_qty += date_diff(to_date, slot[FIFO_DATE_INDEX]) * qty
		total_qty += qty

	return flt(age_qty / total_qty, 2) if total_qty else 0.0


def get_slot_qty(slot: list) -> float:
	if is_qty_slot(slot):
		return slot[FIFO_QTY_INDEX]

	return 1.0


def get_range_age(
	filters: Filters, fifo_queue: list, to_date: str, item_dict: dict, precision: int | None = None
) -> list:
	precision = precision if precision is not None else get_float_precision()
	range_values = [0.0] * ((len(filters.ranges) * 2) + 2)

	for slot in fifo_queue:
		bucket_index = get_age_bucket_index(filters.ranges, slot, to_date)
		qty = 1.0 if item_dict["has_serial_no"] else flt(slot[FIFO_QTY_INDEX])
		stock_value = flt(slot[FIFO_VALUE_INDEX])
		add_to_range_bucket(range_values, bucket_index, qty, stock_value, precision)

	return range_values


def get_age_bucket_index(age_ranges: list, slot: list, to_date: str) -> int:
	age = flt(date_diff(to_date, slot[FIFO_DATE_INDEX]))

	for index, age_limit in enumerate(age_ranges):
		if age <= flt(age_limit):
			return index * 2

	return len(age_ranges) * 2


def add_to_range_bucket(
	range_values: list, bucket_index: int, qty: float, stock_value: float, precision: int
) -> None:
	range_values[bucket_index] = flt(range_values[bucket_index] + qty, precision)
	range_values[bucket_index + 1] = flt(range_values[bucket_index + 1] + stock_value, precision)

	if range_values[bucket_index] == 0.0 and round_off_if_near_zero(range_values[bucket_index + 1], 2) == 0:
		range_values[bucket_index + 1] = 0.0


def get_columns(filters: Filters) -> list[dict]:
	range_columns = []
	setup_ageing_columns(filters, range_columns)
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100,
			"sticky": "True",
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 100},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 200},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 100,
		},
		{
			"label": _("Brand"),
			"fieldname": "brand",
			"fieldtype": "Link",
			"options": "Brand",
			"width": 100,
		},
	]

	if filters.get("show_warehouse_wise_stock"):
		columns += [
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 100,
				"sticky": "True",
			}
		]

	columns.extend(
		[
			{"label": _("Available Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
			{"label": _("Average Age"), "fieldname": "average_age", "fieldtype": "Float", "width": 100},
		]
	)
	columns.extend(range_columns)
	columns.extend(
		[
			{"label": _("Earliest"), "fieldname": "earliest", "fieldtype": "Int", "width": 80},
			{"label": _("Latest"), "fieldname": "latest", "fieldtype": "Int", "width": 80},
			{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 100},
		]
	)

	return columns


def get_chart_data(data: list, filters: Filters) -> dict:
	if not data:
		return []

	labels, datapoints = [], []

	if filters.get("show_warehouse_wise_stock"):
		return {}

	data.sort(key=lambda row: row[AVERAGE_AGE_COLUMN], reverse=True)

	if len(data) > MAX_CHART_ITEMS:
		data = data[:MAX_CHART_ITEMS]

	for row in data:
		labels.append(row[0])
		datapoints.append(row[AVERAGE_AGE_COLUMN])

	return {
		"data": {"labels": labels, "datasets": [{"name": _("Average Age"), "values": datapoints}]},
		"type": "bar",
	}


def setup_ageing_columns(filters: Filters, range_columns: list):
	prev_range_value = 0
	ranges = []
	for age_range in filters.ranges:
		ranges.append(f"{prev_range_value} - {age_range}")
		prev_range_value = cint(age_range) + 1

	ranges.append(f"{prev_range_value} - Above")

	for i, label in enumerate(ranges):
		fieldname = "range" + str(i + 1)
		add_column(range_columns, label=_("Age ({0})").format(label), fieldname=fieldname)
		add_column(range_columns, label=_("Value ({0})").format(label), fieldname=fieldname + "value")


def add_column(range_columns: list, label: str, fieldname: str, fieldtype: str = "Float", width: int = 140):
	range_columns.append(dict(label=label, fieldname=fieldname, fieldtype=fieldtype, width=width))


def is_batch_slot(slot: list) -> bool:
	return len(slot) == BATCH_SLOT_SIZE


def is_qty_slot(slot: list) -> bool:
	return isinstance(slot[FIFO_QTY_INDEX], int | float)


class FIFOSlots:
	"Returns FIFO computed slots of inwarded stock as per date."

	def __init__(self, filters: dict | None = None, sle: list | None = None):
		self.item_details = {}
		self.transferred_item_details = {}
		self.serial_no_details = {}
		self.batch_no_details = {}
		self.batchwise_valuation_by_batch = {}
		self.filters = filters
		self.sle = sle

	def generate(self) -> dict:
		"""
		Returns dict of the following structure:
		Key = Item A / (Item A, Warehouse A)
		Key: {
		                'details' -> Dict: ** item details **,
		                'fifo_queue' -> List: ** list of lists containing entries/slots for existing stock,
		                                consumed/updated and maintained via FIFO. **
		}
		"""
		stock_ledger_entries = self.sle
		bundle_wise_serial_nos, bundle_wise_batch_nos = self._get_bundle_wise_details(stock_ledger_entries)

		# prepare single sle voucher detail lookup
		self.prepare_stock_reco_voucher_wise_count()

		with frappe.db.unbuffered_cursor():
			if stock_ledger_entries is None:
				stock_ledger_entries = self._get_stock_ledger_entries()

			for row in stock_ledger_entries:
				self._process_stock_ledger_entry(row, bundle_wise_serial_nos, bundle_wise_batch_nos)

			# Note that stock_ledger_entries is an iterator, you can not reuse it like a list
			del stock_ledger_entries

		if not self.filters.get("show_warehouse_wise_stock"):
			# (Item 1, WH 1), (Item 1, WH 2) => (Item 1)
			self.item_details = self._aggregate_details_by_item(self.item_details)

		return self.item_details

	def _get_bundle_wise_details(self, stock_ledger_entries: list | None) -> tuple[dict, dict]:
		if stock_ledger_entries is not None:
			return frappe._dict({}), frappe._dict({})

		return self._get_bundle_wise_serial_nos(), self._get_bundle_wise_batch_nos()

	def _process_stock_ledger_entry(
		self, row: dict, bundle_wise_serial_nos: dict, bundle_wise_batch_nos: dict
	) -> None:
		key, fifo_queue, transferred_item_key = self._init_key_stores(row)
		prev_balance_qty = self.item_details[key].get("qty_after_transaction", 0)

		self._set_stock_reconciliation_actual_qty(row, key, fifo_queue, prev_balance_qty)
		serial_nos, batch_nos = self._get_serial_and_batch_nos(
			row, bundle_wise_serial_nos, bundle_wise_batch_nos
		)

		if row.actual_qty > 0:
			self._compute_incoming_stock(row, fifo_queue, transferred_item_key, serial_nos, batch_nos)
		else:
			self._compute_outgoing_stock(row, fifo_queue, transferred_item_key, serial_nos, batch_nos)

		self._update_balances(row, key)
		self._trim_serial_fifo_queue(row, key, fifo_queue)

	def _set_stock_reconciliation_actual_qty(
		self, row: dict, key: tuple, fifo_queue: list, prev_balance_qty: float
	) -> None:
		if row.voucher_type != "Stock Reconciliation":
			return

		if not row.batch_no or row.serial_no or row.serial_and_batch_bundle:
			if row.voucher_detail_no in self.stock_reco_voucher_wise_count:
				# Legacy reconciliation with a single SLE has qty_after_transaction and
				# stock_value_difference without an outward entry, so reset the queue first.
				row.stock_value_difference = flt(row.qty_after_transaction * row.valuation_rate)
				row.actual_qty = row.qty_after_transaction
				self.item_details[key]["qty_after_transaction"] = 0
				self.item_details[key]["total_qty"] = 0
				fifo_queue.clear()
				return

		# Stock reconciliation stores the final balance; FIFO needs the movement delta.
		row.actual_qty = flt(row.qty_after_transaction) - flt(prev_balance_qty)

	def _get_serial_and_batch_nos(
		self, row: dict, bundle_wise_serial_nos: dict, bundle_wise_batch_nos: dict
	) -> tuple[list, list]:
		from erpnext.stock.serial_batch_bundle import get_serial_nos_from_bundle

		serial_nos = get_serial_nos(row.serial_no) if row.serial_no else []
		batch_nos = self._get_row_batch_nos(row)

		if row.serial_and_batch_bundle:
			if row.has_serial_no:
				if bundle_wise_serial_nos:
					serial_nos = bundle_wise_serial_nos.get(row.serial_and_batch_bundle) or []
				else:
					serial_nos = sorted(get_serial_nos_from_bundle(row.serial_and_batch_bundle)) or []
			elif row.has_batch_no:
				if bundle_wise_batch_nos:
					batch_nos = bundle_wise_batch_nos.get(row.serial_and_batch_bundle) or []
				else:
					batch_nos = (
						self._get_bundle_wise_batch_nos(row.serial_and_batch_bundle).get(
							row.serial_and_batch_bundle
						)
						or []
					)

		return self.uppercase_serial_nos(serial_nos), batch_nos

	def _get_row_batch_nos(self, row: dict) -> list:
		if not row.batch_no:
			return []

		return [
			[
				row.batch_no.upper(),
				self._get_batchwise_valuation(row.batch_no),
				abs(row.actual_qty),
				abs(row.stock_value_difference),
			]
		]

	def _trim_serial_fifo_queue(self, row: dict, key: tuple, fifo_queue: list) -> None:
		if not row.has_serial_no:
			return

		qty_after = cint(self.item_details[key]["qty_after_transaction"])
		if qty_after <= 0:
			fifo_queue.clear()
		elif len(fifo_queue) > qty_after:
			fifo_queue[:] = fifo_queue[:qty_after]

	def uppercase_serial_nos(self, serial_nos):
		"Convert serial nos to uppercase for uniformity."
		return [sn.upper() for sn in serial_nos]

	def _get_batchwise_valuation(self, batch_no: str):
		if batch_no not in self.batchwise_valuation_by_batch:
			self.batchwise_valuation_by_batch[batch_no] = frappe.db.get_value(
				"Batch", batch_no, "use_batchwise_valuation"
			)

		return self.batchwise_valuation_by_batch[batch_no]

	def _init_key_stores(self, row: dict) -> tuple:
		"Initialise keys and FIFO Queue."

		key = (row.name, row.warehouse)
		self.item_details.setdefault(key, {"details": row, "fifo_queue": []})
		fifo_queue = self.item_details[key]["fifo_queue"]

		transferred_item_key = (row.voucher_no, row.name, row.warehouse)
		self.transferred_item_details.setdefault(transferred_item_key, [])

		return key, fifo_queue, transferred_item_key

	def _compute_incoming_stock(
		self, row: dict, fifo_queue: list, transfer_key: tuple, serial_nos: list, batch_nos: list
	):
		"Update FIFO Queue on inward stock."
		transfer_data = self.transferred_item_details.get(transfer_key)
		if transfer_data:
			# inward/outward from same voucher, item & warehouse
			# eg: Repack with same item, Stock reco for batch item
			# consume transfer data and add stock to fifo queue
			self._adjust_incoming_transfer_qty(
				transfer_data,
				fifo_queue,
				row,
				batch_nos,
				serial_nos=serial_nos if row.get("has_serial_no") else None,
			)
		elif serial_nos and row.get("has_serial_no"):
			self._add_serial_fifo_slots(row, fifo_queue, serial_nos)
		elif batch_nos and row.get("has_batch_no"):
			self._add_batch_fifo_slots(row, fifo_queue, batch_nos)
		elif fifo_queue and flt(fifo_queue[0][FIFO_QTY_INDEX]) <= 0:
			self._add_to_negative_fifo_head(row, fifo_queue)
		else:
			fifo_queue.append([flt(row.actual_qty), row.posting_date, flt(row.stock_value_difference)])

	def _add_serial_fifo_slots(self, row: dict, fifo_queue: list, serial_nos: list) -> None:
		valuation = row.stock_value_difference / row.actual_qty
		for serial_no in serial_nos:
			posting_date = self.serial_no_details.setdefault(serial_no, row.posting_date)
			fifo_queue.append([serial_no, posting_date, valuation])

	def _add_batch_fifo_slots(self, row: dict, fifo_queue: list, batch_nos: list) -> None:
		for batch_no, use_batchwise_valuation, qty, stock_value_difference in batch_nos:
			qty, stock_value_difference = self._neutralize_negative_batch_stock(
				fifo_queue, row, batch_no, use_batchwise_valuation, qty, stock_value_difference
			)

			if not qty:
				continue

			posting_date = self.batch_no_details.setdefault(batch_no, row.posting_date)
			fifo_queue.append([batch_no, use_batchwise_valuation, qty, posting_date, stock_value_difference])

	def _neutralize_negative_batch_stock(
		self,
		fifo_queue: list,
		row: dict,
		batch_no: str,
		use_batchwise_valuation: bool,
		qty: float,
		stock_value_difference: float,
	) -> tuple[float, float]:
		qty = flt(qty)
		stock_value_difference = flt(stock_value_difference)

		if not qty:
			return qty, stock_value_difference

		for slot in list(fifo_queue):
			if not self._is_matching_negative_batch_slot(slot, batch_no, use_batchwise_valuation):
				continue

			qty_to_adjust = min(qty, abs(flt(slot[BATCH_SLOT_QTY_INDEX])))
			value_to_adjust = (
				stock_value_difference
				if qty_to_adjust == qty
				else flt(stock_value_difference * (qty_to_adjust / qty))
			)

			slot[BATCH_SLOT_QTY_INDEX] = flt(slot[BATCH_SLOT_QTY_INDEX]) + qty_to_adjust
			slot[BATCH_SLOT_DATE_INDEX] = row.posting_date
			slot[BATCH_SLOT_VALUE_INDEX] = flt(slot[BATCH_SLOT_VALUE_INDEX]) + value_to_adjust

			qty = flt(qty - qty_to_adjust)
			stock_value_difference = flt(stock_value_difference - value_to_adjust)

			if not flt(slot[BATCH_SLOT_QTY_INDEX]) and not flt(slot[BATCH_SLOT_VALUE_INDEX]):
				fifo_queue.remove(slot)

			if not qty:
				break

		return qty, stock_value_difference

	def _is_matching_negative_batch_slot(
		self, slot: list, batch_no: str, use_batchwise_valuation: bool, include_zero_qty: bool = False
	) -> bool:
		if not is_batch_slot(slot):
			return False

		qty = flt(slot[BATCH_SLOT_QTY_INDEX])

		return (
			slot[BATCH_SLOT_BATCH_INDEX] == batch_no
			and slot[BATCH_SLOT_VALUATION_INDEX] == use_batchwise_valuation
			and (qty <= 0 if include_zero_qty else qty < 0)
		)

	def _add_to_negative_fifo_head(self, row: dict, fifo_queue: list) -> None:
		fifo_queue[0][FIFO_QTY_INDEX] += flt(row.actual_qty)
		fifo_queue[0][FIFO_DATE_INDEX] = row.posting_date
		fifo_queue[0][FIFO_VALUE_INDEX] += flt(row.stock_value_difference)

	def _compute_outgoing_stock(
		self, row: dict, fifo_queue: list, transfer_key: tuple, serial_nos: list, batch_nos: list
	):
		"Update FIFO Queue on outward stock."
		if serial_nos:
			self._consume_serial_fifo_slots(fifo_queue, serial_nos)
		elif batch_nos:
			self._consume_batch_fifo_slots(row, fifo_queue, transfer_key, batch_nos)
		else:
			self._consume_fifo_slots(row, fifo_queue, transfer_key)

	def _consume_serial_fifo_slots(self, fifo_queue: list, serial_nos: list) -> None:
		fifo_queue[:] = [slot for slot in fifo_queue if slot[FIFO_QTY_INDEX] not in serial_nos]

	def _consume_batch_fifo_slots(
		self, row: dict, fifo_queue: list, transfer_key: tuple, batch_nos: list
	) -> None:
		for batch_no, use_batchwise_valuation, qty, stock_value_difference in batch_nos:
			items_to_remove = []

			for slot in fifo_queue:
				if not self._can_consume_batch_slot(slot, batch_no, use_batchwise_valuation):
					continue

				slot_qty = flt(slot[BATCH_SLOT_QTY_INDEX])
				slot_stock_value = flt(slot[BATCH_SLOT_VALUE_INDEX])

				if slot_qty <= qty:
					qty -= slot_qty
					stock_value_difference -= slot_stock_value
					self.transferred_item_details[transfer_key].append(
						[slot_qty, slot[BATCH_SLOT_DATE_INDEX], slot_stock_value]
					)
					items_to_remove.append(slot)
				else:
					slot[BATCH_SLOT_QTY_INDEX] = slot_qty - qty
					# Preserve ledger valuation (moving average / SLE value), not slot proportional value.
					slot[BATCH_SLOT_VALUE_INDEX] = slot_stock_value - stock_value_difference
					self.transferred_item_details[transfer_key].append(
						[qty, slot[BATCH_SLOT_DATE_INDEX], stock_value_difference]
					)
					qty = 0
					stock_value_difference = 0
					break

			for item in items_to_remove:
				fifo_queue.remove(item)

			if qty:
				self._append_negative_batch_slot(
					row,
					fifo_queue,
					transfer_key,
					batch_no,
					use_batchwise_valuation,
					qty,
					stock_value_difference,
				)

	def _can_consume_batch_slot(self, slot: list, batch_no: str, use_batchwise_valuation: bool) -> bool:
		if not is_batch_slot(slot):
			return False

		if flt(slot[BATCH_SLOT_QTY_INDEX]) <= 0:
			return False

		if use_batchwise_valuation:
			return slot[BATCH_SLOT_BATCH_INDEX] == batch_no

		return not slot[BATCH_SLOT_VALUATION_INDEX]

	def _append_negative_batch_slot(
		self,
		row: dict,
		fifo_queue: list,
		transfer_key: tuple,
		batch_no: str,
		use_batchwise_valuation: bool,
		qty: float,
		stock_value_difference: float,
	) -> None:
		fifo_queue.append(
			[batch_no, use_batchwise_valuation, -(qty), row.posting_date, -(stock_value_difference)]
		)
		self.transferred_item_details[transfer_key].append([qty, row.posting_date, stock_value_difference])

	def _consume_fifo_slots(self, row: dict, fifo_queue: list, transfer_key: tuple) -> None:
		qty_to_pop = abs(row.actual_qty)
		stock_value = abs(row.stock_value_difference)

		while qty_to_pop:
			slot = fifo_queue[0] if fifo_queue else [0, None, 0]
			slot_qty = flt(slot[FIFO_QTY_INDEX])
			slot_value = flt(slot[FIFO_VALUE_INDEX])

			if 0 < slot_qty <= qty_to_pop:
				qty_to_pop -= slot_qty
				stock_value -= slot_value
				self.transferred_item_details[transfer_key].append(fifo_queue.pop(0))
			elif not fifo_queue:
				fifo_queue.append([-(qty_to_pop), row.posting_date, -(stock_value)])
				self.transferred_item_details[transfer_key].append(
					[qty_to_pop, row.posting_date, stock_value]
				)
				qty_to_pop = 0
				stock_value = 0
			else:
				slot[FIFO_QTY_INDEX] = slot_qty - qty_to_pop
				slot[FIFO_VALUE_INDEX] = slot_value - stock_value
				self.transferred_item_details[transfer_key].append(
					[qty_to_pop, slot[FIFO_DATE_INDEX], stock_value]
				)
				qty_to_pop = 0
				stock_value = 0

	def _adjust_incoming_transfer_qty(
		self,
		transfer_data: dict,
		fifo_queue: list,
		row: dict,
		batch_nos: list | None = None,
		serial_nos: list | None = None,
	):
		"Add previously removed stock back to FIFO Queue."
		transfer_qty_to_pop = flt(row.actual_qty)
		stock_value = flt(row.stock_value_difference)
		batch_nos = [list(batch_no) for batch_no in batch_nos or []]
		serial_nos = list(serial_nos or [])

		while transfer_qty_to_pop:
			if transfer_data and 0 < flt(transfer_data[0][FIFO_QTY_INDEX]) <= transfer_qty_to_pop:
				# bucket qty is not enough, consume whole
				transfer_qty = flt(transfer_data[0][FIFO_QTY_INDEX])
				transfer_date = transfer_data[0][FIFO_DATE_INDEX]
				transfer_value = flt(transfer_data[0][FIFO_VALUE_INDEX])
				transfer_qty_to_pop -= transfer_qty
				stock_value -= transfer_value
				self._add_incoming_transfer_slots(
					fifo_queue, batch_nos, transfer_qty, transfer_date, transfer_value, serial_nos
				)
				transfer_data.pop(0)
			elif not transfer_data:
				# transfer bucket is empty, extra incoming qty
				self._add_incoming_transfer_slots(
					fifo_queue, batch_nos, transfer_qty_to_pop, row.posting_date, stock_value, serial_nos
				)
				transfer_qty_to_pop = 0
				stock_value = 0
			else:
				# ample bucket qty to consume
				transfer_data[0][FIFO_QTY_INDEX] -= transfer_qty_to_pop
				transfer_data[0][FIFO_VALUE_INDEX] -= stock_value
				self._add_incoming_transfer_slots(
					fifo_queue,
					batch_nos,
					transfer_qty_to_pop,
					transfer_data[0][FIFO_DATE_INDEX],
					stock_value,
					serial_nos,
				)
				transfer_qty_to_pop = 0
				stock_value = 0

	def _add_incoming_transfer_slots(
		self,
		fifo_queue: list,
		batch_nos: list,
		qty: float,
		posting_date: str,
		value: float,
		serial_nos: list | None = None,
	) -> None:
		for slot in self._get_incoming_transfer_slots(batch_nos, qty, posting_date, value, serial_nos):
			self._add_transfer_slot_to_fifo_queue(fifo_queue, slot)

	def _get_incoming_transfer_slots(
		self,
		batch_nos: list,
		qty: float,
		posting_date: str,
		value: float,
		serial_nos: list | None = None,
	) -> list:
		if serial_nos:
			return self._get_serial_incoming_transfer_slots(serial_nos, qty, posting_date, value)

		if not batch_nos:
			return [[qty, posting_date, value]]

		incoming_slots = []
		remaining_qty = flt(qty)
		remaining_value = flt(value)

		while remaining_qty and batch_nos:
			batch_no, use_batchwise_valuation, batch_qty, _ = batch_nos[0]
			batch_qty = flt(batch_qty)
			slot_qty = min(batch_qty, remaining_qty)
			slot_value = (
				remaining_value
				if slot_qty == remaining_qty
				else flt(remaining_value * (slot_qty / remaining_qty))
			)

			incoming_slots.append([batch_no, use_batchwise_valuation, slot_qty, posting_date, slot_value])

			batch_nos[0][2] = flt(batch_qty - slot_qty)
			if not batch_nos[0][2]:
				batch_nos.pop(0)

			remaining_qty = flt(remaining_qty - slot_qty)
			remaining_value = flt(remaining_value - slot_value)

		if remaining_qty:
			incoming_slots.append([remaining_qty, posting_date, remaining_value])

		return incoming_slots

	def _get_serial_incoming_transfer_slots(
		self, serial_nos: list, qty: float, posting_date: str, value: float
	) -> list:
		incoming_slots = []
		remaining_value = flt(value)
		serial_count = min(cint(qty), len(serial_nos))

		for index in range(serial_count):
			serial_no = serial_nos.pop(0)
			serial_value = remaining_value if index == serial_count - 1 else flt(value / serial_count)
			serial_posting_date = self.serial_no_details.setdefault(serial_no, posting_date)

			incoming_slots.append([serial_no, serial_posting_date, serial_value])
			remaining_value = flt(remaining_value - serial_value)

		return incoming_slots

	def _add_transfer_slot_to_fifo_queue(self, fifo_queue: list, slot: list) -> None:
		matching_negative_batch_slot = self._get_matching_negative_batch_slot(fifo_queue, slot)

		if (
			fifo_queue
			and is_qty_slot(fifo_queue[0])
			and is_qty_slot(slot)
			and flt(fifo_queue[0][FIFO_QTY_INDEX]) <= 0
		):
			fifo_queue[0][FIFO_QTY_INDEX] += flt(slot[FIFO_QTY_INDEX])
			fifo_queue[0][FIFO_DATE_INDEX] = slot[FIFO_DATE_INDEX]
			fifo_queue[0][FIFO_VALUE_INDEX] += flt(slot[FIFO_VALUE_INDEX])
		elif matching_negative_batch_slot:
			matching_negative_batch_slot[BATCH_SLOT_QTY_INDEX] += flt(slot[BATCH_SLOT_QTY_INDEX])
			matching_negative_batch_slot[BATCH_SLOT_DATE_INDEX] = slot[BATCH_SLOT_DATE_INDEX]
			matching_negative_batch_slot[BATCH_SLOT_VALUE_INDEX] += flt(slot[BATCH_SLOT_VALUE_INDEX])
			if self._is_empty_batch_slot(matching_negative_batch_slot):
				fifo_queue.remove(matching_negative_batch_slot)
		else:
			fifo_queue.append(slot)

	def _is_empty_batch_slot(self, slot: list) -> bool:
		return (
			not flt(slot[BATCH_SLOT_QTY_INDEX])
			and round_off_if_near_zero(slot[BATCH_SLOT_VALUE_INDEX], 2) == 0
		)

	def _get_matching_negative_batch_slot(self, fifo_queue: list, slot: list) -> list | None:
		if not is_batch_slot(slot):
			return None

		return next(
			(
				existing_slot
				for existing_slot in fifo_queue
				if self._is_matching_negative_batch_slot(
					existing_slot,
					slot[BATCH_SLOT_BATCH_INDEX],
					slot[BATCH_SLOT_VALUATION_INDEX],
					include_zero_qty=True,
				)
			),
			None,
		)

	def _update_balances(self, row: dict, key: tuple | str):
		self.item_details[key]["qty_after_transaction"] = row.qty_after_transaction
		if "total_qty" not in self.item_details[key]:
			self.item_details[key]["total_qty"] = row.actual_qty
		else:
			self.item_details[key]["total_qty"] += row.actual_qty

		self.item_details[key]["has_serial_no"] = row.has_serial_no
		self.item_details[key]["has_batch_no"] = row.has_batch_no
		self.item_details[key]["details"].valuation_rate = row.valuation_rate

	def _aggregate_details_by_item(self, wh_wise_data: dict) -> dict:
		"Aggregate Item-Wh wise data into single Item entry."
		item_aggregated_data = {}
		for key, row in wh_wise_data.items():
			item = key[0]
			if not item_aggregated_data.get(item):
				item_aggregated_data.setdefault(
					item,
					{
						"details": frappe._dict(),
						"fifo_queue": [],
						"qty_after_transaction": 0.0,
						"total_qty": 0.0,
					},
				)
			item_row = item_aggregated_data.get(item)
			item_row["details"].update(row["details"])
			item_row["fifo_queue"].extend(row["fifo_queue"])
			item_row["qty_after_transaction"] += flt(row["qty_after_transaction"])
			item_row["total_qty"] += flt(row["total_qty"])
			item_row["has_serial_no"] = row["has_serial_no"]
			item_row["has_batch_no"] = row["has_batch_no"]

		return item_aggregated_data

	def _get_stock_ledger_entries(self) -> Iterator[dict]:
		sle = frappe.qb.DocType("Stock Ledger Entry")
		item = self._get_item_query()  # used as derived table in sle query
		to_date = get_datetime(self.filters.get("to_date") + " 23:59:59")

		sle_query = (
			frappe.qb.from_(sle)
			.from_(item)
			.select(
				item.name,
				item.item_name,
				item.item_group,
				item.brand,
				item.description,
				item.stock_uom,
				item.has_batch_no,
				item.has_serial_no,
				sle.actual_qty,
				sle.stock_value_difference,
				sle.valuation_rate,
				sle.posting_date,
				sle.voucher_type,
				sle.voucher_no,
				sle.voucher_detail_no,
				sle.serial_no,
				sle.batch_no,
				sle.qty_after_transaction,
				sle.serial_and_batch_bundle,
				sle.warehouse,
			)
			.where(
				(sle.item_code == item.name)
				& (sle.company == self.filters.get("company"))
				& (sle.posting_datetime <= to_date)
				& (sle.is_cancelled != 1)
			)
		)

		if self.filters.get("warehouse"):
			sle_query = self._get_warehouse_conditions(sle, sle_query)
		elif self.filters.get("warehouse_type"):
			warehouses = frappe.get_all(
				"Warehouse",
				filters={"warehouse_type": self.filters.get("warehouse_type"), "is_group": 0},
				pluck="name",
			)

			if warehouses:
				sle_query = sle_query.where(sle.warehouse.isin(warehouses))

		sle_query = sle_query.orderby(sle.posting_datetime, sle.creation)

		return sle_query.run(as_dict=True, as_iterator=True)

	def _get_bundle_wise_serial_nos(self) -> dict:
		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		entry = frappe.qb.DocType("Serial and Batch Entry")

		to_date = get_datetime(self.filters.get("to_date") + " 23:59:59")
		query = (
			frappe.qb.from_(bundle)
			.join(entry)
			.on(bundle.name == entry.parent)
			.select(bundle.name, entry.serial_no)
			.where(
				(bundle.docstatus == 1)
				& (entry.serial_no.isnotnull())
				& (bundle.company == self.filters.get("company"))
				& (bundle.posting_datetime <= to_date)
			)
		)

		for field in ["item_code"]:
			if self.filters.get(field):
				query = query.where(bundle[field] == self.filters.get(field))

		if self.filters.get("warehouse"):
			query = self._get_warehouse_conditions(bundle, query)

		bundle_wise_serial_nos = frappe._dict({})
		for bundle_name, serial_no in query.run():
			bundle_wise_serial_nos.setdefault(bundle_name, []).append(serial_no)

		return bundle_wise_serial_nos

	def _get_bundle_wise_batch_nos(self, sabb_name=None) -> dict:
		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		entry = frappe.qb.DocType("Serial and Batch Entry")
		batch = frappe.qb.DocType("Batch")

		to_date = get_datetime(self.filters.get("to_date") + " 23:59:59")
		query = (
			frappe.qb.from_(bundle)
			.join(entry)
			.on(bundle.name == entry.parent)
			.join(batch)
			.on(entry.batch_no == batch.name)
			.select(
				bundle.name,
				entry.batch_no,
				batch.use_batchwise_valuation,
				Abs(entry.qty).as_("qty"),
				Abs(entry.stock_value_difference).as_("stock_value_difference"),
			)
			.where(
				(bundle.docstatus == 1)
				& (entry.batch_no.isnotnull())
				& (bundle.company == self.filters.get("company"))
				& (bundle.posting_datetime <= to_date)
			)
		)

		for field in ["item_code"]:
			if self.filters.get(field):
				query = query.where(bundle[field] == self.filters.get(field))

		if self.filters.get("warehouse"):
			query = self._get_warehouse_conditions(bundle, query)

		if sabb_name:
			query = query.where(bundle.name == sabb_name)

		bundle_wise_batch_nos = frappe._dict({})
		for bundle_name, batch_no, use_batchwise_valuation, qty, stock_value_difference in query.run():
			bundle_wise_batch_nos.setdefault(bundle_name, []).append(
				[batch_no.upper(), use_batchwise_valuation, qty, stock_value_difference]
			)

		return bundle_wise_batch_nos

	def _get_item_query(self) -> str:
		item_table = frappe.qb.DocType("Item")

		item = frappe.qb.from_("Item").select(
			"name",
			"item_name",
			"description",
			"stock_uom",
			"brand",
			"item_group",
			"has_serial_no",
			"has_batch_no",
		)

		if self.filters.get("item_code"):
			item = item.where(item_table.item_code == self.filters.get("item_code"))

		if self.filters.get("brand"):
			item = item.where(item_table.brand == self.filters.get("brand"))

		return item

	def _get_warehouse_conditions(self, sle, sle_query) -> str:
		warehouse = frappe.qb.DocType("Warehouse")
		lft, rgt = frappe.db.get_value("Warehouse", self.filters.get("warehouse"), ["lft", "rgt"])

		warehouse_results = (
			frappe.qb.from_(warehouse)
			.select("name")
			.where((warehouse.lft >= lft) & (warehouse.rgt <= rgt))
			.run()
		)
		warehouse_results = [x[0] for x in warehouse_results]

		return sle_query.where(sle.warehouse.isin(warehouse_results))

	def prepare_stock_reco_voucher_wise_count(self):
		self.stock_reco_voucher_wise_count = frappe._dict()

		doctype = frappe.qb.DocType("Stock Ledger Entry")
		item = frappe.qb.DocType("Item")

		query = (
			frappe.qb.from_(doctype)
			.inner_join(item)
			.on(doctype.item_code == item.name)
			.select(doctype.voucher_detail_no, Count(doctype.name).as_("count"))
			.where(
				(doctype.voucher_type == "Stock Reconciliation")
				& (doctype.docstatus < 2)
				& (doctype.is_cancelled == 0)
			)
			.groupby(doctype.voucher_detail_no)
		)

		data = query.run(as_dict=True)
		if not data:
			return

		for row in data:
			if row.count != 1:
				continue

			sr_item = frappe.db.get_value(
				"Stock Reconciliation Item", row.voucher_detail_no, ["current_qty", "qty"], as_dict=True
			)
			if sr_item and sr_item.qty and sr_item.current_qty:
				self.stock_reco_voucher_wise_count[row.voucher_detail_no] = sr_item.current_qty
