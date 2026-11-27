# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Serial & Batch Bundle handling for stock transactions.

Extracted from ``StockController``. Owns creation and teardown of Serial and
Batch Bundles for a stock voucher; their checks live in ``serial_batch_validation_service``. The controller keeps thin
delegators for methods reached from other doctypes / ``run_method``; internal
helpers live here only.
"""

from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.utils import flt

from erpnext.controllers.sales_and_purchase_return import (
	available_serial_batch_for_return,
	filter_serial_batches,
	make_serial_batch_bundle_for_return,
	remove_picked_serial_batches,
)
from erpnext.stock.doctype.serial_and_batch_bundle.api import get_type_of_transaction
from erpnext.stock.serial_batch_bundle import add_picked_batches
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.stock.utils import get_combine_datetime


class SerialBatchBundleService:
	def __init__(self, doc) -> None:
		self.doc = doc

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

		auto_pick_outward = self.auto_picks_outward_serial_batch()
		picked_serial_nos = picked_batches = None
		if auto_pick_outward:
			picked_serial_nos = self.get_serial_nos_used_in_rows()
			picked_batches = self.get_batches_used_in_rows()

		for row in self.doc.get(table_name):
			item_code = row.get("rm_item_code") or row.get("item_code")
			if not item_code or not self.is_serial_batch_item(item_code):
				continue

			if (
				not via_landed_cost_voucher
				and row.serial_and_batch_bundle
				and (row.serial_no or row.batch_no)
			):
				self.validate_serial_nos_and_batches_with_bundle(row)

			if not row.serial_no and not row.batch_no and not row.get("rejected_serial_no"):
				if not (auto_pick_outward and row.get("use_serial_batch_fields") and flt(row.get("qty")) > 0):
					continue

			if not row.use_serial_batch_fields and (
				row.serial_no or row.batch_no or row.get("rejected_serial_no")
			):
				row.use_serial_batch_fields = 1

			if row.use_serial_batch_fields and (
				not row.serial_and_batch_bundle and not row.get("rejected_serial_and_batch_bundle")
			):
				bundle_details = {
					"item_code": row.get("rm_item_code") or row.item_code,
					"posting_datetime": get_combine_datetime(self.doc.posting_date, self.doc.posting_time),
					"voucher_type": self.doc.doctype,
					"voucher_no": self.doc.name,
					"voucher_detail_no": row.name,
					"company": self.doc.company,
					"is_rejected": 1 if row.get("rejected_warehouse") else 0,
					"use_serial_batch_fields": row.use_serial_batch_fields,
					"via_landed_cost_voucher": via_landed_cost_voucher,
					"do_not_submit": True if not via_landed_cost_voucher else False,
				}

				if self.doc.is_internal_transfer() and row.get("from_warehouse") and not self.doc.is_return:
					self.update_bundle_details(bundle_details, table_name, row)
					bundle_details["type_of_transaction"] = "Outward"
					bundle_details["warehouse"] = row.get("from_warehouse")
					bundle_details["qty"] = row.get("stock_qty") or row.get("qty")
					self.create_serial_batch_bundle(bundle_details, row)
					continue

				if row.get("qty") or row.get("consumed_qty") or row.get("stock_qty"):
					self.update_bundle_details(bundle_details, table_name, row, parent_details=parent_details)
					self.create_auto_picked_bundle(bundle_details, row, picked_serial_nos, picked_batches)

				if self.get_rejected_stock_qty(row):
					self.update_bundle_details(bundle_details, table_name, row, is_rejected=True)
					self.create_serial_batch_bundle(bundle_details, row)

	def get_serial_nos_used_in_rows(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		numbers_by_item = defaultdict(list)
		bundle_items = {}
		for row in self.doc.get("items") + self.get_current_packed_rows():
			item_code = row.get("rm_item_code") or row.item_code
			if row.get("serial_no"):
				numbers_by_item[item_code].extend(get_serial_nos(row.serial_no))
			elif row.get("serial_and_batch_bundle"):
				bundle_items[row.serial_and_batch_bundle] = item_code

		picked_serial_nos = defaultdict(list)
		for item_code, numbers in numbers_by_item.items():
			records = SerialBatchIdentity("Serial No").get_records(item_code, numbers, ["name"])
			picked_serial_nos[item_code].extend(record.name for record in records)

		self.add_serial_nos_in_bundles(picked_serial_nos, bundle_items)
		return picked_serial_nos

	def get_batches_used_in_rows(self):
		"""Batch qty the rows already take, by (batch_no, warehouse)."""
		entries, bundles = [], []
		# the row's bundle takes the qty rounded to this precision
		precision = frappe.get_precision("Serial and Batch Entry", "qty")
		for row in self.doc.get("items") + self.get_current_packed_rows():
			if row.get("serial_and_batch_bundle"):
				bundles.append(row.serial_and_batch_bundle)
			elif row.get("batch_no"):
				qty = row.qty if row.doctype == "Packed Item" else row.stock_qty
				entries.append(
					frappe._dict(batch_no=row.batch_no, warehouse=row.warehouse, qty=-flt(qty, precision))
				)

		if bundles:
			entries += frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": ("in", bundles), "batch_no": ("is", "set")},
				fields=["batch_no", "warehouse", "qty"],
			)

		picked_batches = frappe._dict()
		add_picked_batches(picked_batches, entries)
		return picked_batches

	def get_current_packed_rows(self):
		"""Packed rows of the current item rows; rows of removed items stay until the packing list is rebuilt."""
		item_rows = {(row.name, row.item_code) for row in self.doc.get("items")}
		return [
			row
			for row in self.doc.get("packed_items") or []
			if (row.parent_detail_docname, row.parent_item) in item_rows
		]

	def add_serial_nos_in_bundles(self, picked_serial_nos, bundle_items):
		if not bundle_items:
			return

		for entry in frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": ("in", list(bundle_items)), "serial_no": ("is", "set")},
			fields=["parent", "serial_no"],
		):
			picked_serial_nos[bundle_items[entry.parent]].append(entry.serial_no)

	def create_auto_picked_bundle(self, bundle_details, row, picked_serial_nos, picked_batches):
		if picked_serial_nos is None or row.serial_no:
			self.create_serial_batch_bundle(bundle_details, row)
			return

		item_code = bundle_details["item_code"]
		bundle_details["ignore_serial_nos"] = list(picked_serial_nos[item_code])
		bundle_details["already_picked_batches"] = picked_batches
		sn_doc = self.create_serial_batch_bundle(bundle_details, row)
		if row.doctype == "Packed Item":
			from erpnext.stock.doctype.packed_item.packed_item import set_incoming_rate_from_bundle

			set_incoming_rate_from_bundle(row, sn_doc)
		entries = sn_doc.get("entries") or []
		picked_serial_nos[item_code].extend(d.serial_no for d in entries if d.serial_no)
		# a row's own batch no is already counted in picked_batches
		if not row.batch_no:
			add_picked_batches(picked_batches, entries)

	def auto_picks_outward_serial_batch(self):
		if self.doc.doctype not in ("Delivery Note", "Sales Invoice", "POS Invoice") or self.doc.get(
			"is_return"
		):
			return False

		return bool(
			frappe.get_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward")
		)

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

		if self.doc.doctype in ["Purchase Invoice", "Purchase Receipt", "Subcontracting Receipt"]:
			self.make_bundle_for_rejected_qty(table_name)

	def make_bundle_for_rejected_qty(self, table_name=None):
		field, reference_ids = self.get_reference_ids(
			table_name, "rejected_qty", "rejected_serial_and_batch_bundle"
		)

		if not reference_ids:
			return

		child_doctype = self.doc.doctype + " Item"
		available_dict = available_serial_batch_for_return(
			field, child_doctype, reference_ids, is_rejected=True
		)

		for row in self.doc.get(table_name):
			if not self.needs_rejected_bundle(row):
				continue

			if data := available_dict.get(row.get(field)):
				qty_field = "rejected_qty"
				warehouse_field = "rejected_warehouse"
				if row.get("return_qty_from_rejected_warehouse"):
					qty_field = "stock_qty"
					warehouse_field = "warehouse"

				if not data.get("qty"):
					frappe.throw(
						_("For the {0}, no stock is available for the return in the warehouse {1}.").format(
							frappe.bold(row.item_code), row.get(warehouse_field)
						)
					)

				picked = filter_serial_batches(
					self.doc, data, row, warehouse_field=warehouse_field, qty_field=qty_field
				)
				bundle = make_serial_batch_bundle_for_return(
					picked, row, self.doc, warehouse_field, qty_field
				)
				remove_picked_serial_batches(data, picked, self.doc)
				if row.get("return_qty_from_rejected_warehouse"):
					row.db_set(
						{
							"serial_and_batch_bundle": bundle,
							"batch_no": "",
							"serial_no": "",
						}
					)
				else:
					row.db_set(
						{
							"rejected_serial_and_batch_bundle": bundle,
							"batch_no": "",
							"rejected_serial_no": "",
						}
					)

	def make_bundle_for_non_rejected_qty(self, table_name):
		field, reference_ids = self.get_reference_ids(table_name)
		if not reference_ids:
			return

		reference_field = field
		child_doctype = self.doc.doctype + " Item"
		if table_name == "packed_items":
			field = "parent_detail_docname"
			child_doctype = "Packed Item"

		available_dict = available_serial_batch_for_return(field, child_doctype, reference_ids)

		for row in self.doc.get(table_name):
			if row.get("return_qty_from_rejected_warehouse") or not row.get("qty"):
				continue

			value = row.get(field)
			if table_name == "packed_items" and row.get("parent_detail_docname"):
				value = self.get_value_for_packed_item(row, reference_field)
				if not value:
					continue

			if data := available_dict.get(value):
				picked = filter_serial_batches(self.doc, data, row)
				bundle = make_serial_batch_bundle_for_return(picked, row, self.doc)
				remove_picked_serial_batches(data, picked, self.doc)
				row.db_set(
					{
						"serial_and_batch_bundle": bundle,
						"batch_no": "",
						"serial_no": "",
					}
				)

				if self.doc.doctype in ["Sales Invoice", "Delivery Note"]:
					row.db_set(
						"incoming_rate", frappe.db.get_value("Serial and Batch Bundle", bundle, "avg_rate")
					)

	def needs_rejected_bundle(self, row) -> bool:
		"""Return row takes rejected qty and has no bundle for it yet."""
		if row.get("return_qty_from_rejected_warehouse"):
			return not row.get("serial_and_batch_bundle")

		return bool(
			row.get("rejected_warehouse")
			and self.get_rejected_stock_qty(row)
			and not row.get("rejected_serial_and_batch_bundle")
		)

	def get_rejected_stock_qty(self, row) -> float:
		"""Rejected qty of a row in the stock UOM, rounded as its bundle holds it."""
		return flt(
			flt(row.get("rejected_qty")) * flt(row.get("conversion_factor", 1.0)),
			frappe.get_precision("Serial and Batch Entry", "qty"),
		)

	def get_value_for_packed_item(self, row, reference_field):
		parent_items = self.doc.get("items", {"name": row.parent_detail_docname})
		if parent_items:
			return (row.item_code, parent_items[0].get(reference_field))

		return None

	def get_reference_ids(self, table_name, qty_field=None, bundle_field=None) -> tuple[str, list[str]]:
		field = {
			"Sales Invoice": "sales_invoice_item",
			"Delivery Note": "dn_detail",
			"Purchase Receipt": "purchase_receipt_item",
			"Purchase Invoice": "purchase_invoice_item",
			"POS Invoice": "pos_invoice_item",
			"Subcontracting Receipt": "subcontracting_receipt_item",
		}.get(self.doc.doctype)

		if not bundle_field:
			bundle_field = "serial_and_batch_bundle"

		if not qty_field:
			qty_field = "qty"

		reference_ids = []

		for row in self.doc.get(table_name):
			if not self.is_serial_batch_item(row.item_code):
				continue

			needs_bundle = (
				self.needs_rejected_bundle(row)
				if qty_field == "rejected_qty"
				else row.get("qty")
				and not row.get("return_qty_from_rejected_warehouse")
				and not row.get(bundle_field)
			)
			if row.get(field) and needs_bundle and not row.get("use_serial_batch_fields"):
				reference_ids.append(row.get(field))

			if table_name == "packed_items" and row.get("parent_detail_docname"):
				parent_rows = self.doc.get("items", {"name": row.parent_detail_docname}) or []
				for d in parent_rows:
					if d.get(field) and not d.get(bundle_field):
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
			qty = self.get_rejected_stock_qty(row)
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

		bundle_details.update(
			{
				"qty": qty,
				"is_rejected": is_rejected,
				"type_of_transaction": type_of_transaction,
				"warehouse": warehouse,
				"batches": frappe._dict({row.batch_no: qty}) if row.batch_no else None,
				"serial_nos": get_serial_nos(serial_nos) if serial_nos else None,
				"batch_no": row.batch_no,
			}
		)

	def create_serial_batch_bundle(self, bundle_details, row):
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		resolved_details = bundle_details.copy()
		if bundle_details.get("serial_nos"):
			resolved_details["serial_nos"] = SerialBatchIdentity("Serial No").resolve(
				bundle_details["item_code"],
				bundle_details["serial_nos"],
				create=bundle_details.get("type_of_transaction") == "Inward",
				defaults={"company": self.doc.company, "batch_no": bundle_details.get("batch_no")},
				ignore_permissions=self.doc.flags.ignore_permissions,
			)
		sn_doc = SerialBatchCreation(resolved_details).make_serial_and_batch_bundle()

		field = "serial_and_batch_bundle"
		if bundle_details.get("is_rejected"):
			field = "rejected_serial_and_batch_bundle"

		row.set(field, sn_doc.name)
		row.db_set({field: sn_doc.name})

		return sn_doc

	def validate_serial_nos_and_batches_with_bundle(self, row):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		throw_error = False
		if row.serial_no:
			serial_nos = frappe.get_all(
				"Serial and Batch Entry",
				pluck="serial_no",
				filters={"parent": row.serial_and_batch_bundle},
			)
			parsed_serial_nos = SerialBatchIdentity("Serial No").resolve(
				row.get("rm_item_code") or row.item_code,
				get_serial_nos(row.serial_no),
				ignore_permissions=self.doc.flags.ignore_permissions,
			)
			throw_error = sorted(name or "" for name in serial_nos) != sorted(parsed_serial_nos)

		elif row.batch_no:
			batches = sorted(
				frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle},
					pluck="batch_no",
					distinct=True,
				)
			)

			if batches != [row.batch_no]:
				throw_error = True

		if throw_error:
			frappe.throw(
				_(
					"At row {0}: Serial and Batch Bundle {1} has already been created. Please remove the values from the serial no or batch no fields."
				).format(row.idx, row.serial_and_batch_bundle)
			)

	def set_use_serial_batch_fields(self):
		if frappe.get_single_value("Stock Settings", "use_serial_batch_fields"):
			for row in self.doc.items:
				row.use_serial_batch_fields = 1

	def delete_auto_created_batches(self):
		for table_name in ["items", "packed_items", "supplied_items"]:
			if not self.doc.get(table_name):
				continue

			for row in self.doc.get(table_name):
				update_values = {}
				if row.get("batch_no"):
					update_values["batch_no"] = None

				if row.get("serial_and_batch_bundle"):
					update_values["serial_and_batch_bundle"] = None
					frappe.db.set_value(
						"Serial and Batch Bundle", row.serial_and_batch_bundle, {"is_cancelled": 1}
					)

					frappe.db.set_value(
						"Serial and Batch Entry", {"parent": row.serial_and_batch_bundle}, {"is_cancelled": 1}
					)

				if update_values:
					row.db_set(update_values)

				if table_name == "items" and row.get("rejected_serial_and_batch_bundle"):
					frappe.db.set_value(
						"Serial and Batch Bundle", row.rejected_serial_and_batch_bundle, {"is_cancelled": 1}
					)

					frappe.db.set_value(
						"Serial and Batch Entry",
						{"parent": row.rejected_serial_and_batch_bundle},
						{"is_cancelled": 1},
					)

					row.db_set("rejected_serial_and_batch_bundle", None)

				if row.get("current_serial_and_batch_bundle"):
					row.db_set("current_serial_and_batch_bundle", None)

	def set_serial_and_batch_bundle(self, table_name=None, ignore_validate=False):
		if not table_name:
			table_name = "items"

		QTY_FIELD = {
			"serial_and_batch_bundle": "qty",
			"current_serial_and_batch_bundle": "current_qty",
			"rejected_serial_and_batch_bundle": "rejected_qty",
		}

		for row in self.doc.get(table_name):
			for field in QTY_FIELD.keys():
				if row.get(field):
					frappe.get_doc("Serial and Batch Bundle", row.get(field)).set_serial_and_batch_values(
						self.doc, row, qty_field=QTY_FIELD[field]
					)

	def make_package_for_transfer(
		self,
		serial_and_batch_bundle,
		warehouse,
		type_of_transaction=None,
		do_not_submit=None,
		qty=0,
		include_bundle=None,
		exclude_serial_nos=None,
		total_qty=0,
	):
		from erpnext.controllers.stock_controller import make_bundle_for_material_transfer

		return make_bundle_for_material_transfer(
			is_new=self.doc.is_new(),
			docstatus=self.doc.docstatus,
			voucher_type=self.doc.doctype,
			voucher_no=self.doc.name,
			company=self.doc.company,
			serial_and_batch_bundle=serial_and_batch_bundle,
			warehouse=warehouse,
			type_of_transaction=type_of_transaction,
			do_not_submit=do_not_submit,
			qty=qty,
			include_bundle=include_bundle,
			exclude_serial_nos=exclude_serial_nos,
			total_qty=total_qty,
		)
