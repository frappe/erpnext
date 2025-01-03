# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import collections
import csv
from collections import Counter, defaultdict

import frappe
from frappe import _, _dict, bold
from frappe.model.document import Document
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import (
	add_days,
	cint,
	cstr,
	flt,
	get_link_to_form,
	now,
	nowtime,
	parse_json,
	today,
)
from frappe.utils.csvutils import build_csv_response

from erpnext.stock.serial_batch_bundle import (
	BatchNoValuation,
	SerialNoValuation,
	get_batches_from_bundle,
)
from erpnext.stock.serial_batch_bundle import get_serial_nos as get_serial_nos_from_bundle


class SerialNoExistsInFutureTransactionError(frappe.ValidationError):
	pass


class BatchNegativeStockError(frappe.ValidationError):
	pass


class SerialNoDuplicateError(frappe.ValidationError):
	pass


class SerialNoWarehouseError(frappe.ValidationError):
	pass


class SerialandBatchBundle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.serial_and_batch_entry.serial_and_batch_entry import (
			SerialandBatchEntry,
		)

		amended_from: DF.Link | None
		avg_rate: DF.Float
		company: DF.Link
		entries: DF.Table[SerialandBatchEntry]
		has_batch_no: DF.Check
		has_serial_no: DF.Check
		is_cancelled: DF.Check
		is_rejected: DF.Check
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		naming_series: DF.Literal["SABB-.########"]
		posting_date: DF.Date | None
		posting_time: DF.Time | None
		returned_against: DF.Data | None
		total_amount: DF.Float
		total_qty: DF.Float
		type_of_transaction: DF.Literal["", "Inward", "Outward", "Maintenance", "Asset Repair"]
		voucher_detail_no: DF.Data | None
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link
		warehouse: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.reset_serial_batch_bundle()
		self.set_batch_no()
		self.validate_serial_and_batch_no()
		self.validate_duplicate_serial_and_batch_no()
		self.validate_voucher_no()

		if self.type_of_transaction == "Maintenance":
			return

		self.allow_existing_serial_nos()
		if not self.flags.ignore_validate_serial_batch or frappe.flags.in_test:
			self.validate_serial_nos_duplicate()
			self.check_future_entries_exists()

		self.set_is_outward()
		self.calculate_total_qty()
		self.set_warehouse()
		self.set_incoming_rate()
		self.calculate_qty_and_amount()

	def allow_existing_serial_nos(self):
		if self.type_of_transaction == "Outward" or not self.has_serial_no:
			return

		if frappe.db.get_single_value("Stock Settings", "allow_existing_serial_no"):
			return

		if self.voucher_type not in ["Purchase Receipt", "Purchase Invoice", "Stock Entry"]:
			return

		if self.voucher_type == "Stock Entry" and frappe.get_cached_value(
			"Stock Entry", self.voucher_no, "purpose"
		) in ["Material Transfer", "Send to Subcontractor", "Material Transfer for Manufacture"]:
			return

		serial_nos = [d.serial_no for d in self.entries if d.serial_no]

		data = frappe.get_all(
			"Serial and Batch Entry",
			filters={"serial_no": ("in", serial_nos), "docstatus": 1, "qty": ("<", 0)},
			fields=["serial_no", "parent"],
		)

		note = "<br><br> <b>Note</b>:<br>"
		for row in data:
			frappe.throw(
				_(
					"You can't process the serial number {0} as it has already been used in the SABB {1}. {2} if you want to inward same serial number multiple times then enabled 'Allow existing Serial No to be Manufactured/Received again' in the {3}"
				).format(
					row.serial_no,
					get_link_to_form("Serial and Batch Bundle", row.parent),
					note,
					get_link_to_form("Stock Settings", "Stock Settings"),
				)
			)

	def reset_serial_batch_bundle(self):
		if self.is_new() and self.amended_from:
			for field in ["is_cancelled", "is_rejected"]:
				if self.get(field):
					self.set(field, 0)

			if self.voucher_detail_no:
				self.voucher_detail_no = None

	def set_batch_no(self):
		if self.has_serial_no and self.has_batch_no:
			serial_nos = [d.serial_no for d in self.entries if d.serial_no]
			has_no_batch = any(not d.batch_no for d in self.entries)
			if not has_no_batch:
				return

			serial_no_batch = frappe._dict(
				frappe.get_all(
					"Serial No",
					filters={"name": ("in", serial_nos)},
					fields=["name", "batch_no"],
					as_list=True,
				)
			)

			for row in self.entries:
				if not row.batch_no:
					row.batch_no = serial_no_batch.get(row.serial_no)

	def validate_serial_nos_inventory(self):
		if not (self.has_serial_no and self.type_of_transaction == "Outward"):
			return

		serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		kwargs = {
			"item_code": self.item_code,
			"warehouse": self.warehouse,
			"check_serial_nos": True,
			"serial_nos": serial_nos,
		}
		if self.voucher_type == "POS Invoice":
			kwargs["ignore_voucher_nos"] = [self.voucher_no]

		available_serial_nos = get_available_serial_nos(frappe._dict(kwargs))

		serial_no_warehouse = {}
		for data in available_serial_nos:
			if data.serial_no not in serial_nos:
				continue

			serial_no_warehouse[data.serial_no] = data.warehouse

		for serial_no in serial_nos:
			if not serial_no_warehouse.get(serial_no) or serial_no_warehouse.get(serial_no) != self.warehouse:
				self.throw_error_message(
					f"Serial No {bold(serial_no)} is not present in the warehouse {bold(self.warehouse)}.",
					SerialNoWarehouseError,
				)

	def validate_serial_nos_duplicate(self):
		# Don't inward same serial number multiple times
		if self.voucher_type in ["POS Invoice", "Pick List"]:
			return

		if not self.warehouse:
			return

		if self.voucher_type in ["Stock Reconciliation", "Stock Entry"] and self.docstatus != 1:
			return

		if not (self.has_serial_no and self.type_of_transaction == "Inward"):
			return

		serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		kwargs = frappe._dict(
			{
				"item_code": self.item_code,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"serial_nos": serial_nos,
				"check_serial_nos": True,
			}
		)

		if self.returned_against and self.docstatus == 1:
			kwargs["ignore_voucher_detail_no"] = self.voucher_detail_no

		if self.docstatus == 1:
			kwargs["voucher_no"] = self.voucher_no

		available_serial_nos = get_available_serial_nos(kwargs)
		for data in available_serial_nos:
			if data.serial_no in serial_nos:
				self.throw_error_message(
					f"Serial No {bold(data.serial_no)} is already present in the warehouse {bold(data.warehouse)}.",
					SerialNoDuplicateError,
				)

	def throw_error_message(self, message, exception=frappe.ValidationError):
		frappe.throw(_(message), exception, title=_("Error"))

	def set_incoming_rate(self, parent=None, row=None, save=False, allow_negative_stock=False):
		if self.type_of_transaction not in ["Inward", "Outward"] or self.voucher_type in [
			"Installation Note",
			"Job Card",
			"Maintenance Schedule",
			"Pick List",
		]:
			return

		if return_against := self.get_return_against(parent=parent):
			self.set_valuation_rate_for_return_entry(return_against, save)
		elif self.type_of_transaction == "Outward":
			self.set_incoming_rate_for_outward_transaction(
				row, save, allow_negative_stock=allow_negative_stock
			)
		else:
			self.set_incoming_rate_for_inward_transaction(row, save)

	def set_valuation_rate_for_return_entry(self, return_against, save=False):
		if valuation_details := self.get_valuation_rate_for_return_entry(return_against):
			for row in self.entries:
				if valuation_details:
					self.validate_returned_serial_batch_no(return_against, row, valuation_details)

				if row.serial_no:
					valuation_rate = valuation_details["serial_nos"].get(row.serial_no)
				else:
					valuation_rate = valuation_details["batches"].get(row.batch_no)

				row.incoming_rate = flt(valuation_rate)
				row.stock_value_difference = flt(row.qty) * flt(row.incoming_rate)

				if save:
					row.db_set(
						{
							"incoming_rate": row.incoming_rate,
							"stock_value_difference": row.stock_value_difference,
						}
					)

	def validate_returned_serial_batch_no(self, return_against, row, original_inv_details):
		if row.serial_no and row.serial_no not in original_inv_details["serial_nos"]:
			self.throw_error_message(
				_(
					"Serial No {0} is not present in the {1} {2}, hence you can't return it against the {1} {2}"
				).format(bold(row.serial_no), self.voucher_type, bold(return_against))
			)

		if row.batch_no and row.batch_no not in original_inv_details["batches"]:
			self.throw_error_message(
				_(
					"Batch No {0} is not present in the original {1} {2}, hence you can't return it against the {1} {2}"
				).format(bold(row.batch_no), self.voucher_type, bold(return_against))
			)

	def get_valuation_rate_for_return_entry(self, return_against):
		valuation_details = frappe._dict(
			{
				"serial_nos": defaultdict(float),
				"batches": defaultdict(float),
			}
		)

		bundle_data = frappe.get_all(
			"Serial and Batch Bundle",
			fields=[
				"`tabSerial and Batch Entry`.`serial_no`",
				"`tabSerial and Batch Entry`.`batch_no`",
				"`tabSerial and Batch Entry`.`incoming_rate`",
			],
			filters=[
				["Serial and Batch Bundle", "voucher_no", "=", return_against],
				["Serial and Batch Entry", "docstatus", "=", 1],
				["Serial and Batch Bundle", "is_cancelled", "=", 0],
				["Serial and Batch Bundle", "item_code", "=", self.item_code],
				["Serial and Batch Bundle", "warehouse", "=", self.warehouse],
			],
			order_by="`tabSerial and Batch Bundle`.`creation`, `tabSerial and Batch Entry`.`idx`",
		)

		if not bundle_data:
			return {}

		for row in bundle_data:
			if row.serial_no:
				valuation_details["serial_nos"][row.serial_no] = row.incoming_rate
			else:
				valuation_details["batches"][row.batch_no] = row.incoming_rate

		return valuation_details

	def calculate_total_qty(self, save=True):
		self.total_qty = 0.0
		for d in self.entries:
			d.qty = 1 if self.has_serial_no and abs(d.qty) > 1 else abs(d.qty) if d.qty else 0
			d.stock_value_difference = abs(d.stock_value_difference) if d.stock_value_difference else 0
			if self.type_of_transaction == "Outward":
				d.qty *= -1
				d.stock_value_difference *= -1

			self.total_qty += flt(d.qty)

		if save:
			self.db_set("total_qty", self.total_qty)

	def get_serial_nos(self):
		return [d.serial_no for d in self.entries if d.serial_no]

	def update_valuation_rate(self, valuation_rate=None, save=False):
		for row in self.entries:
			row.incoming_rate = valuation_rate
			row.stock_value_difference = flt(row.qty) * flt(valuation_rate)

			if save:
				row.db_set(
					{"incoming_rate": row.incoming_rate, "stock_value_difference": row.stock_value_difference}
				)

	def set_incoming_rate_for_outward_transaction(self, row=None, save=False, allow_negative_stock=False):
		sle = self.get_sle_for_outward_transaction()

		if self.has_serial_no:
			sn_obj = SerialNoValuation(
				sle=sle,
				item_code=self.item_code,
				warehouse=self.warehouse,
			)

		else:
			sn_obj = BatchNoValuation(
				sle=sle,
				item_code=self.item_code,
				warehouse=self.warehouse,
			)

		for d in self.entries:
			available_qty = 0

			if self.has_serial_no:
				d.incoming_rate = abs(sn_obj.serial_no_incoming_rate.get(d.serial_no, 0.0))
			else:
				d.incoming_rate = abs(flt(sn_obj.batch_avg_rate.get(d.batch_no)))

				available_qty = flt(sn_obj.available_qty.get(d.batch_no), d.precision("qty"))
				if self.docstatus == 1:
					available_qty += flt(d.qty, d.precision("qty"))

				if not allow_negative_stock:
					self.validate_negative_batch(d.batch_no, available_qty)

			d.stock_value_difference = flt(d.qty) * flt(d.incoming_rate)

			if save:
				d.db_set(
					{"incoming_rate": d.incoming_rate, "stock_value_difference": d.stock_value_difference}
				)

	def validate_negative_batch(self, batch_no, available_qty):
		if available_qty < 0 and not self.is_stock_reco_for_valuation_adjustment(available_qty):
			msg = f"""Batch No {bold(batch_no)} of an Item {bold(self.item_code)}
				has negative stock
				of quantity {bold(available_qty)} in the
				warehouse {self.warehouse}"""

			frappe.throw(_(msg), BatchNegativeStockError)

	def is_stock_reco_for_valuation_adjustment(self, available_qty):
		if (
			self.voucher_type == "Stock Reconciliation"
			and self.type_of_transaction == "Outward"
			and self.voucher_detail_no
			and abs(frappe.db.get_value("Stock Reconciliation Item", self.voucher_detail_no, "qty"))
			== abs(available_qty)
		):
			return True

		return False

	def get_sle_for_outward_transaction(self):
		sle = frappe._dict(
			{
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"serial_and_batch_bundle": self.name,
				"actual_qty": self.total_qty,
				"company": self.company,
				"serial_nos": [row.serial_no for row in self.entries if row.serial_no],
				"batch_nos": {row.batch_no: row for row in self.entries if row.batch_no},
				"voucher_type": self.voucher_type,
				"voucher_detail_no": self.voucher_detail_no,
				"creation": self.creation,
			}
		)

		if self.docstatus == 1:
			sle["voucher_no"] = self.voucher_no

		if not sle.actual_qty:
			self.calculate_total_qty()
			sle.actual_qty = self.total_qty

		return sle

	def get_return_against(self, parent=None):
		return_against = None

		if parent and parent.get("is_return") and parent.get("return_against"):
			return parent.get("return_against")

		if (
			self.voucher_type
			in [
				"Delivery Note",
				"Sales Invoice",
				"Purchase Invoice",
				"Purchase Receipt",
				"POS Invoice",
				"Subcontracting Receipt",
			]
			and self.voucher_type
			and self.voucher_no
		):
			voucher_details = frappe.db.get_value(
				self.voucher_type, self.voucher_no, ["is_return", "return_against"], as_dict=True
			)
			if voucher_details and voucher_details.get("is_return") and voucher_details.get("return_against"):
				return voucher_details.get("return_against")

		return return_against

	def set_incoming_rate_for_inward_transaction(self, row=None, save=False):
		valuation_field = "valuation_rate"
		if self.voucher_type in ["Sales Invoice", "Delivery Note", "Quotation"]:
			valuation_field = "incoming_rate"

		if self.voucher_type == "POS Invoice":
			valuation_field = "rate"

		rate = row.get(valuation_field) if row else 0.0
		child_table = self.child_table

		if self.voucher_type == "Subcontracting Receipt":
			if not self.voucher_detail_no:
				return
			elif frappe.db.exists("Subcontracting Receipt Supplied Item", self.voucher_detail_no):
				valuation_field = "rate"
				child_table = "Subcontracting Receipt Supplied Item"
			else:
				valuation_field = "rate"
				child_table = "Subcontracting Receipt Item"

		if not rate and self.voucher_detail_no and self.voucher_no:
			rate = frappe.db.get_value(child_table, self.voucher_detail_no, valuation_field)

		for d in self.entries:
			if self.is_rejected:
				rate = 0.0
			elif (d.incoming_rate == rate) and d.qty and d.stock_value_difference:
				continue

			d.incoming_rate = flt(rate)
			if d.qty:
				d.stock_value_difference = flt(d.qty) * d.incoming_rate

			if save:
				d.db_set(
					{"incoming_rate": d.incoming_rate, "stock_value_difference": d.stock_value_difference}
				)

	def set_serial_and_batch_values(self, parent, row, qty_field=None):
		values_to_set = {}
		if not self.voucher_no or self.voucher_no != row.parent:
			values_to_set["voucher_no"] = row.parent

		self.db_set("is_cancelled", 0)

		if self.voucher_type != parent.doctype:
			values_to_set["voucher_type"] = parent.doctype

		if not self.voucher_detail_no or self.voucher_detail_no != row.name:
			values_to_set["voucher_detail_no"] = row.name

		if parent.get("posting_date") and (not self.posting_date or self.posting_date != parent.posting_date):
			values_to_set["posting_date"] = parent.posting_date or today()

		if parent.get("posting_time") and (not self.posting_time or self.posting_time != parent.posting_time):
			values_to_set["posting_time"] = parent.posting_time

		if parent.doctype in [
			"Delivery Note",
			"Purchase Receipt",
			"Purchase Invoice",
			"Sales Invoice",
		] and parent.get("is_return"):
			return_ref_field = frappe.scrub(parent.doctype) + "_item"
			if parent.doctype == "Delivery Note":
				return_ref_field = "dn_detail"

			if row.get(return_ref_field):
				values_to_set["returned_against"] = row.get(return_ref_field)

		if values_to_set:
			self.db_set(values_to_set)

		self.calculate_total_qty(save=True)

		# If user has changed the rate in the child table
		if self.docstatus == 0:
			self.set_incoming_rate(parent=parent, row=row, save=True)

		if self.docstatus == 0 and parent.get("is_return") and parent.is_new():
			self.reset_qty(row, qty_field=qty_field)

		self.calculate_qty_and_amount(save=True)
		self.validate_quantity(row, qty_field=qty_field)

	def validate_voucher_no(self):
		if not (self.voucher_type and self.voucher_no):
			return

		if (
			self.docstatus == 1
			and self.voucher_no
			and not frappe.db.exists(self.voucher_type, self.voucher_no)
		):
			self.throw_error_message(f"The {self.voucher_type} # {self.voucher_no} does not exist")

		if self.flags.ignore_voucher_validation:
			return

		if (
			self.docstatus == 1
			and frappe.get_cached_value(self.voucher_type, self.voucher_no, "docstatus") != 1
		):
			self.throw_error_message(f"The {self.voucher_type} # {self.voucher_no} should be submit first.")

	def check_future_entries_exists(self):
		if self.flags and self.flags.via_landed_cost_voucher:
			return

		if not self.has_serial_no:
			return

		serial_nos = [d.serial_no for d in self.entries if d.serial_no]

		if not serial_nos:
			return

		parent = frappe.qb.DocType("Serial and Batch Bundle")
		child = frappe.qb.DocType("Serial and Batch Entry")

		timestamp_condition = CombineDatetime(parent.posting_date, parent.posting_time) > CombineDatetime(
			self.posting_date, self.posting_time
		)

		future_entries = (
			frappe.qb.from_(parent)
			.inner_join(child)
			.on(parent.name == child.parent)
			.select(
				child.serial_no,
				parent.voucher_type,
				parent.voucher_no,
			)
			.where(
				(child.serial_no.isin(serial_nos))
				& (child.parent != self.name)
				& (parent.item_code == self.item_code)
				& (parent.docstatus == 1)
				& (parent.is_cancelled == 0)
				& (parent.type_of_transaction.isin(["Inward", "Outward"]))
			)
			.where(timestamp_condition)
		).run(as_dict=True)

		if future_entries:
			msg = """The serial nos has been used in the future
				transactions so you need to cancel them first.
				The list of serial nos and their respective
				transactions are as below."""

			msg += "<br><br><ul>"

			for d in future_entries:
				msg += f"<li>{d.serial_no} in {get_link_to_form(d.voucher_type, d.voucher_no)}</li>"
			msg += "</li></ul>"

			title = "Serial No Exists In Future Transaction(s)"

			frappe.throw(_(msg), title=_(title), exc=SerialNoExistsInFutureTransactionError)

	def reset_qty(self, row, qty_field=None):
		qty_field = self.get_qty_field(row, qty_field=qty_field)
		qty = abs(row.get(qty_field))

		idx = None
		while qty > 0:
			for d in self.entries:
				row_qty = abs(d.qty)
				if row_qty >= qty:
					d.db_set("qty", qty if self.type_of_transaction == "Inward" else qty * -1)
					qty = 0
					idx = d.idx
					break
				else:
					qty -= row_qty
					idx = d.idx

		if idx and len(self.entries) > idx:
			remove_rows = []
			for d in self.entries:
				if d.idx > idx:
					remove_rows.append(d)

			for d in remove_rows:
				self.entries.remove(d)

			self.flags.ignore_links = True
			self.save()

	def validate_quantity(self, row, qty_field=None):
		qty_field = self.get_qty_field(row, qty_field=qty_field)
		qty = row.get(qty_field)
		if qty_field == "qty" and row.get("stock_qty"):
			qty = row.get("stock_qty")

		precision = row.precision
		if abs(abs(flt(self.total_qty, precision)) - abs(flt(qty, precision))) > 0.01:
			total_qty = frappe.format_value(abs(flt(self.total_qty)), "Float", row)
			set_qty = frappe.format_value(abs(flt(row.get(qty_field))), "Float", row)
			self.throw_error_message(
				f"Total quantity {total_qty} in the Serial and Batch Bundle {bold(self.name)} does not match with the quantity {set_qty} for the Item {bold(self.item_code)} in the {self.voucher_type} # {self.voucher_no}"
			)

	def get_qty_field(self, row, qty_field=None) -> str:
		if not qty_field:
			qty_field = "qty"

		if row.get("doctype") == "Subcontracting Receipt Supplied Item":
			qty_field = "consumed_qty"
		elif row.get("doctype") == "Stock Entry Detail":
			qty_field = "transfer_qty"

		return qty_field

	def set_is_outward(self):
		for row in self.entries:
			if self.type_of_transaction == "Outward" and row.qty > 0:
				row.qty *= -1
			elif self.type_of_transaction == "Inward" and row.qty < 0:
				row.qty *= -1

			row.is_outward = 1 if self.type_of_transaction == "Outward" else 0

	@frappe.whitelist()
	def set_warehouse(self):
		for row in self.entries:
			if row.warehouse != self.warehouse:
				row.warehouse = self.warehouse

	def calculate_qty_and_amount(self, save=False):
		self.total_amount = 0.0
		self.total_qty = 0.0
		self.avg_rate = 0.0

		for row in self.entries:
			rate = flt(row.incoming_rate)
			row.stock_value_difference = flt(row.qty) * rate
			self.total_amount += flt(row.qty) * rate
			self.total_qty += flt(row.qty)

		if self.total_qty:
			self.avg_rate = flt(self.total_amount) / flt(self.total_qty)

		if save:
			self.db_set(
				{
					"total_qty": self.total_qty,
					"avg_rate": self.avg_rate,
					"total_amount": self.total_amount,
				}
			)

	def calculate_outgoing_rate(self):
		if not (self.has_serial_no and self.entries):
			return

		if not (self.voucher_type and self.voucher_no):
			return False

		if self.voucher_type in ["Purchase Receipt", "Purchase Invoice"]:
			return frappe.get_cached_value(self.voucher_type, self.voucher_no, "is_return")
		elif self.voucher_type in ["Sales Invoice", "Delivery Note"]:
			return not frappe.get_cached_value(self.voucher_type, self.voucher_no, "is_return")
		elif self.voucher_type == "Stock Entry":
			return frappe.get_cached_value(self.voucher_type, self.voucher_no, "purpose") in [
				"Material Receipt"
			]

	def validate_serial_and_batch_no(self):
		if self.item_code and not self.has_serial_no and not self.has_batch_no:
			msg = f"The Item {self.item_code} does not have Serial No or Batch No"
			frappe.throw(_(msg))

		serial_nos = []
		batch_nos = []

		serial_batches = {}
		for row in self.entries:
			if not row.qty and row.batch_no and not row.serial_no:
				if self.voucher_type == "Stock Reconciliation" and self.type_of_transaction == "Inward":
					continue

				frappe.throw(
					_("At row {0}: Qty is mandatory for the batch {1}").format(
						bold(row.idx), bold(row.batch_no)
					)
				)

			if self.has_serial_no and not row.serial_no:
				frappe.throw(
					_("At row {0}: Serial No is mandatory for Item {1}").format(
						bold(row.idx), bold(self.item_code)
					),
					title=_("Serial No is mandatory"),
				)

			if self.has_batch_no and not row.batch_no:
				frappe.throw(
					_("At row {0}: Batch No is mandatory for Item {1}").format(
						bold(row.idx), bold(self.item_code)
					),
					title=_("Batch No is mandatory"),
				)

			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no and not row.serial_no:
				batch_nos.append(row.batch_no)

			if row.serial_no and row.batch_no and self.type_of_transaction == "Outward":
				serial_batches.setdefault(row.serial_no, row.batch_no)

		if serial_nos:
			self.validate_incorrect_serial_nos(serial_nos)

		elif batch_nos:
			self.validate_incorrect_batch_nos(batch_nos)

		if serial_batches:
			self.validate_serial_batch_no(serial_batches)

	def validate_serial_batch_no(self, serial_batches):
		correct_batches = frappe._dict(
			frappe.get_all(
				"Serial No",
				filters={"name": ("in", list(serial_batches.keys()))},
				fields=["name", "batch_no"],
				as_list=True,
			)
		)

		for serial_no, batch_no in serial_batches.items():
			if correct_batches.get(serial_no) and correct_batches.get(serial_no) != batch_no:
				self.throw_error_message(
					f"Serial No {bold(serial_no)} does not belong to Batch No {bold(batch_no)}"
				)

	def validate_incorrect_serial_nos(self, serial_nos):
		incorrect_serial_nos = frappe.get_all(
			"Serial No",
			filters={"name": ("in", serial_nos), "item_code": ("!=", self.item_code)},
			fields=["name"],
		)

		if incorrect_serial_nos:
			incorrect_serial_nos = ", ".join([d.name for d in incorrect_serial_nos])
			self.throw_error_message(
				f"Serial Nos {bold(incorrect_serial_nos)} does not belong to Item {bold(self.item_code)}"
			)

	def validate_incorrect_batch_nos(self, batch_nos):
		incorrect_batch_nos = frappe.get_all(
			"Batch", filters={"name": ("in", batch_nos), "item": ("!=", self.item_code)}, fields=["name"]
		)

		if incorrect_batch_nos:
			incorrect_batch_nos = ", ".join([d.name for d in incorrect_batch_nos])
			self.throw_error_message(
				f"Batch Nos {bold(incorrect_batch_nos)} does not belong to Item {bold(self.item_code)}"
			)

	def validate_serial_and_batch_no_for_returned(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if not self.returned_against:
			return

		if self.voucher_type not in [
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
		current_serial_nos = [d.serial_no for d in self.entries if d.serial_no]
		current_batches = [d.batch_no for d in self.entries if d.batch_no]

		for d in data:
			if self.has_serial_no:
				if d.serial_and_batch_bundle:
					serial_nos = get_serial_nos_from_bundle(d.serial_and_batch_bundle)
				else:
					serial_nos = get_serial_nos(d.serial_no)

			elif self.has_batch_no:
				if d.serial_and_batch_bundle:
					batches = get_batches_from_bundle(d.serial_and_batch_bundle)
				else:
					batches = frappe._dict({d.batch_no: d.stock_qty})

				if batches:
					batches = [d for d in batches if batches[d] > 0]

			if serial_nos:
				if not set(current_serial_nos).issubset(set(serial_nos)):
					self.throw_error_message(
						f"Serial Nos {bold(', '.join(serial_nos))} are not part of the original document."
					)

			if batches:
				if not set(current_batches).issubset(set(batches)):
					self.throw_error_message(
						f"Batch Nos {bold(', '.join(batches))} are not part of the original document."
					)

	def get_orignal_document_data(self):
		fields = ["serial_and_batch_bundle", "stock_qty"]
		if self.has_serial_no:
			fields.append("serial_no")

		elif self.has_batch_no:
			fields.append("batch_no")

		child_doc = self.voucher_type + " Item"
		return frappe.get_all(child_doc, fields=fields, filters={"name": self.returned_against})

	def validate_duplicate_serial_and_batch_no(self):
		serial_nos = []
		batch_nos = []

		for row in self.entries:
			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no and not row.serial_no:
				batch_nos.append(row.batch_no)

		if serial_nos:
			for key, value in collections.Counter(serial_nos).items():
				if value > 1:
					self.throw_error_message(f"Duplicate Serial No {key} found")

		if batch_nos:
			for key, value in collections.Counter(batch_nos).items():
				if value > 1:
					self.throw_error_message(f"Duplicate Batch No {key} found")

	def before_cancel(self):
		self.delink_serial_and_batch_bundle()

	def delink_serial_and_batch_bundle(self):
		sles = frappe.get_all("Stock Ledger Entry", filters={"serial_and_batch_bundle": self.name})

		for sle in sles:
			frappe.db.set_value("Stock Ledger Entry", sle.name, "serial_and_batch_bundle", None)

	@property
	def child_table(self):
		if self.voucher_type == "Job Card":
			return

		parent_child_map = {
			"Asset Capitalization": "Asset Capitalization Stock Item",
			"Asset Repair": "Asset Repair Consumed Item",
			"Quotation": "Packed Item",
			"Stock Entry": "Stock Entry Detail",
		}

		return (
			parent_child_map[self.voucher_type]
			if self.voucher_type in parent_child_map
			else f"{self.voucher_type} Item"
		)

	def delink_refernce_from_voucher(self):
		or_filters = {"serial_and_batch_bundle": self.name}

		fields = ["name", "serial_and_batch_bundle"]
		if self.voucher_type == "Stock Reconciliation":
			fields = ["name", "current_serial_and_batch_bundle", "serial_and_batch_bundle"]
			or_filters["current_serial_and_batch_bundle"] = self.name

		elif self.voucher_type == "Purchase Receipt":
			fields = ["name", "rejected_serial_and_batch_bundle", "serial_and_batch_bundle"]
			or_filters["rejected_serial_and_batch_bundle"] = self.name

		if (
			self.voucher_type == "Subcontracting Receipt"
			and self.voucher_detail_no
			and not frappe.db.exists("Subcontracting Receipt Item", self.voucher_detail_no)
		):
			self.voucher_type = "Subcontracting Receipt Supplied"

		vouchers = frappe.get_all(
			self.child_table,
			fields=fields,
			filters={"docstatus": 0},
			or_filters=or_filters,
		)

		if not vouchers and self.voucher_type == "Delivery Note":
			frappe.db.set_value("Packed Item", self.voucher_detail_no, "serial_and_batch_bundle", None)
			return

		for voucher in vouchers:
			if voucher.get("current_serial_and_batch_bundle"):
				frappe.db.set_value(self.child_table, voucher.name, "current_serial_and_batch_bundle", None)
			elif voucher.get("rejected_serial_and_batch_bundle"):
				frappe.db.set_value(self.child_table, voucher.name, "rejected_serial_and_batch_bundle", None)

			frappe.db.set_value(self.child_table, voucher.name, "serial_and_batch_bundle", None)

	def delink_reference_from_batch(self):
		batches = frappe.get_all(
			"Batch",
			fields=["name"],
			filters={"reference_name": self.name, "reference_doctype": "Serial and Batch Bundle"},
		)

		for batch in batches:
			frappe.db.set_value("Batch", batch.name, {"reference_name": None, "reference_doctype": None})

	def validate_serial_and_batch_data(self):
		if not self.voucher_no:
			frappe.throw(_("Voucher No is mandatory"))

	def before_submit(self):
		self.validate_serial_and_batch_data()
		self.validate_serial_and_batch_no_for_returned()
		self.set_purchase_document_no()

	def on_submit(self):
		self.validate_batch_inventory()
		self.validate_serial_nos_inventory()

	def set_purchase_document_no(self):
		if self.flags.ignore_validate_serial_batch:
			return

		if not self.has_serial_no:
			return

		if self.total_qty > 0:
			serial_nos = [d.serial_no for d in self.entries if d.serial_no]
			sn_table = frappe.qb.DocType("Serial No")
			(
				frappe.qb.update(sn_table)
				.set(
					sn_table.purchase_document_no,
					self.voucher_no if not sn_table.purchase_document_no else self.voucher_no,
				)
				.where(sn_table.name.isin(serial_nos))
			).run()

	def validate_serial_and_batch_inventory(self):
		self.check_future_entries_exists()
		self.validate_batch_inventory()

	def validate_batch_inventory(self):
		if (
			self.voucher_type in ["Purchase Invoice", "Purchase Receipt"]
			and frappe.db.get_value(self.voucher_type, self.voucher_no, "docstatus") == 1
		):
			return

		if self.voucher_type in ["Sales Invoice", "Delivery Note"] and self.type_of_transaction == "Inward":
			return

		if not self.has_batch_no:
			return

		if (
			self.voucher_type == "Stock Reconciliation"
			and self.type_of_transaction == "Outward"
			and frappe.db.get_value("Stock Reconciliation Item", self.voucher_detail_no, "qty") > 0
		):
			return

		batches = [d.batch_no for d in self.entries if d.batch_no]
		if not batches:
			return

		available_batches = get_auto_batch_nos(
			frappe._dict(
				{
					"item_code": self.item_code,
					"warehouse": self.warehouse,
					"batch_no": batches,
					"consider_negative_batches": True,
				}
			)
		)

		if not available_batches:
			return

		available_batches = get_available_batches_qty(available_batches)
		for batch_no in batches:
			if batch_no in available_batches and available_batches[batch_no] < 0:
				if flt(available_batches.get(batch_no)) < 0:
					self.validate_negative_batch(batch_no, available_batches[batch_no])

				self.throw_error_message(
					f"Batch {bold(batch_no)} is not available in the selected warehouse {self.warehouse}"
				)

	def on_cancel(self):
		self.validate_voucher_no_docstatus()

	def validate_voucher_no_docstatus(self):
		if self.voucher_type == "POS Invoice":
			return

		if frappe.db.get_value(self.voucher_type, self.voucher_no, "docstatus") == 1:
			msg = f"""The {self.voucher_type} {bold(self.voucher_no)}
				is in submitted state, please cancel it first"""
			frappe.throw(_(msg))

	def on_trash(self):
		self.validate_voucher_no_docstatus()
		self.delink_refernce_from_voucher()
		self.delink_reference_from_batch()

	@frappe.whitelist()
	def add_serial_batch(self, data):
		serial_nos, batch_nos = [], []
		if isinstance(data, str):
			data = parse_json(data)

		if data.get("csv_file"):
			serial_nos, batch_nos = get_serial_batch_from_csv(self.item_code, data.get("csv_file"))
		else:
			serial_nos, batch_nos = get_serial_batch_from_data(self.item_code, data)

		if not serial_nos and not batch_nos:
			return

		if serial_nos:
			self.set("entries", serial_nos)
		elif batch_nos:
			self.set("entries", batch_nos)

	def delete_serial_batch_entries(self):
		SBBE = frappe.qb.DocType("Serial and Batch Entry")

		frappe.qb.from_(SBBE).delete().where(SBBE.parent == self.name).run()

		self.set("entries", [])


@frappe.whitelist()
def download_blank_csv_template(content):
	csv_data = []
	if isinstance(content, str):
		content = parse_json(content)

	csv_data.append(content)
	csv_data.append([])
	csv_data.append([])

	filename = "serial_and_batch_bundle"
	build_csv_response(csv_data, filename)


@frappe.whitelist()
def upload_csv_file(item_code, file_path):
	serial_nos, batch_nos = [], []
	serial_nos, batch_nos = get_serial_batch_from_csv(item_code, file_path)

	return {
		"serial_nos": serial_nos,
		"batch_nos": batch_nos,
	}


def get_serial_batch_from_csv(item_code, file_path):
	if "private" in file_path:
		file_path = frappe.get_site_path() + file_path
	else:
		file_path = frappe.get_site_path() + "/public" + file_path

	serial_nos = []
	batch_nos = []

	with open(file_path) as f:
		reader = csv.reader(f)
		serial_nos, batch_nos = parse_csv_file_to_get_serial_batch(reader)

	if serial_nos:
		make_serial_nos(item_code, serial_nos)

	if batch_nos:
		make_batch_nos(item_code, batch_nos)

	return serial_nos, batch_nos


def parse_csv_file_to_get_serial_batch(reader):
	has_serial_no, has_batch_no = False, False
	serial_nos = []
	batch_nos = []

	for index, row in enumerate(reader):
		if index == 0:
			has_serial_no = row[0] == "Serial No"
			has_batch_no = row[0] == "Batch No"
			if not has_batch_no and len(row) > 1:
				has_batch_no = row[1] == "Batch No"

			continue

		if not row[0]:
			continue

		if has_serial_no or (has_serial_no and has_batch_no):
			_dict = {"serial_no": row[0].strip(), "qty": 1}

			if has_batch_no:
				_dict.update(
					{
						"batch_no": row[1].strip(),
						"qty": row[2],
					}
				)

				batch_nos.append(
					{
						"batch_no": row[1].strip(),
						"qty": row[2],
					}
				)

			serial_nos.append(_dict)
		elif has_batch_no:
			batch_nos.append(
				{
					"batch_no": row[0].strip(),
					"qty": row[1],
				}
			)

	return serial_nos, batch_nos


def get_serial_batch_from_data(item_code, kwargs):
	serial_nos = []
	batch_nos = []
	if kwargs.get("serial_nos"):
		data = parse_serial_nos(kwargs.get("serial_nos"))
		for serial_no in data:
			if not serial_no:
				continue
			serial_nos.append({"serial_no": serial_no, "qty": 1})

		make_serial_nos(item_code, serial_nos)

	if kwargs.get("_has_serial_nos"):
		return serial_nos

	return serial_nos, batch_nos


@frappe.whitelist()
def create_serial_nos(item_code, serial_nos):
	serial_nos = get_serial_batch_from_data(
		item_code,
		{
			"serial_nos": serial_nos,
			"_has_serial_nos": True,
		},
	)

	return serial_nos


def make_serial_nos(item_code, serial_nos):
	item = frappe.get_cached_value(
		"Item", item_code, ["description", "item_code", "item_name", "warranty_period"], as_dict=1
	)

	serial_nos = [d.get("serial_no").strip() for d in serial_nos if d.get("serial_no")]
	existing_serial_nos = frappe.get_all("Serial No", filters={"name": ("in", serial_nos)})

	existing_serial_nos = [d.get("name") for d in existing_serial_nos if d.get("name")]
	serial_nos = list(set(serial_nos) - set(existing_serial_nos))

	if not serial_nos:
		return

	serial_nos_details = []
	user = frappe.session.user
	for serial_no in serial_nos:
		serial_nos_details.append(
			(
				serial_no,
				serial_no,
				now(),
				now(),
				user,
				user,
				item.item_code,
				item.item_name,
				item.description,
				item.warranty_period or 0,
				"Inactive",
			)
		)

	fields = [
		"name",
		"serial_no",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"item_code",
		"item_name",
		"description",
		"warranty_period",
		"status",
	]

	frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

	frappe.msgprint(_("Serial Nos are created successfully"), alert=True)


def make_batch_nos(item_code, batch_nos):
	item = frappe.get_cached_value("Item", item_code, ["description", "item_code"], as_dict=1)
	batch_nos = [d.get("batch_no") for d in batch_nos if d.get("batch_no")]

	existing_batches = frappe.get_all("Batch", filters={"name": ("in", batch_nos)})

	existing_batches = [d.get("name") for d in existing_batches if d.get("name")]

	batch_nos = list(set(batch_nos) - set(existing_batches))
	if not batch_nos:
		return

	batch_nos_details = []
	user = frappe.session.user
	for batch_no in batch_nos:
		if frappe.db.exists("Batch", batch_no):
			continue

		batch_nos_details.append(
			(
				batch_no,
				batch_no,
				now(),
				now(),
				user,
				user,
				item.item_code,
				item.item_name,
				item.description,
				1,
			)
		)

	fields = [
		"name",
		"batch_id",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"item",
		"item_name",
		"description",
		"use_batchwise_valuation",
	]

	frappe.db.bulk_insert("Batch", fields=fields, values=set(batch_nos_details))

	frappe.msgprint(_("Batch Nos are created successfully"), alert=True)


def parse_serial_nos(data):
	if isinstance(data, list):
		return data

	return [s.strip() for s in cstr(data).strip().replace(",", "\n").split("\n") if s.strip()]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	item_filters = {"disabled": 0}
	if txt:
		item_filters["name"] = ("like", f"%{txt}%")

	return frappe.get_all(
		"Item",
		filters=item_filters,
		or_filters={"has_serial_no": 1, "has_batch_no": 1},
		fields=["name", "item_name"],
		as_list=1,
	)


@frappe.whitelist()
def get_serial_batch_ledgers(item_code=None, docstatus=None, voucher_no=None, name=None, child_row=None):
	filters = get_filters_for_bundle(
		item_code=item_code, docstatus=docstatus, voucher_no=voucher_no, name=name, child_row=child_row
	)

	fields = [
		"`tabSerial and Batch Bundle`.`item_code`",
		"`tabSerial and Batch Entry`.`qty`",
		"`tabSerial and Batch Entry`.`warehouse`",
		"`tabSerial and Batch Entry`.`batch_no`",
		"`tabSerial and Batch Entry`.`serial_no`",
		"`tabSerial and Batch Entry`.`name` as `child_row`",
	]

	if not child_row:
		fields.append("`tabSerial and Batch Bundle`.`name`")

	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=fields,
		filters=filters,
		order_by="`tabSerial and Batch Entry`.`idx`",
	)


def get_filters_for_bundle(item_code=None, docstatus=None, voucher_no=None, name=None, child_row=None):
	filters = [
		["Serial and Batch Bundle", "is_cancelled", "=", 0],
	]

	if child_row and isinstance(child_row, str):
		child_row = parse_json(child_row)

	if not name and child_row and child_row.get("qty") < 0:
		bundle = get_reference_serial_and_batch_bundle(child_row)
		if bundle:
			voucher_no = None
			filters.append(["Serial and Batch Bundle", "name", "=", bundle])

	if item_code:
		filters.append(["Serial and Batch Bundle", "item_code", "=", item_code])

	if not docstatus:
		docstatus = [0, 1]

	if isinstance(docstatus, list):
		filters.append(["Serial and Batch Bundle", "docstatus", "in", docstatus])
	else:
		filters.append(["Serial and Batch Bundle", "docstatus", "=", docstatus])

	if voucher_no:
		filters.append(["Serial and Batch Bundle", "voucher_no", "=", voucher_no])

	if name:
		if isinstance(name, list):
			filters.append(["Serial and Batch Entry", "parent", "in", name])
		else:
			filters.append(["Serial and Batch Entry", "parent", "=", name])

	return filters


def get_reference_serial_and_batch_bundle(child_row):
	field = {
		"Sales Invoice Item": "sales_invoice_item",
		"Delivery Note Item": "dn_detail",
		"Purchase Receipt Item": "purchase_receipt_item",
		"Purchase Invoice Item": "purchase_invoice_item",
		"POS Invoice Item": "pos_invoice_item",
	}.get(child_row.doctype)

	if field:
		return frappe.get_cached_value(child_row.doctype, child_row.get(field), "serial_and_batch_bundle")


@frappe.whitelist()
def add_serial_batch_ledgers(entries, child_row, doc, warehouse, do_not_save=False) -> object:
	if isinstance(child_row, str):
		child_row = frappe._dict(parse_json(child_row))

	if isinstance(entries, str):
		entries = parse_json(entries)

	parent_doc = doc
	if parent_doc and isinstance(parent_doc, str):
		parent_doc = parse_json(parent_doc)

	bundle = child_row.serial_and_batch_bundle
	if child_row.get("is_rejected"):
		bundle = child_row.rejected_serial_and_batch_bundle

	if frappe.db.exists("Serial and Batch Bundle", bundle):
		sb_doc = update_serial_batch_no_ledgers(bundle, entries, child_row, parent_doc, warehouse)
	else:
		sb_doc = create_serial_batch_no_ledgers(
			entries, child_row, parent_doc, warehouse, do_not_save=do_not_save
		)

	return sb_doc


def create_serial_batch_no_ledgers(
	entries, child_row, parent_doc, warehouse=None, do_not_save=False
) -> object:
	warehouse = warehouse or (child_row.rejected_warehouse if child_row.is_rejected else child_row.warehouse)

	type_of_transaction = get_type_of_transaction(parent_doc, child_row)
	if parent_doc.get("doctype") == "Stock Entry":
		warehouse = warehouse or child_row.s_warehouse or child_row.t_warehouse

	doc = frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"voucher_type": child_row.parenttype,
			"item_code": child_row.item_code,
			"warehouse": warehouse,
			"is_rejected": child_row.is_rejected,
			"type_of_transaction": type_of_transaction,
			"posting_date": parent_doc.get("posting_date"),
			"posting_time": parent_doc.get("posting_time"),
			"company": parent_doc.get("company"),
		}
	)

	batch_no = None

	if (
		not entries[0].get("batch_no")
		and entries[0].get("serial_no")
		and frappe.get_cached_value("Item", child_row.item_code, "has_batch_no")
	):
		batch_no = get_batch(child_row.item_code)

	for row in entries:
		row = frappe._dict(row)
		doc.append(
			"entries",
			{
				"qty": (flt(row.qty) or 1.0) * (1 if type_of_transaction == "Inward" else -1),
				"warehouse": warehouse,
				"batch_no": row.batch_no or batch_no,
				"serial_no": row.serial_no,
			},
		)

	doc.save()

	if do_not_save:
		frappe.db.set_value(child_row.doctype, child_row.name, "serial_and_batch_bundle", doc.name)

	frappe.msgprint(_("Serial and Batch Bundle created"), alert=True)

	return doc


def get_batch(item_code):
	from erpnext.stock.doctype.batch.batch import make_batch

	return make_batch(
		frappe._dict(
			{
				"item": item_code,
			}
		)
	)


def get_type_of_transaction(parent_doc, child_row):
	type_of_transaction = child_row.get("type_of_transaction")
	if parent_doc.get("doctype") == "Stock Entry":
		type_of_transaction = "Outward" if child_row.s_warehouse else "Inward"

	if not type_of_transaction:
		type_of_transaction = "Outward"
		if parent_doc.get("doctype") in ["Purchase Receipt", "Purchase Invoice"]:
			type_of_transaction = "Inward"

	if parent_doc.get("doctype") == "Subcontracting Receipt":
		type_of_transaction = "Outward"
		if child_row.get("doctype") == "Subcontracting Receipt Item":
			type_of_transaction = "Inward"
	elif parent_doc.get("doctype") == "Stock Reconciliation":
		type_of_transaction = "Inward"

	if parent_doc.get("is_return"):
		type_of_transaction = "Inward"
		if (
			parent_doc.get("doctype") in ["Purchase Receipt", "Purchase Invoice"]
			or child_row.get("doctype") == "Subcontracting Receipt Item"
		):
			type_of_transaction = "Outward"

	return type_of_transaction


def update_serial_batch_no_ledgers(bundle, entries, child_row, parent_doc, warehouse=None) -> object:
	doc = frappe.get_doc("Serial and Batch Bundle", bundle)
	doc.voucher_detail_no = child_row.name
	doc.posting_date = parent_doc.posting_date
	doc.posting_time = parent_doc.posting_time
	doc.warehouse = warehouse or doc.warehouse
	doc.set("entries", [])

	for d in entries:
		doc.append(
			"entries",
			{
				"qty": (flt(d.get("qty")) or 1.0) * (1 if doc.type_of_transaction == "Inward" else -1),
				"warehouse": warehouse or d.get("warehouse"),
				"batch_no": d.get("batch_no"),
				"serial_no": d.get("serial_no"),
			},
		)

	doc.save(ignore_permissions=True)

	frappe.msgprint(_("Serial and Batch Bundle updated"), alert=True)

	return doc


@frappe.whitelist()
def update_serial_or_batch(bundle_id, serial_no=None, batch_no=None):
	if batch_no and not serial_no:
		if qty := frappe.db.get_value(
			"Serial and Batch Entry", {"parent": bundle_id, "batch_no": batch_no}, "qty"
		):
			frappe.db.set_value(
				"Serial and Batch Entry", {"parent": bundle_id, "batch_no": batch_no}, "qty", qty + 1
			)
			return

	doc = frappe.get_cached_doc("Serial and Batch Bundle", bundle_id)
	if not serial_no and not batch_no:
		return

	doc.append("entries", {"serial_no": serial_no, "batch_no": batch_no, "qty": 1})
	doc.save(ignore_permissions=True)


def get_serial_and_batch_ledger(**kwargs):
	kwargs = frappe._dict(kwargs)

	sle_table = frappe.qb.DocType("Stock Ledger Entry")
	serial_batch_table = frappe.qb.DocType("Serial and Batch Entry")

	query = (
		frappe.qb.from_(sle_table)
		.inner_join(serial_batch_table)
		.on(sle_table.serial_and_batch_bundle == serial_batch_table.parent)
		.select(
			serial_batch_table.serial_no,
			serial_batch_table.warehouse,
			serial_batch_table.batch_no,
			serial_batch_table.qty,
			serial_batch_table.incoming_rate,
			serial_batch_table.voucher_detail_no,
		)
		.where(
			(sle_table.item_code == kwargs.item_code)
			& (sle_table.warehouse == kwargs.warehouse)
			& (serial_batch_table.is_outward == 0)
		)
	)

	if kwargs.serial_nos:
		query = query.where(serial_batch_table.serial_no.isin(kwargs.serial_nos))

	if kwargs.batch_nos:
		query = query.where(serial_batch_table.batch_no.isin(kwargs.batch_nos))

	if kwargs.fetch_incoming_rate:
		query = query.where(sle_table.actual_qty > 0)

	return query.run(as_dict=True)


@frappe.whitelist()
def get_auto_data(**kwargs):
	kwargs = frappe._dict(kwargs)
	if cint(kwargs.has_serial_no):
		return get_available_serial_nos(kwargs)

	elif cint(kwargs.has_batch_no):
		return get_auto_batch_nos(kwargs)


def get_available_batches_qty(available_batches):
	available_batches_qty = defaultdict(float)
	for batch in available_batches:
		available_batches_qty[batch.batch_no] += batch.qty

	return available_batches_qty


def get_available_serial_nos(kwargs):
	fields = ["name as serial_no", "warehouse"]
	if kwargs.has_batch_no:
		fields.append("batch_no")

	order_by = "creation"
	if kwargs.based_on == "LIFO":
		order_by = "creation desc"
	elif kwargs.based_on == "Expiry":
		order_by = "amc_expiry_date asc"

	filters = {"item_code": kwargs.item_code}

	# ignore_warehouse is used for backdated stock transactions
	# There might be chances that the serial no not exists in the warehouse during backdated stock transactions
	if not kwargs.get("ignore_warehouse"):
		filters["warehouse"] = ("is", "set")
		if kwargs.warehouse:
			filters["warehouse"] = kwargs.warehouse

	# Since SLEs are not present against Reserved Stock [POS invoices, SRE], need to ignore reserved serial nos.
	ignore_serial_nos = get_reserved_serial_nos(kwargs)

	# To ignore serial nos in the same record for the draft state
	if kwargs.get("ignore_serial_nos"):
		ignore_serial_nos.extend(kwargs.get("ignore_serial_nos"))

	if kwargs.get("posting_date"):
		if kwargs.get("posting_time") is None:
			kwargs.posting_time = nowtime()

		time_based_serial_nos = get_serial_nos_based_on_posting_date(kwargs, ignore_serial_nos)

		if not time_based_serial_nos:
			return []

		filters["name"] = ("in", time_based_serial_nos)
	elif ignore_serial_nos:
		filters["name"] = ("not in", ignore_serial_nos)

	if kwargs.get("batches"):
		batches = get_non_expired_batches(kwargs.get("batches"))
		if not batches:
			return []

		filters["batch_no"] = ("in", batches)

	return frappe.get_all(
		"Serial No",
		fields=fields,
		filters=filters,
		limit=cint(kwargs.qty) or 10000000,
		order_by=order_by,
	)


def get_non_expired_batches(batches):
	filters = {}
	if isinstance(batches, list):
		filters["name"] = ("in", batches)
	else:
		filters["name"] = batches

	data = frappe.get_all(
		"Batch",
		filters=filters,
		or_filters=[["expiry_date", ">=", today()], ["expiry_date", "is", "not set"]],
		fields=["name"],
	)

	return [d.name for d in data] if data else []


def get_serial_nos_based_on_posting_date(kwargs, ignore_serial_nos):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	serial_nos = set()
	data = get_stock_ledgers_for_serial_nos(kwargs)

	bundle_wise_serial_nos = get_bundle_wise_serial_nos(data, kwargs)
	for d in data:
		if d.serial_and_batch_bundle:
			if sns := bundle_wise_serial_nos.get(d.serial_and_batch_bundle):
				if d.actual_qty > 0:
					serial_nos.update(sns)
				else:
					serial_nos.difference_update(sns)

		elif d.serial_no:
			sns = get_serial_nos(d.serial_no)
			if d.actual_qty > 0:
				serial_nos.update(sns)
			else:
				serial_nos.difference_update(sns)

	serial_nos = list(serial_nos)
	for serial_no in ignore_serial_nos:
		if serial_no in serial_nos:
			serial_nos.remove(serial_no)

	return serial_nos


def get_bundle_wise_serial_nos(data, kwargs):
	bundle_wise_serial_nos = defaultdict(list)
	bundles = [d.serial_and_batch_bundle for d in data if d.serial_and_batch_bundle]
	if not bundles:
		return bundle_wise_serial_nos

	filters = {"parent": ("in", bundles), "docstatus": 1, "serial_no": ("is", "set")}

	if kwargs.get("check_serial_nos") and kwargs.get("serial_nos"):
		filters["serial_no"] = ("in", kwargs.get("serial_nos"))

	bundle_data = frappe.get_all(
		"Serial and Batch Entry",
		fields=["serial_no", "parent"],
		filters=filters,
	)

	for d in bundle_data:
		if d.parent:
			bundle_wise_serial_nos[d.parent].append(d.serial_no)

	return bundle_wise_serial_nos


def get_reserved_serial_nos(kwargs) -> list:
	"""Returns a list of `Serial No` reserved in POS Invoice and Stock Reservation Entry."""

	ignore_serial_nos = []

	# Extend the list by serial nos reserved in POS Invoice
	ignore_serial_nos.extend(get_reserved_serial_nos_for_pos(kwargs))

	# Extend the list by serial nos reserved via SRE
	ignore_serial_nos.extend(get_reserved_serial_nos_for_sre(kwargs))

	return ignore_serial_nos


def get_reserved_serial_nos_for_pos(kwargs):
	from erpnext.controllers.sales_and_purchase_return import get_returned_serial_nos
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	ignore_serial_nos = []
	pos_invoices = frappe.get_all(
		"POS Invoice",
		fields=[
			"`tabPOS Invoice Item`.serial_no",
			"`tabPOS Invoice`.is_return",
			"`tabPOS Invoice Item`.name as child_docname",
			"`tabPOS Invoice`.name as parent_docname",
			"`tabPOS Invoice Item`.serial_and_batch_bundle",
		],
		filters=[
			["POS Invoice", "consolidated_invoice", "is", "not set"],
			["POS Invoice", "docstatus", "=", 1],
			["POS Invoice", "is_return", "=", 0],
			["POS Invoice Item", "item_code", "=", kwargs.item_code],
			["POS Invoice", "name", "not in", kwargs.ignore_voucher_nos],
		],
	)

	ids = [
		pos_invoice.serial_and_batch_bundle
		for pos_invoice in pos_invoices
		if pos_invoice.serial_and_batch_bundle
	]

	if not ids:
		return []

	for d in get_serial_batch_ledgers(kwargs.item_code, docstatus=1, name=ids):
		ignore_serial_nos.append(d.serial_no)

	returned_serial_nos = []
	for pos_invoice in pos_invoices:
		if pos_invoice.serial_no:
			ignore_serial_nos.extend(get_serial_nos(pos_invoice.serial_no))

		if pos_invoice.is_return:
			continue

		child_doc = _dict(
			{
				"doctype": "POS Invoice Item",
				"name": pos_invoice.child_docname,
			}
		)

		parent_doc = _dict(
			{
				"doctype": "POS Invoice",
				"name": pos_invoice.parent_docname,
			}
		)

		returned_serial_nos.extend(
			get_returned_serial_nos(
				child_doc, parent_doc, ignore_voucher_detail_no=kwargs.get("ignore_voucher_detail_no")
			)
		)
	# Counter is used to create a hashmap of serial nos, which contains count of each serial no
	# so we subtract returned serial nos from ignore serial nos after creating a counter of each to get the items which we need 	to ignore(which are sold)

	ignore_serial_nos_counter = Counter(ignore_serial_nos)
	returned_serial_nos_counter = Counter(returned_serial_nos)

	return list(ignore_serial_nos_counter - returned_serial_nos_counter)


def get_reserved_serial_nos_for_sre(kwargs) -> list:
	"""Returns a list of `Serial No` reserved in Stock Reservation Entry."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(sb_entry.serial_no)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == kwargs.item_code)
			& (sre.reserved_qty >= sre.delivered_qty)
			& (sre.status.notin(["Delivered", "Cancelled"]))
			& (sre.reservation_based_on == "Serial and Batch")
		)
	)

	if kwargs.warehouse:
		query = query.where(sre.warehouse == kwargs.warehouse)

	if kwargs.ignore_voucher_nos:
		query = query.where(sre.name.notin(kwargs.ignore_voucher_nos))

	return [row[0] for row in query.run()]


def get_reserved_batches_for_pos(kwargs) -> dict:
	"""Returns a dict of `Batch No` followed by the `Qty` reserved in POS Invoices."""

	pos_batches = frappe._dict()
	pos_invoices = frappe.get_all(
		"POS Invoice",
		fields=[
			"`tabPOS Invoice Item`.batch_no",
			"`tabPOS Invoice Item`.qty",
			"`tabPOS Invoice`.is_return",
			"`tabPOS Invoice Item`.warehouse",
			"`tabPOS Invoice Item`.name as child_docname",
			"`tabPOS Invoice`.name as parent_docname",
			"`tabPOS Invoice Item`.use_serial_batch_fields",
			"`tabPOS Invoice Item`.serial_and_batch_bundle",
		],
		filters=[
			["POS Invoice", "consolidated_invoice", "is", "not set"],
			["POS Invoice", "docstatus", "=", 1],
			["POS Invoice Item", "item_code", "=", kwargs.item_code],
			["POS Invoice", "name", "not in", kwargs.ignore_voucher_nos],
		],
	)

	ids = [
		pos_invoice.serial_and_batch_bundle
		for pos_invoice in pos_invoices
		if pos_invoice.serial_and_batch_bundle and not pos_invoice.use_serial_batch_fields
	]

	if ids:
		for d in get_serial_batch_ledgers(kwargs.item_code, docstatus=1, name=ids):
			key = (d.batch_no, d.warehouse)
			if key not in pos_batches:
				pos_batches[key] = frappe._dict(
					{
						"qty": d.qty,
						"warehouse": d.warehouse,
					}
				)
			else:
				pos_batches[key].qty += d.qty

	# POS invoices having batch without bundle (to handle old POS invoices)
	for row in pos_invoices:
		if not row.batch_no:
			continue

		if kwargs.get("batch_no") and row.batch_no != kwargs.get("batch_no"):
			continue

		key = (row.batch_no, row.warehouse)
		if key in pos_batches:
			pos_batches[key]["qty"] -= row.qty * -1 if row.is_return else row.qty
		else:
			pos_batches[key] = frappe._dict(
				{
					"qty": (row.qty * -1 if not row.is_return else row.qty),
					"warehouse": row.warehouse,
				}
			)

	return pos_batches


def get_reserved_batches_for_sre(kwargs) -> dict:
	"""Returns a dict of `Batch No` followed by the `Qty` reserved in Stock Reservation Entry."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(
			sb_entry.batch_no, sre.warehouse, (-1 * Sum(sb_entry.qty - sb_entry.delivered_qty)).as_("qty")
		)
		.where(
			(sre.docstatus == 1)
			& (sre.item_code == kwargs.item_code)
			& (sre.reserved_qty >= sre.delivered_qty)
			& (sre.status.notin(["Delivered", "Cancelled"]))
			& (sre.reservation_based_on == "Serial and Batch")
		)
		.groupby(sb_entry.batch_no, sre.warehouse)
	)

	if kwargs.batch_no:
		if isinstance(kwargs.batch_no, list):
			query = query.where(sb_entry.batch_no.isin(kwargs.batch_no))
		else:
			query = query.where(sb_entry.batch_no == kwargs.batch_no)

	if kwargs.warehouse:
		if isinstance(kwargs.warehouse, list):
			query = query.where(sre.warehouse.isin(kwargs.warehouse))
		else:
			query = query.where(sre.warehouse == kwargs.warehouse)

	if kwargs.ignore_voucher_nos:
		query = query.where(sre.name.notin(kwargs.ignore_voucher_nos))

	data = query.run(as_dict=True)

	reserved_batches_details = frappe._dict()
	if data:
		reserved_batches_details = frappe._dict(
			{(d.batch_no, d.warehouse): frappe._dict({"warehouse": d.warehouse, "qty": d.qty}) for d in data}
		)

	return reserved_batches_details


def get_auto_batch_nos(kwargs):
	available_batches = get_available_batches(kwargs)
	qty = flt(kwargs.qty)

	stock_ledgers_batches = get_stock_ledgers_batches(kwargs)
	pos_invoice_batches = get_reserved_batches_for_pos(kwargs)
	sre_reserved_batches = get_reserved_batches_for_sre(kwargs)
	picked_batches = frappe._dict()
	if kwargs.get("is_pick_list"):
		picked_batches = get_picked_batches(kwargs)

	if stock_ledgers_batches or pos_invoice_batches or sre_reserved_batches or picked_batches:
		update_available_batches(
			available_batches,
			stock_ledgers_batches,
			pos_invoice_batches,
			sre_reserved_batches,
			picked_batches,
		)

	if not kwargs.consider_negative_batches:
		available_batches = list(filter(lambda x: x.qty > 0, available_batches))

	if not qty:
		return available_batches

	return get_qty_based_available_batches(available_batches, qty)


def get_qty_based_available_batches(available_batches, qty):
	batches = []
	for batch in available_batches:
		if qty <= 0:
			break

		batch_qty = flt(batch.qty)
		if qty > batch_qty:
			batches.append(
				frappe._dict(
					{
						"batch_no": batch.batch_no,
						"qty": batch_qty,
						"warehouse": batch.warehouse,
					}
				)
			)
			qty -= batch_qty
		else:
			batches.append(
				frappe._dict(
					{
						"batch_no": batch.batch_no,
						"qty": qty,
						"warehouse": batch.warehouse,
					}
				)
			)
			qty = 0

	return batches


def update_available_batches(available_batches, *reserved_batches) -> None:
	for batches in reserved_batches:
		if batches:
			for key, data in batches.items():
				batch_no, warehouse = key
				batch_not_exists = True
				for batch in available_batches:
					if batch.batch_no == batch_no and batch.warehouse == warehouse:
						batch.qty += data.qty
						batch_not_exists = False

				if batch_not_exists:
					available_batches.append(data)


def get_available_batches(kwargs):
	from erpnext.stock.utils import get_combine_datetime

	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_ledger = frappe.qb.DocType("Serial and Batch Entry")
	batch_table = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.inner_join(batch_ledger)
		.on(stock_ledger_entry.serial_and_batch_bundle == batch_ledger.parent)
		.inner_join(batch_table)
		.on(batch_ledger.batch_no == batch_table.name)
		.select(
			batch_ledger.batch_no,
			batch_ledger.warehouse,
			Sum(batch_ledger.qty).as_("qty"),
		)
		.where(batch_table.disabled == 0)
		.where(stock_ledger_entry.is_cancelled == 0)
		.groupby(batch_ledger.batch_no, batch_ledger.warehouse)
	)

	if not kwargs.get("for_stock_levels"):
		query = query.where((batch_table.expiry_date >= today()) | (batch_table.expiry_date.isnull()))

	if kwargs.get("posting_date"):
		if kwargs.get("posting_time") is None:
			kwargs.posting_time = nowtime()

		timestamp_condition = stock_ledger_entry.posting_datetime <= get_combine_datetime(
			kwargs.posting_date, kwargs.posting_time
		)

		query = query.where(timestamp_condition)

	for field in ["warehouse", "item_code"]:
		if not kwargs.get(field):
			continue

		if isinstance(kwargs.get(field), list):
			query = query.where(stock_ledger_entry[field].isin(kwargs.get(field)))
		else:
			query = query.where(stock_ledger_entry[field] == kwargs.get(field))

	if kwargs.get("batch_no"):
		if isinstance(kwargs.batch_no, list):
			query = query.where(batch_ledger.batch_no.isin(kwargs.batch_no))
		else:
			query = query.where(batch_ledger.batch_no == kwargs.batch_no)

	if kwargs.based_on == "LIFO":
		query = query.orderby(batch_table.creation, order=frappe.qb.desc)
	elif kwargs.based_on == "Expiry":
		query = query.orderby(batch_table.expiry_date)
	else:
		query = query.orderby(batch_table.creation)

	if kwargs.get("ignore_voucher_nos"):
		query = query.where(stock_ledger_entry.voucher_no.notin(kwargs.get("ignore_voucher_nos")))

	data = query.run(as_dict=True)

	return data


# For work order and subcontracting
def get_voucher_wise_serial_batch_from_bundle(**kwargs) -> dict[str, dict]:
	data = get_ledgers_from_serial_batch_bundle(**kwargs)
	if not data:
		return {}

	group_by_voucher = {}

	for row in data:
		key = (row.item_code, row.warehouse, row.voucher_no)
		if kwargs.get("get_subcontracted_item"):
			# get_subcontracted_item = ("doctype", "field_name")
			doctype, field_name = kwargs.get("get_subcontracted_item")

			subcontracted_item_code = frappe.get_cached_value(doctype, row.voucher_detail_no, field_name)
			key = (row.item_code, subcontracted_item_code, row.warehouse, row.voucher_no)

		if key not in group_by_voucher:
			group_by_voucher.setdefault(
				key,
				frappe._dict({"serial_nos": [], "batch_nos": defaultdict(float), "item_row": row}),
			)

		child_row = group_by_voucher[key]
		if row.serial_no:
			child_row["serial_nos"].append(row.serial_no)

		if row.batch_no:
			child_row["batch_nos"][row.batch_no] += row.qty

	return group_by_voucher


def get_picked_batches(kwargs) -> dict[str, dict]:
	picked_batches = frappe._dict()

	table = frappe.qb.DocType("Serial and Batch Bundle")
	child_table = frappe.qb.DocType("Serial and Batch Entry")
	pick_list_table = frappe.qb.DocType("Pick List")

	query = (
		frappe.qb.from_(table)
		.inner_join(child_table)
		.on(table.name == child_table.parent)
		.inner_join(pick_list_table)
		.on(table.voucher_no == pick_list_table.name)
		.select(
			child_table.batch_no,
			child_table.warehouse,
			Sum(child_table.qty).as_("qty"),
		)
		.where(
			(table.docstatus != 2)
			& (pick_list_table.status != "Completed")
			& (table.type_of_transaction == "Outward")
			& (table.is_cancelled == 0)
			& (table.voucher_type == "Pick List")
			& (table.voucher_no.isnotnull())
		)
	)

	if kwargs.get("item_code"):
		query = query.where(table.item_code == kwargs.get("item_code"))

	if kwargs.get("warehouse"):
		if isinstance(kwargs.warehouse, list):
			query = query.where(table.warehouse.isin(kwargs.warehouse))
		else:
			query = query.where(table.warehouse == kwargs.get("warehouse"))

	data = query.run(as_dict=True)
	for row in data:
		if not row.qty:
			continue

		key = (row.batch_no, row.warehouse)
		if key not in picked_batches:
			picked_batches[key] = frappe._dict(
				{
					"qty": row.qty,
					"warehouse": row.warehouse,
				}
			)
		else:
			picked_batches[key].qty += row.qty

	return picked_batches


def get_picked_serial_nos(item_code, warehouse=None) -> list[str]:
	table = frappe.qb.DocType("Serial and Batch Bundle")
	child_table = frappe.qb.DocType("Serial and Batch Entry")
	pick_list_table = frappe.qb.DocType("Pick List")

	query = (
		frappe.qb.from_(table)
		.inner_join(child_table)
		.on(table.name == child_table.parent)
		.inner_join(pick_list_table)
		.on(table.voucher_no == pick_list_table.name)
		.select(
			child_table.serial_no,
		)
		.where(
			(table.docstatus != 2)
			& (pick_list_table.status != "Completed")
			& (table.type_of_transaction == "Outward")
			& (table.is_cancelled == 0)
			& (table.voucher_type == "Pick List")
			& (table.voucher_no.isnotnull())
		)
	)

	if item_code:
		query = query.where(table.item_code == item_code)

	if warehouse:
		if isinstance(warehouse, list):
			query = query.where(table.warehouse.isin(warehouse))
		else:
			query = query.where(table.warehouse == warehouse)

	data = query.run(as_dict=True)
	if not data:
		return []

	return [row.serial_no for row in data if row.serial_no]


def get_ledgers_from_serial_batch_bundle(**kwargs) -> list[frappe._dict]:
	bundle_table = frappe.qb.DocType("Serial and Batch Bundle")
	serial_batch_table = frappe.qb.DocType("Serial and Batch Entry")

	query = (
		frappe.qb.from_(bundle_table)
		.inner_join(serial_batch_table)
		.on(bundle_table.name == serial_batch_table.parent)
		.select(
			serial_batch_table.serial_no,
			bundle_table.warehouse,
			bundle_table.item_code,
			serial_batch_table.batch_no,
			serial_batch_table.qty,
			serial_batch_table.incoming_rate,
			bundle_table.voucher_detail_no,
			bundle_table.voucher_no,
			bundle_table.posting_date,
			bundle_table.posting_time,
		)
		.where(
			(bundle_table.docstatus == 1)
			& (bundle_table.is_cancelled == 0)
			& (bundle_table.type_of_transaction.isin(["Inward", "Outward"]))
		)
		.orderby(bundle_table.posting_date, bundle_table.posting_time)
	)

	for key, val in kwargs.items():
		if val is None:
			continue

		if not val and isinstance(val, list):
			return []

		if key == "get_subcontracted_item":
			continue

		if key in ["name", "item_code", "warehouse", "voucher_no", "company", "voucher_detail_no"]:
			if isinstance(val, list):
				query = query.where(bundle_table[key].isin(val))
			else:
				query = query.where(bundle_table[key] == val)
		elif key in ["posting_date", "posting_time"]:
			query = query.where(bundle_table[key] >= val)
		else:
			if isinstance(val, list):
				query = query.where(serial_batch_table[key].isin(val))
			else:
				query = query.where(serial_batch_table[key] == val)

	return query.run(as_dict=True)


def get_stock_ledgers_for_serial_nos(kwargs):
	from erpnext.stock.utils import get_combine_datetime

	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.select(
			stock_ledger_entry.actual_qty,
			stock_ledger_entry.serial_no,
			stock_ledger_entry.serial_and_batch_bundle,
		)
		.where(stock_ledger_entry.is_cancelled == 0)
		.orderby(stock_ledger_entry.posting_datetime)
	)

	if kwargs.get("posting_date"):
		if kwargs.get("posting_time") is None:
			kwargs.posting_time = nowtime()

		timestamp_condition = stock_ledger_entry.posting_datetime <= get_combine_datetime(
			kwargs.posting_date, kwargs.posting_time
		)

		query = query.where(timestamp_condition)

	for field in ["warehouse", "item_code", "serial_no"]:
		if not kwargs.get(field):
			continue

		if isinstance(kwargs.get(field), list):
			query = query.where(stock_ledger_entry[field].isin(kwargs.get(field)))
		else:
			query = query.where(stock_ledger_entry[field] == kwargs.get(field))

	if kwargs.voucher_no:
		query = query.where(stock_ledger_entry.voucher_no != kwargs.voucher_no)

	return query.run(as_dict=True)


def get_stock_ledgers_batches(kwargs):
	from erpnext.stock.utils import get_combine_datetime

	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_table = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.inner_join(batch_table)
		.on(stock_ledger_entry.batch_no == batch_table.name)
		.select(
			stock_ledger_entry.warehouse,
			stock_ledger_entry.item_code,
			Sum(stock_ledger_entry.actual_qty).as_("qty"),
			stock_ledger_entry.batch_no,
		)
		.where((stock_ledger_entry.is_cancelled == 0) & (stock_ledger_entry.batch_no.isnotnull()))
		.groupby(stock_ledger_entry.batch_no, stock_ledger_entry.warehouse)
	)

	for field in ["warehouse", "item_code", "batch_no"]:
		if not kwargs.get(field):
			continue

		if isinstance(kwargs.get(field), list):
			query = query.where(stock_ledger_entry[field].isin(kwargs.get(field)))
		else:
			query = query.where(stock_ledger_entry[field] == kwargs.get(field))

	if kwargs.get("posting_date"):
		if kwargs.get("posting_time") is None:
			kwargs.posting_time = nowtime()

		timestamp_condition = stock_ledger_entry.posting_datetime <= get_combine_datetime(
			kwargs.posting_date, kwargs.posting_time
		)

		query = query.where(timestamp_condition)

	if kwargs.get("ignore_voucher_nos"):
		query = query.where(stock_ledger_entry.voucher_no.notin(kwargs.get("ignore_voucher_nos")))

	if kwargs.based_on == "LIFO":
		query = query.orderby(batch_table.creation, order=frappe.qb.desc)
	elif kwargs.based_on == "Expiry":
		query = query.orderby(batch_table.expiry_date)
	else:
		query = query.orderby(batch_table.creation)

	data = query.run(as_dict=True)
	batches = {}
	for d in data:
		key = (d.batch_no, d.warehouse)
		if key not in batches:
			batches[key] = d
		else:
			batches[key].qty += d.qty

	return batches


@frappe.whitelist()
def get_batch_no_from_serial_no(serial_no):
	return frappe.get_cached_value("Serial No", serial_no, "batch_no")


@frappe.whitelist()
def is_serial_batch_no_exists(item_code, type_of_transaction, serial_no=None, batch_no=None):
	if serial_no and not frappe.db.exists("Serial No", serial_no):
		if type_of_transaction != "Inward":
			frappe.throw(_("Serial No {0} does not exists").format(serial_no))

		make_serial_no(serial_no, item_code)

	if batch_no and not frappe.db.exists("Batch", batch_no):
		if type_of_transaction != "Inward":
			frappe.throw(_("Batch No {0} does not exists").format(batch_no))

		make_batch_no(batch_no, item_code)


def make_serial_no(serial_no, item_code):
	serial_no_doc = frappe.new_doc("Serial No")
	serial_no_doc.serial_no = serial_no
	serial_no_doc.item_code = item_code
	serial_no_doc.save(ignore_permissions=True)


def make_batch_no(batch_no, item_code):
	batch_doc = frappe.new_doc("Batch")
	batch_doc.batch_id = batch_no
	batch_doc.item = item_code
	batch_doc.save(ignore_permissions=True)


@frappe.whitelist()
def is_duplicate_serial_no(bundle_id, serial_no):
	return frappe.db.exists("Serial and Batch Entry", {"parent": bundle_id, "serial_no": serial_no})
