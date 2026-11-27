import json
from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.query_builder.functions import Abs, Coalesce, Sum
from frappe.utils import cint, escape_html, flt, parse_json

from erpnext.stock.doctype.serial_and_batch_bundle.services.valuation import BundleValuation
from erpnext.stock.serial_batch_bundle import BatchNoValuation, get_batches_from_bundle
from erpnext.stock.serial_batch_bundle import get_serial_nos as get_serial_nos_from_bundle
from erpnext.stock.serial_batch_bundle.bundle_entries import parse_serial_nos
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.stock.valuation import FIFOValuation, LIFOValuation


class BundleReturn(BundleValuation):
	def get_return_against(self, parent=None):
		return_against = None

		if parent and parent.get("is_return") and parent.get("return_against"):
			return parent.get("return_against")

		if (
			self.doc.voucher_type
			in [
				"Delivery Note",
				"Sales Invoice",
				"Purchase Invoice",
				"Purchase Receipt",
				"POS Invoice",
				"Subcontracting Receipt",
			]
			and self.doc.voucher_type
			and self.doc.voucher_no
		):
			voucher_details = frappe.db.get_value(
				self.doc.voucher_type, self.doc.voucher_no, ["is_return", "return_against"], as_dict=True
			)
			if voucher_details and voucher_details.get("is_return") and voucher_details.get("return_against"):
				return voucher_details.get("return_against")

		return return_against

	def set_valuation_rate_for_return_entry(self, return_against, row, save=False, prev_sle=None):
		if valuation_details := self.get_valuation_rate_for_return_entry(return_against):
			from erpnext.stock.utils import get_valuation_method, is_serial_no_wise_valuation_disabled

			skip_rate_update = is_serial_no_wise_valuation_disabled(self.doc.item_code)
			valuation_method = get_valuation_method(self.doc.item_code, self.doc.company)

			# An outward return must go out at the batch's current average rate for a
			# batchwise valuation batch. The original receipt rate is only correct while
			# the batch still holds stock at that rate; once other receipts have changed
			# the average, removing at the original rate strands a residue in the batch
			# value (negative when returning the costlier receipt).
			batchwise_avg_rates = self.get_batchwise_return_avg_rates()

			stock_queue = []
			non_batchwise_batches = []
			if not self.doc.has_serial_no and valuation_method in ("FIFO", "LIFO"):
				non_batchwise_batches = frappe.get_all(
					"Batch",
					filters={
						"name": ("in", [d.batch_no for d in self.doc.entries if d.batch_no]),
						"use_batchwise_valuation": 0,
					},
					pluck="name",
				)

				if non_batchwise_batches and prev_sle and prev_sle.stock_queue:
					stock_queue = parse_json(prev_sle.stock_queue)

			for row in self.doc.entries:
				if valuation_details:
					self.validate_returned_serial_batch_no(return_against, row, valuation_details)

				if skip_rate_update:
					continue

				if row.serial_no:
					valuation_rate = valuation_details["serial_nos"].get(row.serial_no)
				else:
					valuation_rate = valuation_details["batches"].get(row.batch_no)

				if frappe.flags.through_repost_item_valuation and valuation_rate is None:
					# if different serial nos / batches are returned
					if row.serial_no:
						serial_nos = sorted(list(valuation_details["serial_nos"].keys()))
						valuation_rate = valuation_details["serial_nos"].get(serial_nos[cint(row.idx) - 1])
					else:
						batches = sorted(list(valuation_details["batches"].keys()))
						valuation_rate = valuation_details["batches"].get(batches[cint(row.idx) - 1])

				# a batch with an available balance goes out at its current average rate (a
				# valid 0.0 included); the original receipt rate applies only when there is
				# no balance to average
				if not row.serial_no and row.batch_no in batchwise_avg_rates:
					valuation_rate = batchwise_avg_rates[row.batch_no]

				row.incoming_rate = flt(valuation_rate)
				row.stock_value_difference = flt(row.qty) * flt(row.incoming_rate)

				if (
					non_batchwise_batches
					and row.batch_no in non_batchwise_batches
					and row.incoming_rate is not None
				):
					if flt(row.qty) > 0:
						stock_queue.append([row.qty, row.incoming_rate])
					elif flt(row.qty) < 0:
						queue_class = LIFOValuation if valuation_method == "LIFO" else FIFOValuation
						stock_queue = queue_class(stock_queue)
						stock_queue.remove_stock(
							qty=abs(row.qty), outgoing_rate=row.incoming_rate, is_return_purchase_entry=True
						)
						stock_queue = stock_queue.state
					row.stock_queue = json.dumps(stock_queue)

				if save:
					row.db_set(
						{
							"incoming_rate": row.incoming_rate,
							"stock_value_difference": row.stock_value_difference,
							"stock_queue": row.get("stock_queue"),
						}
					)

		elif self.doc.type_of_transaction == "Inward":
			self.set_incoming_rate_for_inward_transaction(row, save, prev_sle=prev_sle)

	def get_batchwise_return_avg_rates(self):
		from erpnext.stock.utils import get_valuation_method

		if self.doc.type_of_transaction != "Outward" or self.doc.has_serial_no:
			return {}

		batch_nos = [d.batch_no for d in self.doc.entries if d.batch_no]
		if not batch_nos:
			return {}

		if get_valuation_method(
			self.doc.item_code, self.doc.company
		) == "Moving Average" and frappe.db.get_single_value(
			"Stock Settings", "do_not_use_batchwise_valuation"
		):
			return {}

		batchwise_batches = frappe.get_all(
			"Batch",
			filters={"name": ("in", batch_nos), "use_batchwise_valuation": 1},
			pluck="name",
		)
		if not batchwise_batches:
			return {}

		# scoped to batchwise batches only, so BatchNoValuation's non-batchwise
		# machinery never runs for them
		sle = self.get_sle_for_outward_transaction()
		sle.batch_nos = {batch_no: sle.batch_nos[batch_no] for batch_no in batchwise_batches}
		sle.batchwise_valuation_batches = batchwise_batches
		sn_obj = BatchNoValuation(sle=sle, item_code=self.doc.item_code, warehouse=self.doc.warehouse)
		return {
			batch_no: abs(flt(sn_obj.batch_avg_rate.get(batch_no)))
			for batch_no in batchwise_batches
			if flt(sn_obj.available_qty.get(batch_no))
		}

	def get_valuation_rate_for_return_entry(self, return_against):
		from erpnext.controllers.sales_and_purchase_return import get_warehouses_for_return

		if not self.doc.voucher_detail_no:
			return {}

		field = {
			"Sales Invoice": "sales_invoice_item",
			"Purchase Invoice": "purchase_invoice_item",
			"Delivery Note": "dn_detail",
			"Purchase Receipt": "purchase_receipt_item",
			"Subcontracting Receipt": "subcontracting_receipt_item",
		}.get(self.doc.voucher_type)

		return_against_voucher_detail_no = frappe.db.get_value(
			self.doc.child_table, self.doc.voucher_detail_no, field
		)

		if not return_against_voucher_detail_no and self.doc.voucher_type in (
			"Delivery Note",
			"Sales Invoice",
		):
			# Bundles built via the use_serial_batch_fields / SLE-driven path keep the Packed Item
			# as voucher_detail_no (not remapped to the DN/SI Item), so the lookup above misses.
			return_against_voucher_detail_no = self.get_return_against_packed_item(field)

		if not return_against_voucher_detail_no and self.doc.voucher_type == "Subcontracting Receipt":
			return self.get_valuation_rate_for_returned_supplied_item(return_against)

		filters = [
			["Serial and Batch Bundle", "voucher_no", "=", return_against],
			["Serial and Batch Entry", "docstatus", "=", 1],
			["Serial and Batch Bundle", "is_cancelled", "=", 0],
			["Serial and Batch Bundle", "item_code", "=", self.doc.item_code],
			["Serial and Batch Bundle", "voucher_detail_no", "=", return_against_voucher_detail_no],
		]

		# Added to handle rejected warehouse case
		return_warehouse = None
		if self.doc.voucher_type in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
			warehouses = get_warehouses_for_return(self.doc.voucher_type, return_against_voucher_detail_no)
			if self.doc.warehouse in warehouses:
				return_warehouse = self.doc.warehouse
				filters.append(["Serial and Batch Entry", "warehouse", "=", return_warehouse])

		bundle_data = frappe.get_all(
			"Serial and Batch Bundle",
			fields=[
				"name",
				"`tabSerial and Batch Entry`.`serial_no`",
				"`tabSerial and Batch Entry`.`batch_no`",
				"`tabSerial and Batch Entry`.`incoming_rate`",
			],
			filters=filters,
			order_by="`tabSerial and Batch Bundle`.`creation`, `tabSerial and Batch Entry`.`idx`",
		)
		if delivered_bundle := self.get_delivered_packed_item_bundle():
			# the delivered packed row's own rate wins for a batch other packed rows delivered too
			bundle_data.sort(key=lambda row: row.name == delivered_bundle)

		if not bundle_data:
			bundle_data = self.get_legacy_valuation_rate_for_return_entry(
				return_against, return_against_voucher_detail_no, return_warehouse
			)

		return self.get_valuation_details(bundle_data)

	def get_valuation_rate_for_returned_supplied_item(self, return_against):
		"""Rates of the serial nos and batches the returned receipt consumed for this raw material row."""
		returned = frappe.qb.DocType("Subcontracting Receipt Supplied Item")
		consumed = frappe.qb.DocType("Subcontracting Receipt Supplied Item").as_("consumed")
		item = frappe.qb.DocType("Subcontracting Receipt Item")
		original = frappe.qb.DocType("Subcontracting Receipt Item").as_("original")
		entry = frappe.qb.DocType("Serial and Batch Entry")

		bundle_data = (
			frappe.qb.from_(returned)
			.join(item)
			.on(item.name == returned.reference_name)
			.join(original)
			.on(original.name == item.subcontracting_receipt_item)
			.join(consumed)
			.on((consumed.reference_name == original.name) & (consumed.rm_item_code == returned.rm_item_code))
			.join(entry)
			.on(entry.parent == consumed.serial_and_batch_bundle)
			.select(entry.serial_no, entry.batch_no, entry.incoming_rate)
			.where(
				(returned.name == self.doc.voucher_detail_no)
				& (consumed.parent == return_against)
				& (entry.docstatus == 1)
				# returned rejected goods bring raw materials back at the row rate, see get_rejected_return_rows
				& (item.warehouse != Coalesce(original.rejected_warehouse, ""))
			)
			.orderby(consumed.idx)
			.orderby(entry.idx)
		).run(as_dict=True)

		return self.get_valuation_details(bundle_data)

	@staticmethod
	def get_valuation_details(bundle_data):
		if not bundle_data:
			return {}

		valuation_details = frappe._dict(
			{
				"serial_nos": defaultdict(float),
				"batches": defaultdict(float),
			}
		)
		for row in bundle_data:
			if row.serial_no:
				valuation_details["serial_nos"][row.serial_no] = row.incoming_rate
			if row.batch_no:
				valuation_details["batches"][row.batch_no] = row.incoming_rate

		return valuation_details

	def get_delivered_packed_item_bundle(self):
		"""Bundle of the delivered packed row that the return's packed row of this bundle reverses."""
		if self.doc.voucher_type not in ("Delivery Note", "Sales Invoice"):
			return

		returned = frappe.qb.DocType("Packed Item")
		delivered = frappe.qb.DocType("Packed Item").as_("delivered")
		bundles = (
			frappe.qb.from_(returned)
			.join(delivered)
			.on(delivered.name == returned.return_against_packed_item)
			.select(delivered.serial_and_batch_bundle)
			# a packed row's bundle points to the packed row, or to its bundle row once posted
			.where(
				(returned.name == self.doc.voucher_detail_no)
				| (
					(returned.parent_detail_docname == self.doc.voucher_detail_no)
					& (returned.serial_and_batch_bundle == self.doc.name)
				)
			)
			.limit(1)
			.run()
		)
		return bundles[0][0] if bundles else None

	def get_return_against_packed_item(self, field):
		"""Resolve the original DN/SI Item when a return bundle's voucher_detail_no is the Packed Item."""
		parent_detail_docname = frappe.db.get_value(
			"Packed Item", self.doc.voucher_detail_no, "parent_detail_docname"
		)
		if not parent_detail_docname:
			return

		return frappe.db.get_value(self.doc.child_table, parent_detail_docname, field)

	def get_legacy_valuation_rate_for_return_entry(
		self, return_against, return_against_voucher_detail_no, return_warehouse=None
	):
		"""Return the original line's incoming rate per serial no / batch from the SLE, for legacy receipts with no bundle."""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if not (self.doc.has_serial_no or self.doc.has_batch_no):
			return []

		sle = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(sle)
			.select(sle.serial_no, sle.batch_no, sle.incoming_rate)
			.where(
				(sle.voucher_no == return_against)
				& (sle.voucher_detail_no == return_against_voucher_detail_no)
				& (sle.item_code == self.doc.item_code)
				& (sle.is_cancelled == 0)
				& (sle.serial_and_batch_bundle.isnull())
			)
		)

		if return_warehouse:
			query = query.where(sle.warehouse == return_warehouse)

		data = []
		for d in query.run(as_dict=True):
			if d.serial_no:
				for serial_no in get_serial_nos(d.serial_no):
					data.append(
						frappe._dict(
							{"serial_no": serial_no, "batch_no": d.batch_no, "incoming_rate": d.incoming_rate}
						)
					)
			elif d.batch_no:
				data.append(
					frappe._dict(
						{"serial_no": None, "batch_no": d.batch_no, "incoming_rate": d.incoming_rate}
					)
				)

		return data

	def validate_returned_serial_batch_no(self, return_against, row, original_inv_details):
		if frappe.flags.through_repost_item_valuation and not frappe.in_test:
			return

		if row.serial_no and row.serial_no not in original_inv_details["serial_nos"]:
			self.doc.throw_error_message(
				_(
					"Serial No {0} is not present in the {1} {2}, hence you can't return it against the {1} {2}"
				).format(
					bold(SerialBatchIdentity("Serial No").get_label(row.serial_no)),
					self.doc.voucher_type,
					bold(return_against),
				)
			)

		if row.batch_no and row.batch_no not in original_inv_details["batches"]:
			self.doc.throw_error_message(
				_(
					"Batch No {0} is not present in the original {1} {2}, hence you can't return it against the {1} {2}"
				).format(
					bold(SerialBatchIdentity("Batch").get_label(row.batch_no)),
					self.doc.voucher_type,
					bold(return_against),
				)
			)

	def validate_serial_and_batch_no_for_returned(self):
		if not self.doc.returned_against:
			return

		if self.doc.voucher_type not in [
			"Purchase Receipt",
			"Purchase Invoice",
			"Sales Invoice",
			"Delivery Note",
		]:
			return

		data = self.get_orignal_document_data()
		if not data:
			return

		serial_nos, batches = [], []
		current_serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]
		current_batches = [d.batch_no for d in self.doc.entries if d.batch_no]

		for d in data:
			if self.doc.has_serial_no:
				if d.serial_and_batch_bundle:
					serial_nos = get_serial_nos_from_bundle(d.serial_and_batch_bundle)
				else:
					serial_nos = SerialBatchIdentity("Serial No").resolve(
						d.item_code, parse_serial_nos(d.serial_no), ignore_permissions=True
					)

			elif self.doc.has_batch_no:
				if d.serial_and_batch_bundle:
					batches = get_batches_from_bundle(d.serial_and_batch_bundle)
				else:
					batches = frappe._dict({d.batch_no: d.stock_qty})

				if batches:
					batches = [d for d in batches if batches[d] > 0]

			if serial_nos:
				if invalid_serial_nos := set(current_serial_nos) - set(serial_nos):
					numbers = frappe.get_all(
						"Serial No", filters={"name": ("in", invalid_serial_nos)}, pluck="serial_no"
					)
					self.doc.throw_error_message(
						_("Serial Nos {0} are not part of the original document.").format(
							bold(escape_html(", ".join(numbers)))
						)
					)

			if batches:
				if invalid_batches := set(current_batches) - set(batches):
					numbers = frappe.get_all(
						"Batch", filters={"name": ("in", invalid_batches)}, pluck="batch_id"
					)
					self.doc.throw_error_message(
						_("Batch Nos {0} are not part of the original document.").format(
							bold(escape_html(", ".join(numbers)))
						)
					)

	def get_orignal_document_data(self):
		fields = ["item_code", "serial_and_batch_bundle", "stock_qty"]
		if self.doc.has_serial_no:
			fields.append("serial_no")

		elif self.doc.has_batch_no:
			fields.append("batch_no")

		child_doc = self.doc.voucher_type + " Item"
		return frappe.get_all(child_doc, fields=fields, filters={"name": self.doc.returned_against})

	def validate_returned_batch_qty(self):
		reference_field = {"Delivery Note": "dn_detail", "Sales Invoice": "sales_invoice_item"}.get(
			self.doc.voucher_type
		)
		if (
			self.doc.type_of_transaction != "Inward"
			or not reference_field
			or not self.doc.has_batch_no
			or self.doc.has_serial_no
		):
			return

		child_doctype = self.doc.voucher_type + " Item"
		original_row = frappe.db.get_value(child_doctype, self.doc.voucher_detail_no, reference_field)
		available = original_row and self.get_batch_qty_left_to_return(
			child_doctype, reference_field, original_row
		)
		if not available:
			return

		precision = self.doc.precision("total_qty")
		for row in self.doc.entries:
			remaining = flt(available.get(row.batch_no), precision)
			if row.batch_no and flt(abs(row.qty), precision) > remaining:
				self.doc.throw_error_message(
					_(
						"Row #{0}: Cannot return {1} of Batch {2}, only {3} was delivered and not returned yet."
					).format(
						row.idx,
						abs(row.qty),
						bold(SerialBatchIdentity("Batch").get_label(row.batch_no)),
						max(remaining, 0),
					)
				)

	def get_batch_qty_left_to_return(self, child_doctype, reference_field, original_row):
		original = frappe.db.get_value(
			child_doctype, original_row, ["serial_and_batch_bundle", "batch_no", "stock_qty"], as_dict=True
		)
		if not original:
			return {}

		delivered = get_batches_from_bundle(original.serial_and_batch_bundle) or {
			original.batch_no: original.stock_qty
		}
		available = {batch_no: abs(flt(qty)) for batch_no, qty in delivered.items() if batch_no}
		if not available:
			return available

		for batch_no, qty in self.get_returned_batch_qty(child_doctype, reference_field, original_row):
			available[batch_no] = flt(available.get(batch_no)) - flt(qty)
		return available

	def get_returned_batch_qty(self, child_doctype, reference_field, original_row):
		child = frappe.qb.DocType(child_doctype)
		parent = frappe.qb.DocType(self.doc.voucher_type)
		entry = frappe.qb.DocType("Serial and Batch Entry")
		return (
			frappe.qb.from_(entry)
			.join(child)
			.on(entry.parent == child.serial_and_batch_bundle)
			.join(parent)
			.on(child.parent == parent.name)
			.select(entry.batch_no, Sum(Abs(entry.qty)))
			.where(
				(child[reference_field] == original_row)
				& (child.name != self.doc.voucher_detail_no)
				& (entry.docstatus == 1)
				& (parent.docstatus == 1)
				& (parent.is_return == 1)
			)
			.groupby(entry.batch_no)
		).run()
