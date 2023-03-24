import frappe
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import flt
from frappe.utils.deprecations import deprecated


class DeprecatedSerialNoValuation:
	@deprecated
	def calculate_stock_value_from_deprecarated_ledgers(self):
		serial_nos = list(
			filter(lambda x: x not in self.serial_no_incoming_rate and x, self.get_serial_nos())
		)

		actual_qty = flt(self.sle.actual_qty)

		stock_value_change = 0
		if actual_qty < 0:
			# In case of delivery/stock issue, get average purchase rate
			# of serial nos of current entry
			if not self.sle.is_cancelled:
				outgoing_value = self.get_incoming_value_for_serial_nos(serial_nos)
				stock_value_change = -1 * outgoing_value
			else:
				stock_value_change = actual_qty * self.sle.outgoing_rate

		self.stock_value_change += stock_value_change

	@deprecated
	def get_incoming_value_for_serial_nos(self, serial_nos):
		# get rate from serial nos within same company
		all_serial_nos = frappe.get_all(
			"Serial No", fields=["purchase_rate", "name", "company"], filters={"name": ("in", serial_nos)}
		)

		incoming_values = 0.0
		for d in all_serial_nos:
			if d.company == self.sle.company:
				self.serial_no_incoming_rate[d.name] = flt(d.purchase_rate)
				incoming_values += flt(d.purchase_rate)

		# Get rate for serial nos which has been transferred to other company
		invalid_serial_nos = [d.name for d in all_serial_nos if d.company != self.sle.company]
		for serial_no in invalid_serial_nos:
			incoming_rate = frappe.db.sql(
				"""
				select incoming_rate
				from `tabStock Ledger Entry`
				where
					company = %s
					and actual_qty > 0
					and is_cancelled = 0
					and (serial_no = %s
						or serial_no like %s
						or serial_no like %s
						or serial_no like %s
					)
				order by posting_date desc
				limit 1
			""",
				(self.sle.company, serial_no, serial_no + "\n%", "%\n" + serial_no, "%\n" + serial_no + "\n%"),
			)

			self.serial_no_incoming_rate[serial_no] = flt(incoming_rate[0][0]) if incoming_rate else 0
			incoming_values += self.serial_no_incoming_rate[serial_no]

		return incoming_values


class DeprecatedBatchNoValuation:
	@deprecated
	def calculate_avg_rate_from_deprecarated_ledgers(self):
		entries = self.get_sle_for_batches()
		for ledger in entries:
			self.batch_avg_rate[ledger.batch_no] += flt(ledger.batch_value) / flt(ledger.batch_qty)
			self.available_qty[ledger.batch_no] += flt(ledger.batch_qty)

	@deprecated
	def get_sle_for_batches(self):
		batch_nos = list(self.batch_nos.keys())
		sle = frappe.qb.DocType("Stock Ledger Entry")

		timestamp_condition = CombineDatetime(sle.posting_date, sle.posting_time) < CombineDatetime(
			self.sle.posting_date, self.sle.posting_time
		)
		if self.sle.creation:
			timestamp_condition |= (
				CombineDatetime(sle.posting_date, sle.posting_time)
				== CombineDatetime(self.sle.posting_date, self.sle.posting_time)
			) & (sle.creation < self.sle.creation)

		return (
			frappe.qb.from_(sle)
			.select(
				sle.batch_no,
				Sum(sle.stock_value_difference).as_("batch_value"),
				Sum(sle.actual_qty).as_("batch_qty"),
			)
			.where(
				(sle.item_code == self.sle.item_code)
				& (sle.name != self.sle.name)
				& (sle.warehouse == self.sle.warehouse)
				& (sle.batch_no.isin(batch_nos))
				& (sle.is_cancelled == 0)
			)
			.where(timestamp_condition)
			.groupby(sle.batch_no)
		).run(as_dict=True)
