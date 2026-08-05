# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Serial / batch composition handling for stock transactions.

Extracted from ``StockController``. Owns creation, validation and teardown of
serial/batch Stock Location Ledger entries for a stock voucher. The controller
keeps thin delegators for methods reached from other doctypes / ``run_method``;
internal helpers live here only.
"""

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate

from erpnext.controllers.sales_and_purchase_return import (
	available_serial_batch_for_return,
	filter_serial_batches,
	make_serial_batch_bundle_for_return,
)
from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.serial_batch_bundle import combine_datetime, get_type_of_transaction


class SerialBatchBundleService:
	def __init__(self, doc) -> None:
		self.doc = doc

	def validate_serialized_batch(self):
		from erpnext.exceptions import BatchExpiredError
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		is_material_issue = False
		if self.doc.doctype == "Stock Entry" and self.doc.purpose in ["Material Issue", "Material Transfer"]:
			is_material_issue = True

		for d in self.doc.get("items"):
			if hasattr(d, "serial_no") and hasattr(d, "batch_no") and d.serial_no and d.batch_no:
				serial_nos = frappe.get_all(
					"Serial No",
					fields=["batch_no", "name", "warehouse"],
					filters={"name": ("in", get_serial_nos(d.serial_no))},
				)

				for row in serial_nos:
					if row.warehouse and row.batch_no != d.batch_no:
						frappe.throw(
							_("Row #{0}: Serial No {1} does not belong to Batch {2}").format(
								d.idx, row.name, d.batch_no
							)
						)

			if is_material_issue:
				continue

			if (
				flt(d.qty) > 0.0
				and d.get("batch_no")
				and self.doc.get("posting_date")
				and self.doc.docstatus < 2
			):
				expiry_date = frappe.get_cached_value("Batch", d.get("batch_no"), "expiry_date")

				if expiry_date and getdate(expiry_date) < getdate(self.doc.posting_date):
					frappe.throw(
						_("Row #{0}: The batch {1} has already expired.").format(
							d.idx, get_link_to_form("Batch", d.get("batch_no"))
						),
						BatchExpiredError,
					)

	def clean_serial_nos(self):
		from erpnext.stock.doctype.serial_no.serial_no import clean_serial_no_string

		for row in self.doc.get("items"):
			if hasattr(row, "serial_no") and row.serial_no:
				# remove extra whitespace and store one serial no on each line
				row.serial_no = clean_serial_no_string(row.serial_no)

		for row in self.doc.get("packed_items") or []:
			if hasattr(row, "serial_no") and row.serial_no:
				# remove extra whitespace and store one serial no on each line
				row.serial_no = clean_serial_no_string(row.serial_no)

	def make_bundle_using_old_serial_batch_fields(self, table_name=None, via_landed_cost_voucher=False):
		if self.doc.get("_action") == "update_after_submit":
			return

		# To handle test cases
		if frappe.in_test and frappe.flags.use_serial_and_batch_fields:
			return

		if not table_name:
			table_name = "items"

		if self.doc.doctype == "Asset Capitalization":
			table_name = "stock_items"

		parent_details = frappe._dict()
		if table_name == "packed_items":
			parent_details = self.get_parent_details_for_packed_items()

		for row in self.doc.get(table_name):
			item_code = row.get("rm_item_code") or row.get("item_code")
			if not item_code or not self.is_serial_batch_item(item_code):
				continue

			if not row.serial_no and not row.batch_no and not row.get("rejected_serial_no"):
				self.apply_reserved_serial_batch(row, table_name)
				continue

			if not row.use_serial_batch_fields and (
				row.serial_no or row.batch_no or row.get("rejected_serial_no")
			):
				row.use_serial_batch_fields = 1

			if row.use_serial_batch_fields:
				bundle_details = {
					"item_code": row.get("rm_item_code") or row.item_code,
					"posting_datetime": combine_datetime(self.doc.posting_date, self.doc.posting_time),
					"voucher_type": self.doc.doctype,
					"voucher_no": self.doc.name,
					"voucher_detail_no": row.name,
					"company": self.doc.company,
					"is_rejected": 1 if row.get("rejected_warehouse") else 0,
					"use_serial_batch_fields": row.use_serial_batch_fields,
					"via_landed_cost_voucher": via_landed_cost_voucher,
					"do_not_submit": True if not via_landed_cost_voucher else False,
				}

				if self.doc.doctype == "Stock Reconciliation":
					# The reversal leg shares this voucher tuple and is written separately by
					# make_bundle_for_current_qty - scope the refresh to the new-state leg so it
					# isn't wiped along with it.
					bundle_details["ledger_is_outward"] = 0

				if self.doc.is_internal_transfer() and row.get("from_warehouse") and not self.doc.is_return:
					self.update_bundle_details(bundle_details, table_name, row)
					bundle_details["type_of_transaction"] = "Outward"
					bundle_details["warehouse"] = row.get("from_warehouse")
					bundle_details["qty"] = row.get("stock_qty") or row.get("qty")
					self.create_serial_batch_bundle(bundle_details, row)
					continue

				if row.get("qty") or row.get("consumed_qty") or row.get("stock_qty"):
					self.update_bundle_details(bundle_details, table_name, row, parent_details=parent_details)
					self.create_serial_batch_bundle(bundle_details, row)
					self.sync_capped_serial_nos_on_return(bundle_details, row)

				if row.get("rejected_qty"):
					self.update_bundle_details(bundle_details, table_name, row, is_rejected=True)
					self.create_serial_batch_bundle(bundle_details, row)

	def sync_capped_serial_nos_on_return(self, bundle_details, row):
		"""A partial return's mapped row keeps the original's full serial list while the
		composition covers only the returned qty - later returns subtract this row's text,
		so it must reflect what was actually returned."""
		if not self.doc.get("is_return") or not bundle_details.get("serial_nos"):
			return

		capped = "\n".join(bundle_details["serial_nos"])
		if row.serial_no != capped:
			row.db_set("serial_no", capped, update_modified=False)

	def apply_reserved_serial_batch(self, row, table_name) -> bool:
		"""Fallback for a Delivery Note / Sales Invoice row fulfilling a Stock Reservation Entry
		that spans more than one batch - a single `batch_no` field can't preview that, so the
		mapper leaves the row with no serial_no/batch_no set. Resolve the exact composition from
		the SRE here (via the row's persisted `so_detail` link) and write the Stock Location
		Ledger entries for it directly. No-op for anything else - most rows are handled by the
		normal serial_no/batch_no path above."""
		if self.doc.doctype not in ("Delivery Note", "Sales Invoice"):
			return False

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_reserved_serial_batch_for_delivery,
		)

		so_field = "sales_order" if self.doc.doctype == "Sales Invoice" else "against_sales_order"
		composition = get_reserved_serial_batch_for_delivery(so_field, table_name, self.doc, row)
		if not composition:
			return False

		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		serial_nos, batch_nos = composition
		SerialBatchCreation(
			{
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"posting_datetime": combine_datetime(self.doc.posting_date, self.doc.posting_time),
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"voucher_detail_no": row.name,
				"company": self.doc.company,
				"type_of_transaction": "Outward",
				"ledger_is_outward": 1,
				"use_serial_batch_fields": 1,
				"do_not_submit": True,
			}
		).make_location_ledger_entries(serial_nos=serial_nos, batch_nos=batch_nos)
		row.use_serial_batch_fields = 1
		return True

	def get_parent_details_for_packed_items(self):
		parent_details = frappe._dict()
		for row in self.doc.get("items"):
			parent_details[row.name] = row

		return parent_details

	def make_bundle_for_sales_purchase_return(self, table_name=None):
		if not self.doc.get("is_return"):
			return

		if not table_name:
			table_name = "items"

		self.make_bundle_for_non_rejected_qty(table_name)

		if self.doc.doctype in ["Purchase Invoice", "Purchase Receipt"]:
			self.make_bundle_for_rejected_qty(table_name)

	def make_bundle_for_rejected_qty(self, table_name=None):
		field, reference_ids = self.get_reference_ids(table_name, "rejected_qty")

		if not reference_ids:
			return

		child_doctype = self.doc.doctype + " Item"
		available_dict = available_serial_batch_for_return(
			field, child_doctype, reference_ids, is_rejected=True
		)

		for row in self.doc.get(table_name):
			if data := available_dict.get(row.get(field)):
				qty_field = "rejected_qty"
				warehouse_field = "rejected_warehouse"
				if row.get("return_qty_from_rejected_warehouse"):
					qty_field = "qty"
					warehouse_field = "warehouse"

				if not data.get("qty"):
					frappe.throw(
						_("For the {0}, no stock is available for the return in the warehouse {1}.").format(
							frappe.bold(row.item_code), row.get(warehouse_field)
						)
					)

				data = filter_serial_batches(
					self.doc, data, row, warehouse_field=warehouse_field, qty_field=qty_field
				)
				make_serial_batch_bundle_for_return(data, row, self.doc, warehouse_field, qty_field)
				if row.get("return_qty_from_rejected_warehouse"):
					row.db_set(
						{
							"batch_no": "",
							"serial_no": "",
						}
					)
				else:
					row.db_set(
						{
							"batch_no": "",
							"rejected_serial_no": "",
						}
					)

	def make_bundle_for_non_rejected_qty(self, table_name):
		field, reference_ids = self.get_reference_ids(table_name)
		if not reference_ids:
			return

		child_doctype = self.doc.doctype + " Item"
		if table_name == "packed_items":
			field = "parent_detail_docname"
			child_doctype = "Packed Item"

		available_dict = available_serial_batch_for_return(field, child_doctype, reference_ids)

		for row in self.doc.get(table_name):
			value = row.get(field)
			if table_name == "packed_items" and row.get("parent_detail_docname"):
				value = self.get_value_for_packed_item(row)
				if not value:
					continue

			if data := available_dict.get(value):
				data = filter_serial_batches(self.doc, data, row)
				entries = make_serial_batch_bundle_for_return(data, row, self.doc)
				row.db_set(
					{
						"batch_no": "",
						"serial_no": "",
					}
				)

				if self.doc.doctype in ["Sales Invoice", "Delivery Note"] and entries:
					total_qty = sum(abs(flt(e.get("qty"))) for e in entries)
					avg_rate = (
						sum(abs(flt(e.get("qty"))) * flt(e.get("incoming_rate")) for e in entries) / total_qty
						if total_qty
						else 0
					)
					row.db_set("incoming_rate", avg_rate)

	def get_value_for_packed_item(self, row):
		parent_items = self.doc.get("items", {"name": row.parent_detail_docname})
		if parent_items:
			ref = parent_items[0].get("dn_detail")
			return (row.item_code, ref)

		return None

	def get_reference_ids(self, table_name, qty_field=None) -> tuple[str, list[str]]:
		field = {
			"Sales Invoice": "sales_invoice_item",
			"Delivery Note": "dn_detail",
			"Purchase Receipt": "purchase_receipt_item",
			"Purchase Invoice": "purchase_invoice_item",
			"POS Invoice": "pos_invoice_item",
		}.get(self.doc.doctype)

		if not qty_field:
			qty_field = "qty"

		reference_ids = []

		for row in self.doc.get(table_name):
			if not self.is_serial_batch_item(row.item_code):
				continue

			if (
				row.get(field)
				and (
					qty_field == "qty"
					and not row.get("return_qty_from_rejected_warehouse")
					or qty_field == "rejected_qty"
					and (row.get("return_qty_from_rejected_warehouse") or row.get("rejected_warehouse"))
				)
				and not row.get("use_serial_batch_fields")
			):
				reference_ids.append(row.get(field))

			if table_name == "packed_items" and row.get("parent_detail_docname"):
				parent_rows = self.doc.get("items", {"name": row.parent_detail_docname}) or []
				for d in parent_rows:
					if d.get(field):
						reference_ids.append(d.get(field))

		return field, reference_ids

	def is_serial_batch_item(self, item_code) -> bool:
		item_details = frappe.get_cached_value(
			"Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=True
		)
		if not item_details:
			frappe.throw(_("Item {0} does not exist.").format(bold(item_code)))

		return bool(item_details.has_serial_no or item_details.has_batch_no)

	def update_bundle_details(self, bundle_details, table_name, row, is_rejected=False, parent_details=None):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		# Since qty field is different for different doctypes
		qty = row.get("qty")
		warehouse = row.get("warehouse")

		if table_name == "packed_items":
			type_of_transaction = "Inward"
			if not self.doc.is_return:
				type_of_transaction = "Outward"
		elif table_name == "supplied_items":
			qty = row.consumed_qty
			warehouse = self.doc.supplier_warehouse
			type_of_transaction = "Outward"
			if self.doc.is_return:
				type_of_transaction = "Inward"
		else:
			type_of_transaction = get_type_of_transaction(self.doc, row)

		if hasattr(row, "stock_qty"):
			qty = row.stock_qty

		if self.doc.doctype == "Stock Entry":
			qty = row.transfer_qty
			warehouse = row.s_warehouse or row.t_warehouse

		serial_nos = row.serial_no
		if is_rejected:
			serial_nos = row.get("rejected_serial_no")
			type_of_transaction = "Inward" if not self.doc.is_return else "Outward"
			qty = flt(
				row.get("rejected_qty") * row.get("conversion_factor", 1.0),
				frappe.get_precision("Stock Location Ledger", "qty"),
			)
			warehouse = row.get("rejected_warehouse")

		if (
			self.doc.is_internal_transfer()
			and self.doc.doctype in ["Sales Invoice", "Delivery Note"]
			and self.doc.is_return
		):
			warehouse = row.get("target_warehouse") or row.get("warehouse")
			type_of_transaction = "Outward"

		if table_name == "packed_items":
			if not warehouse:
				warehouse = parent_details[row.parent_detail_docname].warehouse
			bundle_details["voucher_detail_no"] = parent_details[row.parent_detail_docname].name

		serial_nos_list = get_serial_nos(serial_nos) if serial_nos else None
		# The row can list more serials than this movement covers: a supplied-items row keeps
		# every transferred serial while consuming fewer (and on partial transfers some are not
		# even in the supplier warehouse - let auto-pick resolve from actual availability), and
		# a partial return's mapped row keeps the original invoice's full list (return the
		# first N of it).
		cap = cint(abs(flt(qty)))
		if serial_nos_list and cap and len(serial_nos_list) > cap:
			serial_nos_list = None if table_name == "supplied_items" else serial_nos_list[:cap]

		bundle_details.update(
			{
				"qty": qty,
				"is_rejected": is_rejected,
				"type_of_transaction": type_of_transaction,
				"warehouse": warehouse,
				"batches": frappe._dict({row.batch_no: qty}) if row.batch_no else None,
				"serial_nos": serial_nos_list,
				"batch_no": row.batch_no,
			}
		)

	def create_serial_batch_bundle(self, bundle_details, row):
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		# SLL-native: entries are persisted directly as draft Stock Location Ledger rows,
		# keyed by (voucher_type, voucher_no, voucher_detail_no, warehouse) - no Serial and
		# Batch Bundle document is created, so no bundle-name field to set on the row.
		SerialBatchCreation(bundle_details).make_location_ledger_entries()

	def set_use_serial_batch_fields(self):
		if frappe.get_single_value("Stock Settings", "use_serial_batch_fields"):
			for row in self.doc.items:
				row.use_serial_batch_fields = 1

	def delete_auto_created_batches(self):
		for table_name in ["items", "packed_items", "supplied_items"]:
			if not self.doc.get(table_name):
				continue

			for row in self.doc.get(table_name):
				if row.get("batch_no"):
					row.db_set("batch_no", None)

	def validate_reserved_batches(self):
		if not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
			return

		if self.doc.doctype not in ["Delivery Note", "Sales Invoice", "Stock Entry"]:
			return

		batches = frappe.get_all(
			"Stock Location Ledger",
			filters={
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"docstatus": 1,
				"batch_no": ("is", "set"),
				"qty": ("<", 0),
			},
			pluck="batch_no",
		)

		if not batches:
			return

		reference_fields = {
			"Sales Invoice": ["sales_order"],
			"Delivery Note": ["against_sales_order"],
			"Stock Entry": ["work_order", "subcontracting_inward_order"],
		}.get(self.doc.doctype)

		items = self.doc.items
		if self.doc.doctype == "Stock Entry":
			items = [self.doc]

		own_vouchers = {item.get(field) for item in items for field in reference_fields if item.get(field)}

		outstanding_qty = defaultdict(float)
		reservations = defaultdict(list)
		for row in self.get_reserved_batches(batches):
			if row.voucher_no in own_vouchers:
				continue

			key = (row.batch_no, row.warehouse)
			outstanding = flt(row.qty) - flt(row.delivered_qty)
			outstanding_qty[key] += outstanding
			if outstanding > 0:
				reservations[key].append(row)

		precision = frappe.get_precision("Stock Location Ledger", "qty")
		for (batch_no, warehouse), reserved_qty in outstanding_qty.items():
			if flt(reserved_qty, precision) <= 0:
				continue

			batch_qty = get_batch_qty(
				batch_no,
				warehouse,
				posting_date=self.doc.posting_date,
				posting_time=self.doc.posting_time,
				consider_negative_batches=True,
			)

			if flt(batch_qty, precision) >= flt(reserved_qty, precision):
				continue

			vouchers = ", ".join(
				f"{frappe.bold(voucher_type)} {frappe.bold(voucher_no)}"
				for voucher_type, voucher_no in dict.fromkeys(
					(row.voucher_type, row.voucher_no) for row in reservations[(batch_no, warehouse)]
				)
			)
			frappe.throw(
				_(
					"The batch {0} is reserved for {1} in the warehouse {2} and the remaining quantity is not enough to cover the reservations. So, cannot proceed with the {3} {4}."
				).format(
					frappe.bold(batch_no),
					vouchers,
					frappe.bold(warehouse),
					frappe.bold(self.doc.doctype),
					frappe.bold(self.doc.name),
				),
				title=_("Reserved Batch Conflict"),
			)

	def get_reserved_batches(self, batches):
		doctype = frappe.qb.DocType("Stock Reservation Entry")
		child_doc = frappe.qb.DocType("Stock Reservation Serial Batch")

		return (
			frappe.qb.from_(doctype)
			.join(child_doc)
			.on(doctype.name == child_doc.parent)
			.select(
				child_doc.batch_no,
				child_doc.qty,
				child_doc.delivered_qty,
				doctype.voucher_type,
				doctype.voucher_no,
				doctype.warehouse,
			)
			.where((doctype.docstatus == 1) & (child_doc.batch_no.isin(batches)))
		).run(as_dict=True)
