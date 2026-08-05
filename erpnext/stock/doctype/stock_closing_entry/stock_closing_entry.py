# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import gzip
import json

import frappe
from frappe import _
from frappe.desk.form.load import get_attachments
from frappe.model.document import Document
from frappe.query_builder import Case, Order
from frappe.utils import add_days, flt, get_date_str, get_link_to_form, parse_json
from frappe.utils.background_jobs import enqueue
from frappe.utils.caching import request_cache

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions

SCOPE_FIELDS = ("warehouse", "item_code", "item_group", "warehouse_type")


def apply_unscoped_filters(filters):
	meta = frappe.get_meta("Stock Closing Entry")
	for fieldname in SCOPE_FIELDS:
		if meta.has_field(fieldname):
			filters[fieldname] = ("is", "not set")

	return filters


def get_closing_entry_for_closed_period(company):
	closed_upto = frappe.db.get_value(
		"Period Closing Voucher", {"docstatus": 1, "company": company}, [{"MAX": "period_end_date"}]
	)
	if not closed_upto:
		return None

	return _get_completed_closing_entry(company, str(closed_upto))


@request_cache
def _get_completed_closing_entry(company, closed_upto):
	filters = apply_unscoped_filters(
		{
			"company": company,
			"docstatus": 1,
			"status": "Completed",
			"to_date": ("<=", closed_upto),
		}
	)

	return frappe.db.get_value(
		"Stock Closing Entry",
		filters,
		["name", "to_date"],
		order_by="to_date desc",
		as_dict=True,
	)


class StockClosingEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link | None
		from_date: DF.Date | None
		naming_series: DF.Literal["CBAL-.#####"]
		status: DF.Literal["Draft", "Queued", "In Progress", "Completed", "Failed", "Cancelled"]
		to_date: DF.Date | None
	# end: auto-generated types

	def on_discard(self):
		self.db_set("status", "Cancelled")

	def before_save(self):
		self.set_status()

	def set_status(self, save=False):
		self.status = "Queued"
		if self.docstatus == 2:
			self.status = "Cancelled"

		if self.docstatus == 0:
			self.status = "Draft"

		if save:
			self.db_set("status", self.status)

	def validate(self):
		self.validate_duplicate()

	def validate_duplicate(self):
		table = frappe.qb.DocType("Stock Closing Entry")

		query = (
			frappe.qb.from_(table)
			.select(table.name)
			.where(
				(table.docstatus == 1)
				& (table.company == self.company)
				# two date ranges overlap when each starts on or before the other ends;
				# this also catches one range being fully contained within the other
				& (table.from_date <= self.to_date)
				& (table.to_date >= self.from_date)
			)
		)

		for fieldname in SCOPE_FIELDS:
			if self.get(fieldname):
				query = query.where(table[fieldname] == self.get(fieldname))

		query = query.run(as_dict=True)

		if query and query[0].name:
			name = get_link_to_form("Stock Closing Entry", query[0].name)
			frappe.throw(
				_("Stock Closing Entry {0} already exists for the selected date range").format(name),
				title=_("Duplicate Stock Closing Entry"),
			)

	def on_submit(self):
		self.set_status(save=True)
		self.enqueue_job()

	def on_cancel(self):
		self.validate_closed_period_lock()
		self.set_status(save=True)
		self.remove_stock_closing()

	def validate_closed_period_lock(self):
		pcv = frappe.db.get_value(
			"Period Closing Voucher",
			{"company": self.company, "docstatus": 1, "period_end_date": (">=", self.to_date)},
			"name",
		)

		if pcv:
			frappe.throw(
				_(
					"Stock Closing Entry {0} belongs to a closed accounting period. Cancel the Period Closing Voucher {1} first."
				).format(self.name, get_link_to_form("Period Closing Voucher", pcv)),
				title=_("Closed Period"),
			)

	def remove_stock_closing(self):
		table = frappe.qb.DocType("Stock Closing Balance")
		frappe.qb.from_(table).delete().where(table.stock_closing_entry == self.name).run()
		reset_stock_closing_cache()

	@frappe.whitelist(methods=["POST"])
	def enqueue_job(self):
		self.db_set("status", "In Progress")
		enqueue(prepare_closing_stock_balance, name=self.name, queue="long", timeout=1500)
		frappe.msgprint(
			_(
				"Stock Closing Entry {0} has been queued for processing, the system will take some time to complete it."
			).format(self.name)
		)

	@frappe.whitelist(methods=["POST"])
	def regenerate_closing_balance(self):
		self.validate_closed_period_lock()
		self.remove_stock_closing()
		self.enqueue_job()

	def create_stock_closing_balance_entries(self):
		from erpnext.stock.utils import get_combine_datetime

		stk_cl_obj = StockClosing(self.company, self.from_date, self.to_date)

		entries = stk_cl_obj.get_stock_closing_entries()
		for key in entries:
			row = entries[key]

			if row.actual_qty == 0.0 and row.stock_value_difference == 0.0:
				continue

			if row.fifo_queue is not None:
				row.fifo_queue = json.dumps(row.fifo_queue)

			new_doc = frappe.new_doc("Stock Closing Balance")
			new_doc.update(row)
			new_doc.posting_date = self.to_date
			# The snapshot absorbs every entry dated on or before to_date, so its floor must sit at
			# the very end of that day - a mid-day timestamp would let same-day entries be counted
			# both inside the snapshot and again by live readers.
			new_doc.posting_time = "23:59:59.999999"
			new_doc.posting_datetime = get_combine_datetime(self.to_date, new_doc.posting_time)
			new_doc.stock_closing_entry = self.name
			new_doc.company = self.company
			new_doc.save()

	def get_prepared_data(self):
		if attachments := get_attachments(self.doctype, self.name):
			attachment = attachments[0]
			attached_file = frappe.get_doc("File", attachment.name)

			data = gzip.decompress(attached_file.get_content())
			data = json.loads(data.decode("utf-8"))

			return parse_json(data)

		return frappe._dict({})


def prepare_closing_stock_balance(name):
	doc = frappe.get_doc("Stock Closing Entry", name)
	doc.db_set("status", "In Progress")

	try:
		doc.create_stock_closing_balance_entries()
		doc.db_set("status", "Completed")
		reset_stock_closing_cache()
	except Exception:
		frappe.db.rollback()
		doc.db_set("status", "Failed")
		doc.log_error(title="Stock Closing Entry Failed")


def reset_stock_closing_cache():
	for attr in ("has_completed_stock_closing", "last_completed_stock_closing"):
		if hasattr(frappe.local, attr):
			delattr(frappe.local, attr)


def has_completed_stock_closing() -> bool:
	if not hasattr(frappe.local, "has_completed_stock_closing"):
		frappe.local.has_completed_stock_closing = bool(
			frappe.db.exists("Stock Closing Entry", {"docstatus": 1, "status": "Completed"})
		)

	return frappe.local.has_completed_stock_closing


def get_closing_balance_for_batch(item_code, warehouse, batch_no):
	"""Latest completed snapshot row for one (item, warehouse, batch) key. Ledger rows dated at
	or before its posting_datetime are absorbed into the snapshot and must not be counted again."""
	if not (batch_no and has_completed_stock_closing()):
		return None

	balance = frappe.qb.DocType("Stock Closing Balance")
	entry = frappe.qb.DocType("Stock Closing Entry")

	rows = (
		frappe.qb.from_(balance)
		.inner_join(entry)
		.on(balance.stock_closing_entry == entry.name)
		.select(
			balance.actual_qty,
			# StockClosing accumulates value into stock_value_difference; summed over the whole
			# window it IS the closing stock value (stock_value itself is never populated).
			balance.stock_value_difference.as_("stock_value"),
			balance.posting_datetime,
		)
		.where(
			(entry.docstatus == 1)
			& (entry.status == "Completed")
			& (balance.item_code == item_code)
			& (balance.warehouse == warehouse)
			& (balance.batch_no == batch_no)
		)
		.orderby(balance.posting_datetime, order=Order.desc)
		.limit(1)
	).run(as_dict=True)

	return _clamp_negative_stock_value(rows[0]) if rows else None


def _clamp_negative_stock_value(row):
	"""Legacy data can carry outgoing rates above the incoming rate (e.g. a serial received at
	1000 but consumed at 2000), leaving the snapshot value negative while qty is not - such a
	value is a data anomaly and would poison every seeded valuation, so floor it at zero. A
	negative value alongside negative qty is legitimate negative stock and is kept."""
	if flt(row.stock_value) < 0 and flt(row.actual_qty) >= 0:
		row.stock_value = 0.0

	return row


def get_closing_balances_for_batches(kwargs) -> dict:
	"""Snapshot rows keyed by (batch_no, warehouse) matching an availability query's filters,
	keeping only the latest snapshot per key."""
	if not has_completed_stock_closing():
		return {}

	balance = frappe.qb.DocType("Stock Closing Balance")
	entry = frappe.qb.DocType("Stock Closing Entry")

	query = (
		frappe.qb.from_(balance)
		.inner_join(entry)
		.on(balance.stock_closing_entry == entry.name)
		.select(
			balance.batch_no,
			balance.warehouse,
			balance.actual_qty,
			balance.stock_value_difference.as_("stock_value"),
			balance.posting_datetime,
		)
		.where(
			(entry.docstatus == 1)
			& (entry.status == "Completed")
			& (balance.batch_no.isnotnull())
			& (balance.batch_no != "")
		)
		.orderby(balance.posting_datetime, order=Order.desc)
	)

	for field in ("item_code", "warehouse", "batch_no", "company"):
		value = kwargs.get(field)
		if not value:
			continue

		if isinstance(value, list):
			query = query.where(balance[field].isin(value))
		else:
			query = query.where(balance[field] == value)

	closing_rows = {}
	for row in query.run(as_dict=True):
		closing_rows.setdefault((row.batch_no, row.warehouse), _clamp_negative_stock_value(row))

	return closing_rows


def get_last_completed_closing(company):
	if not has_completed_stock_closing():
		return None

	cache = getattr(frappe.local, "last_completed_stock_closing", None)
	if cache is None:
		cache = frappe.local.last_completed_stock_closing = {}

	if company not in cache:
		entries = frappe.get_all(
			"Stock Closing Entry",
			fields=["name", "to_date"],
			filters={"company": company, "docstatus": 1, "status": "Completed"},
			order_by="to_date desc",
			limit=1,
		)
		cache[company] = entries[0] if entries else None

	return cache[company]


class StockClosing:
	def __init__(self, company, from_date, to_date, **kwargs):
		self.company = company
		self.from_date = from_date
		self.to_date = to_date
		self.kwargs = kwargs
		self.inv_dimensions = get_inventory_dimensions()
		self.last_closing_balance = self.get_last_stock_closing_entry()

	def get_stock_closing_entries(self):
		sl_entries = self.get_sle_entries()

		closing_stock = frappe._dict()
		for row in sl_entries:
			dimensions_keys = self.get_keys(row)
			for dimension_key in dimensions_keys:
				for dimension_fields, dimension_values in dimension_key.items():
					key = dimension_values

					if key in closing_stock:
						actual_qty = row.sabb_qty or row.actual_qty
						closing_stock[key].actual_qty += actual_qty
						closing_stock[key].stock_value_difference += (
							row.sabb_stock_value_difference or row.stock_value_difference
						)

						if not row.actual_qty and row.qty_after_transaction:
							closing_stock[key].actual_qty = row.qty_after_transaction

						fifo_queue = closing_stock[key].fifo_queue
						if fifo_queue:
							self.update_fifo_queue(fifo_queue, actual_qty, row.posting_date)
							closing_stock[key].fifo_queue = fifo_queue
					else:
						entries = self.get_initialized_entry(row, dimension_fields)
						closing_stock[key] = entries

		return closing_stock

	def update_fifo_queue(self, fifo_queue, actual_qty, posting_date):
		if actual_qty > 0:
			fifo_queue.append([actual_qty, get_date_str(posting_date)])
		else:
			remaining_qty = actual_qty
			for idx, queue in enumerate(fifo_queue):
				if queue[0] + remaining_qty >= 0:
					queue[0] += remaining_qty
					if queue[0] == 0:
						fifo_queue.pop(idx)
					break
				else:
					remaining_qty += queue[0]
					fifo_queue.pop(0)

	def get_initialized_entry(self, row, dimension_fields):
		item_details = frappe.get_cached_value(
			"Item", row.item_code, ["item_group", "item_name", "stock_uom", "has_serial_no"], as_dict=1
		)

		inventory_dimension_key = None
		if dimension_fields not in [("item_code", "warehouse"), ("item_code", "warehouse", "batch_no")]:
			inventory_dimension_key = json.dumps(dimension_fields)

		actual_qty = row.sabb_qty or row.actual_qty or row.qty_after_transaction

		entry = frappe._dict(
			{
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"actual_qty": actual_qty,
				"stock_value_difference": row.sabb_stock_value_difference or row.stock_value_difference,
				"item_group": item_details.item_group,
				"item_name": item_details.item_name,
				"stock_uom": item_details.stock_uom,
				"inventory_dimension_key": inventory_dimension_key,
				"fifo_queue": [[actual_qty, get_date_str(row.posting_date)]]
				if not item_details.has_serial_no
				else [],
			}
		)

		if row.sabb_batch_no:
			row.batch_no = row.sabb_batch_no

		# To update dimensions
		for field in dimension_fields:
			if row.get(field):
				entry[field] = row.get(field)

		return entry

	def get_sle_entries(self):
		sl_entries = []
		if self.last_closing_balance:
			self.from_date = add_days(self.last_closing_balance.to_date, 1)
			sl_entries += self.get_entries(
				"Stock Closing Balance",
				fields=[
					"item_code",
					"warehouse",
					"posting_date",
					"posting_time",
					"posting_datetime",
					"batch_no",
					"actual_qty",
					"valuation_rate",
					"stock_value",
					"stock_value_difference",
				],
				filters={
					"company": self.company,
					"stock_closing_entry": self.last_closing_balance.name,
				},
			)

		if not self.last_closing_balance:
			self.from_date = "1900-01-01"

		sl_entries += self.get_entries(
			"Stock Ledger Entry",
			fields=[
				"item_code",
				"warehouse",
				"posting_date",
				"posting_time",
				"posting_datetime",
				"batch_no",
				"actual_qty",
				"valuation_rate",
				"stock_value",
				"stock_value_difference",
				"qty_after_transaction",
				"stock_uom",
			],
			filters={
				"company": self.company,
				"posting_date": [self.from_date, self.to_date],
				"is_cancelled": 0,
				"docstatus": 1,
			},
		)

		return sl_entries

	def get_entries(self, doctype, fields, filters, **kwargs):
		"""Get Stock Ledger Entries for the given filters."""

		for dimension in self.inv_dimensions:
			if dimension.fieldname not in fields:
				fields.append(dimension.fieldname)

		table = frappe.qb.DocType(doctype)
		query = frappe.qb.from_(table).select(*fields).orderby(table.posting_datetime)

		if filters:
			for field, value in filters.items():
				if field == "posting_date":
					query = query.where(table[field].between(value[0], value[1]))
				elif isinstance(value, list) or isinstance(value, tuple):
					query = query.where(table[field].isin(value))
				else:
					query = query.where(table[field] == value)

		for key, value in kwargs.items():
			if value:
				if isinstance(value, list) or isinstance(value, tuple):
					query = query.where(table[key].isin(value))
				else:
					query = query.where(table[key] == value)

		if doctype == "Stock Ledger Entry":
			# A single SLE can aggregate several batches moved in one transaction (its own
			# batch_no field only holds one); join Stock Location Ledger to split it back out
			# per batch. Match is_outward to the SLE's own direction so a Stock Reconciliation's
			# reversal leg and new-state leg (same voucher tuple, opposite directions) don't both
			# fan out against this one SLE row.
			sll_table = frappe.qb.DocType("Stock Location Ledger")
			query = query.left_join(sll_table).on(
				(sll_table.voucher_type == table.voucher_type)
				& (sll_table.voucher_no == table.voucher_no)
				& (sll_table.voucher_detail_no == table.voucher_detail_no)
				& (sll_table.item_code == table.item_code)
				& (sll_table.warehouse == table.warehouse)
				& (sll_table.docstatus == 1)
				& (sll_table.is_outward == Case().when(table.actual_qty < 0, 1).else_(0))
				& (table.has_batch_no == 1)
			)
			query = query.select(sll_table.batch_no.as_("sabb_batch_no"))
			query = query.select(sll_table.qty.as_("sabb_qty"))
			query = query.select(sll_table.stock_value_difference.as_("sabb_stock_value_difference"))

		return query.run(as_dict=True)

	def get_last_stock_closing_entry(self):
		entries = frappe.get_all(
			"Stock Closing Entry",
			fields=["name", "to_date"],
			filters={"company": self.company, "to_date": ["<", self.from_date], "docstatus": 1},
			order_by="to_date desc, creation desc",
			limit=1,
		)

		return entries[0] if entries else frappe._dict()

	def get_keys(self, row):
		keys = []

		keys.append({("item_code", "warehouse"): (row.item_code, row.warehouse)})

		if row.batch_no:
			keys.append(
				{("item_code", "warehouse", "batch_no"): (row.item_code, row.warehouse, row.batch_no)}
			)

		if row.sabb_batch_no:
			keys.append(
				{("item_code", "warehouse", "batch_no"): (row.item_code, row.warehouse, row.sabb_batch_no)}
			)

		dimension_fields = []
		dimension_values = []
		for dimension in self.inv_dimensions:
			if row.get(dimension.fieldname):
				keys.append(
					{
						("item_code", "warehouse", dimension.fieldname): (
							row.item_code,
							row.warehouse,
							row.get(dimension.fieldname),
						)
					}
				)

				dimension_fields.append(dimension.fieldname)
				dimension_values.append(row.get(dimension.fieldname))

		if dimension_fields and len(dimension_fields) > 1:
			keys.append(
				{
					("item_code", "warehouse", *dimension_fields): (
						row.item_code,
						row.warehouse,
						*dimension_values,
					)
				}
			)

		return keys

	def get_stock_closing_balance(self, kwargs, for_batch=False):
		if not self.last_closing_balance:
			return []

		stock_closing_entry = self.last_closing_balance.name
		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		table = frappe.qb.DocType("Stock Closing Balance")
		query = frappe.qb.from_(table).select("*").where(table.stock_closing_entry == stock_closing_entry)

		for key, value in kwargs.items():
			if key == "inventory_dimension_key":
				if isinstance(value, tuple) and value[0] == "is" and value[1] == "not set":
					query = query.where(
						table.inventory_dimension_key.isnull() | (table.inventory_dimension_key == "")
					)
			elif isinstance(value, list) or isinstance(value, tuple):
				query = query.where(table[key].isin(value))
			else:
				query = query.where(table[key] == value)

		if for_batch:
			query = query.where(table.batch_no.isnotnull())
			query = query.where(
				table.inventory_dimension_key.isnull() | (table.inventory_dimension_key == "")
			)

		return query.run(as_dict=True)
