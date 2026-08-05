import frappe
from frappe.utils import flt
from pypika import Order

from erpnext.deprecation_dumpster import deprecated


class DeprecatedSerialNoValuation:
	"""Valuation fallback for legacy serial nos whose inward history predates the Stock
	Location Ledger and exists only as denormalised serial_no text on Stock Ledger Entry."""

	@deprecated(
		"erpnext.stock.serial_batch_bundle.SerialNoValuation.calculate_stock_value_from_deprecarated_ledgers",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def calculate_stock_value_from_deprecarated_ledgers(self):
		serial_nos = []
		if hasattr(self, "old_serial_nos"):
			serial_nos = self.old_serial_nos

		if not serial_nos:
			return

		stock_value_change = 0
		if not self.sle.is_cancelled:
			stock_value_change = self.get_incoming_value_for_serial_nos(serial_nos)

		self.stock_value_change += flt(stock_value_change)

	@deprecated(
		"erpnext.stock.serial_batch_bundle.SerialNoValuation.get_incoming_value_for_serial_nos",
		"unknown",
		"v16",
		"No known instructions.",
	)
	def get_incoming_value_for_serial_nos(self, serial_nos):
		from erpnext.stock.utils import get_combine_datetime

		# get rate from serial nos within same company
		incoming_values = 0.0
		posting_datetime = self.sle.posting_datetime

		if not posting_datetime and self.sle.posting_date:
			posting_datetime = get_combine_datetime(self.sle.posting_date, self.sle.posting_time)

		do_not_fetch_rate = frappe.db.get_single_value(
			"Stock Reposting Settings", "do_not_fetch_incoming_rate_from_serial_no"
		)

		for serial_no in serial_nos:
			sn_details = frappe.db.get_value("Serial No", serial_no, ["purchase_rate", "company"], as_dict=1)
			if (
				sn_details
				and sn_details.purchase_rate
				and sn_details.company == self.sle.company
				and (not frappe.flags.through_repost_item_valuation or not do_not_fetch_rate)
			):
				self.serial_no_incoming_rate[serial_no] += flt(sn_details.purchase_rate)
				incoming_values += self.serial_no_incoming_rate[serial_no]
				continue

			table = frappe.qb.DocType("Stock Ledger Entry")
			stock_ledgers = (
				frappe.qb.from_(table)
				.select(table.incoming_rate, table.actual_qty, table.stock_value_difference)
				.where(
					(
						(table.serial_no == serial_no)
						| (table.serial_no.like(serial_no + "\n%"))
						| (table.serial_no.like("%\n" + serial_no))
						| (table.serial_no.like("%\n" + serial_no + "\n%"))
					)
					& (table.item_code == self.sle.item_code)
					& (table.company == self.sle.company)
					& (table.warehouse == self.sle.warehouse)
					& (table.actual_qty > 0)
					& (table.is_cancelled == 0)
					& table.posting_datetime
					<= posting_datetime
				)
				.orderby(table.posting_datetime, order=Order.desc)
				.limit(1)
			).run(as_dict=1)

			for sle in stock_ledgers:
				self.serial_no_incoming_rate[serial_no] += flt(sle.incoming_rate)
				incoming_values += self.serial_no_incoming_rate[serial_no]

		return incoming_values
