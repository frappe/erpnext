from collections import Counter

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce
from frappe.utils import flt

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.report.stock_balance.stock_balance import (
	StockBalanceFilter,
	StockBalanceReport,
	filter_items_with_no_transactions,
)


def execute(filters: StockBalanceFilter | None = None):
	return SerialAndBatchWiseStockBalanceReport(filters).run()


class SerialAndBatchWiseStockBalanceReport(StockBalanceReport):
	"""Stock Balance with a row per batch under each item row, and the serial nos in stock."""

	def get_entries_from_stock_closing_balance(self) -> list:
		return []

	def prepare_new_data(self):
		self.prepare_serial_batch_map()
		super().prepare_new_data()
		self.data = [row for item_row in self.data for row in self.get_item_and_batch_rows(item_row)]

	def prepare_serial_batch_map(self):
		self.batch_map = {}
		self.serial_map = {}

		query = self.get_serial_batch_query()
		with frappe.db.unbuffered_cursor():
			for entry in query.run(as_dict=True, as_iterator=True):
				group_by_key = self.get_group_by_key(entry)
				if entry.batch_no:
					self.add_batch_entry(group_by_key, entry)

				if entry.serial_no:
					self.add_serial_nos(group_by_key, entry)

		for batches in self.batch_map.values():
			filter_items_with_no_transactions(batches, self.float_precision, self.inventory_dimensions)

	def get_serial_batch_query(self):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		item_table = frappe.qb.DocType("Item")
		bundle_entry = frappe.qb.DocType("Serial and Batch Entry")

		query = (
			frappe.qb.from_(sle)
			.inner_join(item_table)
			.on(sle.item_code == item_table.name)
			.left_join(bundle_entry)
			.on(bundle_entry.parent == sle.serial_and_batch_bundle)
			.select(
				sle.item_code,
				sle.warehouse,
				sle.posting_date,
				sle.company,
				sle.voucher_type,
				sle.voucher_no,
				Coalesce(bundle_entry.batch_no, sle.batch_no).as_("batch_no"),
				Coalesce(bundle_entry.serial_no, sle.serial_no).as_("serial_no"),
				Coalesce(bundle_entry.qty, sle.actual_qty).as_("actual_qty"),
				Coalesce(bundle_entry.stock_value_difference, sle.stock_value_difference).as_(
					"stock_value_difference"
				),
				item_table.item_group,
				item_table.stock_uom,
				item_table.item_name,
			)
			.where(
				(sle.docstatus < 2)
				& (sle.is_cancelled == 0)
				& ((item_table.has_batch_no == 1) | (item_table.has_serial_no == 1))
			)
		)

		return self.apply_filters(query, sle, item_table)

	def add_batch_entry(self, group_by_key, entry):
		batches = self.batch_map.setdefault(group_by_key, {})
		if entry.batch_no not in batches:
			batches[entry.batch_no] = self.get_initial_data(entry)

		self.add_to_balance(
			batches[entry.batch_no], entry, flt(entry.actual_qty), flt(entry.stock_value_difference)
		)

	def add_serial_nos(self, group_by_key, entry):
		serial_nos = self.serial_map.setdefault((group_by_key, entry.batch_no or None), Counter())
		for serial_no in get_serial_nos(entry.serial_no):
			serial_nos[serial_no] += 1 if flt(entry.actual_qty) > 0 else -1

	def get_item_and_batch_rows(self, item_row) -> list:
		key = self.get_group_by_key(item_row)
		item_row.indent = 0
		item_row.serial_no = self.get_serial_nos_in_stock(key, None)

		return [item_row, *self.get_batch_rows(key)]

	def get_batch_rows(self, key) -> list:
		rows = []
		for batch_no, batch_data in sorted(self.batch_map.get(key, {}).items()):
			if self.is_hidden_zero_stock(batch_data):
				continue

			batch_data.update(
				{
					"indent": 1,
					"batch_no": batch_no,
					"serial_no": self.get_serial_nos_in_stock(key, batch_no),
					"val_rate": flt(batch_data.bal_val / batch_data.bal_qty) if batch_data.bal_qty else 0.0,
				}
			)
			rows.append(batch_data)

		return rows

	def get_serial_nos_in_stock(self, key, batch_no) -> str:
		serial_nos = self.serial_map.get((key, batch_no), {})
		return "\n".join(sorted(serial_no for serial_no, qty in serial_nos.items() if qty > 0))

	def get_columns(self):
		columns = super().get_columns()
		position = next(i for i, column in enumerate(columns) if column["fieldname"] == "val_rate") + 1
		columns[position:position] = [
			{
				"label": _("Batch No"),
				"fieldname": "batch_no",
				"fieldtype": "Link",
				"options": "Batch",
				"width": 120,
			},
			{"label": _("Serial No"), "fieldname": "serial_no", "width": 150},
		]

		return columns
