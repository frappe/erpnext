import json

import frappe
from frappe.utils import flt, parse_json

from erpnext.buying.doctype.buying_settings.buying_settings import (
	is_material_from_in_transit_warehouse,
	is_rejected_material_valued,
)
from erpnext.stock.doctype.serial_and_batch_bundle.services.batch_stock import BundleBatchStock
from erpnext.stock.serial_batch_bundle import BatchNoValuation, SerialNoValuation
from erpnext.stock.valuation import FIFOValuation, LIFOValuation


class BundleValuation:
	def __init__(self, doc):
		self.doc = doc

	def set_incoming_rate_for_inward_transaction(self, row=None, save=False, prev_sle=None):
		from erpnext.stock.utils import get_valuation_method

		valuation_method = get_valuation_method(self.doc.item_code, self.doc.company)

		valuation_field = "valuation_rate"
		if self.doc.voucher_type in ["Sales Invoice", "Delivery Note", "Quotation"]:
			valuation_field = "incoming_rate"

		if self.doc.voucher_type == "POS Invoice":
			valuation_field = "rate"

		rate = row.get(valuation_field) if row else 0.0
		child_table = self.doc.child_table

		if self.doc.voucher_type == "Subcontracting Receipt":
			if not self.doc.voucher_detail_no:
				return
			elif frappe.db.exists("Subcontracting Receipt Supplied Item", self.doc.voucher_detail_no):
				valuation_field = "rate"
				child_table = "Subcontracting Receipt Supplied Item"
			else:
				valuation_field = "rate"
				child_table = "Subcontracting Receipt Item"

		if not rate and self.doc.voucher_detail_no and self.doc.voucher_no:
			rate = frappe.db.get_value(child_table, self.doc.voucher_detail_no, valuation_field)

		is_packed_item = False
		if rate is None and child_table in ["Delivery Note Item", "Sales Invoice Item"]:
			rate = frappe.db.get_value(
				"Packed Item",
				{"parent_detail_docname": self.doc.voucher_detail_no, "item_code": self.doc.item_code},
				"incoming_rate",
			)

			if rate is None:
				rate = frappe.db.get_value("Packed Item", self.doc.voucher_detail_no, "incoming_rate")

			if rate is not None:
				is_packed_item = True

		stock_queue = []
		batches = frappe.get_all(
			"Batch",
			filters={
				"name": ("in", [d.batch_no for d in self.doc.entries if d.batch_no]),
				"use_batchwise_valuation": 0,
			},
			pluck="name",
		)

		if prev_sle and prev_sle.stock_queue and parse_json(prev_sle.stock_queue):
			if batches and valuation_method in ("FIFO", "LIFO"):
				stock_queue = parse_json(prev_sle.stock_queue)

		values_rejected_material = is_rejected_material_valued(
			self.doc.voucher_type, self.doc.voucher_detail_no
		)

		if self.doc.is_rejected and is_material_from_in_transit_warehouse(
			self.doc.voucher_type, self.doc.voucher_detail_no
		):
			# Rejected material of a transfer keeps the value it had in transit. A charge spread
			# over the accepted quantity does not belong to it.
			rate = flt(self.get_transit_rate(row)) or rate

		entry_rates = self.get_transfer_rates() or self.get_subcontracting_return_rates()
		precision = frappe.get_precision("Serial and Batch Entry", "incoming_rate")
		for d in self.doc.entries:
			is_queue_valued = valuation_method in ("FIFO", "LIFO") and d.batch_no in batches

			entry_rate = entry_rates.get((d.serial_no, d.batch_no), rate)

			if self.doc.is_rejected and not values_rejected_material:
				entry_rate = 0.0
			elif (
				(flt(d.incoming_rate, precision) == flt(entry_rate, precision))
				and not stock_queue
				and not is_queue_valued
				and d.qty
				and d.stock_value_difference
			):
				continue

			if is_packed_item and d.incoming_rate:
				entry_rate = d.incoming_rate

			d.incoming_rate = flt(entry_rate)
			if d.qty:
				d.stock_value_difference = flt(d.qty) * d.incoming_rate

			if is_queue_valued and d.incoming_rate is not None:
				stock_queue.append([d.qty, d.incoming_rate])
				d.stock_queue = json.dumps(stock_queue)

			if save:
				d.db_set(
					{
						"incoming_rate": d.incoming_rate,
						"stock_value_difference": d.stock_value_difference,
						"stock_queue": d.get("stock_queue"),
					}
				)

	def set_incoming_rate_for_outward_transaction(self, row=None, save=False, allow_negative_stock=False):
		from erpnext.stock.utils import get_valuation_method, is_serial_no_wise_valuation_disabled

		if is_serial_no_wise_valuation_disabled(self.doc.item_code):
			return

		sle = self.get_sle_for_outward_transaction()

		if self.doc.has_serial_no:
			sn_obj = SerialNoValuation(
				sle=sle,
				item_code=self.doc.item_code,
				warehouse=self.doc.warehouse,
			)

		else:
			sn_obj = BatchNoValuation(
				sle=sle,
				item_code=self.doc.item_code,
				warehouse=self.doc.warehouse,
			)

		stock_queue = []
		if hasattr(sn_obj, "stock_queue") and sn_obj.stock_queue:
			stock_queue = parse_json(sn_obj.stock_queue)

		val_method = get_valuation_method(self.doc.item_code, self.doc.company)

		for d in self.doc.entries:
			available_qty = 0

			if self.doc.has_serial_no:
				d.incoming_rate = abs(sn_obj.serial_no_incoming_rate.get(d.serial_no, 0.0))
			else:
				actual_qty = d.qty
				if (
					stock_queue
					and val_method in ("FIFO", "LIFO")
					and d.batch_no in sn_obj.non_batchwise_valuation_batches
				):
					if actual_qty < 0:
						queue_class = LIFOValuation if val_method == "LIFO" else FIFOValuation
						stock_queue = queue_class(stock_queue)
						_prev_qty, prev_stock_value = stock_queue.get_total_stock_and_value()

						stock_queue.remove_stock(qty=abs(actual_qty))
						_qty, stock_value = stock_queue.get_total_stock_and_value()

						stock_value_difference = stock_value - prev_stock_value
						d.incoming_rate = abs(flt(stock_value_difference) / abs(flt(actual_qty)))
						stock_queue = stock_queue.state
					else:
						d.incoming_rate = abs(flt(sn_obj.batch_avg_rate.get(d.batch_no)))
						stock_queue.append([d.qty, d.incoming_rate])
					d.stock_queue = json.dumps(stock_queue)
				else:
					d.incoming_rate = abs(flt(sn_obj.batch_avg_rate.get(d.batch_no)))

				precision = d.precision("qty")
				available_qty = flt(sn_obj.available_qty.get(d.batch_no), precision)
				if self.doc.docstatus == 1:
					available_qty += flt(d.qty, precision)

				if not allow_negative_stock:
					BundleBatchStock(self.doc).validate_negative_batch(d.batch_no, available_qty)

			d.stock_value_difference = flt(d.qty) * flt(d.incoming_rate)

			if save:
				d.db_set(
					{
						"incoming_rate": d.incoming_rate,
						"stock_value_difference": d.stock_value_difference,
						"stock_queue": d.get("stock_queue"),
					}
				)

	def get_sle_for_outward_transaction(self):
		sle = frappe._dict(
			{
				"posting_datetime": self.doc.posting_datetime,
				"item_code": self.doc.item_code,
				"warehouse": self.doc.warehouse,
				"serial_and_batch_bundle": self.doc.name,
				"company": self.doc.company,
				"serial_nos": [row.serial_no for row in self.doc.entries if row.serial_no],
				"batch_nos": {row.batch_no: row for row in self.doc.entries if row.batch_no},
				"voucher_type": self.doc.voucher_type,
				"voucher_detail_no": self.doc.voucher_detail_no,
				"creation": self.doc.creation,
			}
		)

		if self.doc.docstatus == 1:
			sle["voucher_no"] = self.doc.voucher_no

		if not sle.actual_qty:
			self.doc.calculate_total_qty()
			sle.actual_qty = self.doc.total_qty

		return sle

	def get_transfer_rates(self) -> dict:
		"""Rate of each serial/batch where the same transfer row took it out, plus the row's added cost."""
		from erpnext.stock.utils import is_serial_no_wise_valuation_disabled

		if not self.doc.voucher_detail_no or is_serial_no_wise_valuation_disabled(self.doc.item_code):
			return {}

		outward_bundles = frappe.get_all(
			"Serial and Batch Bundle",
			filters={
				"voucher_type": self.doc.voucher_type,
				"voucher_detail_no": self.doc.voucher_detail_no,
				"item_code": self.doc.item_code,
				"type_of_transaction": "Outward",
				"is_cancelled": 0,
			},
			pluck="name",
		)
		if not outward_bundles:
			return {}

		added_cost_per_unit = self.get_transfer_added_cost_per_unit()
		if added_cost_per_unit is None:
			return {}

		return {
			(d.serial_no, d.batch_no): flt(d.incoming_rate) + added_cost_per_unit
			for d in frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": ("in", outward_bundles)},
				fields=["serial_no", "batch_no", "incoming_rate"],
			)
		}

	def get_transfer_added_cost_per_unit(self) -> float | None:
		"""Cost a transfer row adds to each stock unit it moves, None when the row is no transfer."""
		if self.doc.voucher_type == "Stock Entry":
			additional_cost, transfer_qty = frappe.db.get_value(
				"Stock Entry Detail", self.doc.voucher_detail_no, ["additional_cost", "transfer_qty"]
			)
			return flt(additional_cost) / flt(transfer_qty)

		if self.doc.voucher_type in ("Delivery Note", "Sales Invoice"):
			target_warehouse = frappe.db.get_value(
				self.doc.child_table, self.doc.voucher_detail_no, "target_warehouse"
			)
			return 0.0 if target_warehouse else None

		if self.doc.voucher_type not in ("Purchase Receipt", "Purchase Invoice"):
			return None

		row = frappe.db.get_value(
			self.doc.child_table,
			self.doc.voucher_detail_no,
			["from_warehouse", "landed_cost_voucher_amount", "stock_qty"],
			as_dict=True,
		)
		if not (row and row.from_warehouse):
			return None

		# the landed cost belongs to the accepted stock only
		if self.doc.is_rejected or not flt(row.stock_qty):
			return 0.0

		return flt(row.landed_cost_voucher_amount) / flt(row.stock_qty)

	def get_subcontracting_return_rates(self) -> dict:
		"""Rate the returned Subcontracting Receipt consumed each serial/batch of a supplied item at."""
		from erpnext.stock.utils import get_valuation_method

		if self.doc.voucher_type != "Subcontracting Receipt" or not self.doc.voucher_detail_no:
			return {}

		row = frappe.db.get_value(
			"Subcontracting Receipt Supplied Item",
			self.doc.voucher_detail_no,
			["parent", "reference_name", "rm_item_code"],
			as_dict=True,
		)
		if not row:
			return {}

		receipt = frappe.get_doc("Subcontracting Receipt", row.parent)
		# rejected returns and Standard Cost items keep the row rate
		if (
			not receipt.is_return
			or row.reference_name in receipt.get_rejected_return_rows()
			or get_valuation_method(self.doc.item_code, self.doc.company) == "Standard Cost"
		):
			return {}

		receipt_item = receipt.get("items", {"name": row.reference_name})[0].subcontracting_receipt_item
		consumed = receipt.get_consumed_serial_batches().get((receipt_item, row.rm_item_code), {})
		return {key: identity.rate for key, identity in consumed.items()}

	def get_transit_rate(self, row) -> float:
		"""What one stock unit of the material was worth on its way into the in-transit warehouse."""
		if not (row and row.get("sales_incoming_rate")):
			if not (self.doc.voucher_detail_no and self.doc.voucher_no):
				return 0.0

			row = (
				frappe.db.get_value(
					self.doc.child_table,
					self.doc.voucher_detail_no,
					["sales_incoming_rate", "conversion_factor"],
					as_dict=True,
				)
				or {}
			)

		# sales_incoming_rate is per purchase UOM, but the entries of the bundle hold stock UOM qty
		return flt(row.get("sales_incoming_rate")) / (flt(row.get("conversion_factor")) or 1.0)
