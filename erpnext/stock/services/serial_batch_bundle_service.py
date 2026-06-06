# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Serial & Batch Bundle handling for stock transactions.

Extracted from ``StockController``. Owns creation, validation and teardown of
Serial and Batch Bundles for a stock voucher. The controller keeps thin
delegators for methods reached from other doctypes / ``run_method``; internal
helpers live here only.
"""

import frappe
from frappe import _, bold
from frappe.utils import cstr, flt, get_link_to_form, getdate

from erpnext.controllers.sales_and_purchase_return import (
	available_serial_batch_for_return,
	filter_serial_batches,
	make_serial_batch_bundle_for_return,
)
from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	combine_datetime,
	get_type_of_transaction,
)


class SerialBatchBundleService:
	def __init__(self, doc) -> None:
		self.doc = doc

	def validate_warehouse_of_sabb(self):
		if self.doc.is_internal_transfer():
			return

		doc_before_save = self.doc.get_doc_before_save()

		for row in self.doc.items:
			if not row.get("serial_and_batch_bundle"):
				continue

			sabb_details = frappe.db.get_value(
				"Serial and Batch Bundle",
				row.serial_and_batch_bundle,
				["type_of_transaction", "warehouse", "has_serial_no"],
				as_dict=True,
			)
			if not sabb_details:
				continue

			if sabb_details.type_of_transaction != "Outward":
				continue

			warehouse = row.get("warehouse") or row.get("s_warehouse")
			if sabb_details.warehouse != warehouse:
				frappe.throw(
					_(
						"Row #{0}: Warehouse {1} does not match with the warehouse {2} in Serial and Batch Bundle {3}."
					).format(row.idx, warehouse, sabb_details.warehouse, row.serial_and_batch_bundle)
				)

			if self.doc.doctype == "Stock Reconciliation":
				continue

			if sabb_details.has_serial_no and doc_before_save and doc_before_save.get("items"):
				prev_row = doc_before_save.get("items", {"idx": row.idx})
				if prev_row and prev_row[0].serial_and_batch_bundle != row.serial_and_batch_bundle:
					sabb_doc = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
					sabb_doc.validate_serial_no_status()

	def validate_duplicate_serial_and_batch_bundle(self, table_name):
		if not self.doc.get(table_name):
			return

		sbb_list = []
		for item in self.doc.get(table_name):
			if item.get("serial_and_batch_bundle"):
				sbb_list.append(item.get("serial_and_batch_bundle"))

			if item.get("rejected_serial_and_batch_bundle"):
				sbb_list.append(item.get("rejected_serial_and_batch_bundle"))

		if sbb_list:
			SLE = frappe.qb.DocType("Stock Ledger Entry")
			data = (
				frappe.qb.from_(SLE)
				.select(SLE.voucher_type, SLE.voucher_no, SLE.serial_and_batch_bundle)
				.where(
					(SLE.docstatus == 1)
					& (SLE.serial_and_batch_bundle.notnull())
					& (SLE.serial_and_batch_bundle.isin(sbb_list))
				)
				.limit(1)
			).run(as_dict=True)

			if data:
				data = data[0]
				frappe.throw(
					_("Serial and Batch Bundle {0} is already used in {1} {2}.").format(
						frappe.bold(data.serial_and_batch_bundle), data.voucher_type, data.voucher_no
					)
				)

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
			if (
				not via_landed_cost_voucher
				and row.serial_and_batch_bundle
				and (row.serial_no or row.batch_no)
			):
				self.validate_serial_nos_and_batches_with_bundle(row)

			if not row.serial_no and not row.batch_no and not row.get("rejected_serial_no"):
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

				if row.get("rejected_qty"):
					self.update_bundle_details(bundle_details, table_name, row, is_rejected=True)
					self.create_serial_batch_bundle(bundle_details, row)

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
				bundle = make_serial_batch_bundle_for_return(data, row, self.doc, warehouse_field, qty_field)
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
				bundle = make_serial_batch_bundle_for_return(data, row, self.doc)
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

	def get_value_for_packed_item(self, row):
		parent_items = self.doc.get("items", {"name": row.parent_detail_docname})
		if parent_items:
			ref = parent_items[0].get("dn_detail")
			return (row.item_code, ref)

		return None

	def get_reference_ids(self, table_name, qty_field=None, bundle_field=None) -> tuple[str, list[str]]:
		field = {
			"Sales Invoice": "sales_invoice_item",
			"Delivery Note": "dn_detail",
			"Purchase Receipt": "purchase_receipt_item",
			"Purchase Invoice": "purchase_invoice_item",
			"POS Invoice": "pos_invoice_item",
		}.get(self.doc.doctype)

		if not bundle_field:
			bundle_field = "serial_and_batch_bundle"

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
				and not row.get(bundle_field)
			):
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
			qty = flt(
				row.get("rejected_qty") * row.get("conversion_factor", 1.0),
				frappe.get_precision("Serial and Batch Entry", "qty"),
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

		sn_doc = SerialBatchCreation(bundle_details).make_serial_and_batch_bundle()

		field = "serial_and_batch_bundle"
		if bundle_details.get("is_rejected"):
			field = "rejected_serial_and_batch_bundle"

		row.set(field, sn_doc.name)
		row.db_set({field: sn_doc.name})

	def validate_serial_nos_and_batches_with_bundle(self, row):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		throw_error = False
		if row.serial_no:
			serial_nos = frappe.get_all(
				"Serial and Batch Entry",
				fields=["serial_no"],
				filters={"parent": row.serial_and_batch_bundle},
			)
			serial_nos = sorted([cstr(d.serial_no) for d in serial_nos])
			parsed_serial_nos = get_serial_nos(row.serial_no)

			if len(serial_nos) != len(parsed_serial_nos):
				throw_error = True
			elif serial_nos != parsed_serial_nos:
				for serial_no in serial_nos:
					if serial_no not in parsed_serial_nos:
						throw_error = True
						break

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
					"At row {0}: Serial and Batch Bundle {1} has already created. Please remove the values from the serial no or batch no fields."
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
		self, serial_and_batch_bundle, warehouse, type_of_transaction=None, do_not_submit=None, qty=0
	):
		from erpnext.controllers.stock_controller import make_bundle_for_material_transfer

		return make_bundle_for_material_transfer(
			is_new=self.doc.is_new(),
			docstatus=self.doc.docstatus,
			voucher_type=self.doc.doctype,
			voucher_no=self.doc.name,
			serial_and_batch_bundle=serial_and_batch_bundle,
			warehouse=warehouse,
			type_of_transaction=type_of_transaction,
			do_not_submit=do_not_submit,
			qty=qty,
		)

	def validate_reserved_batches(self):
		if not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
			return

		if self.doc.doctype not in ["Delivery Note", "Sales Invoice", "Stock Entry"]:
			return

		batches = frappe.get_all(
			"Serial and Batch Entry",
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

		field_mapper = {
			"Sales Invoice": [["Sales Order", "sales_order"]],
			"Delivery Note": [["Sales Order", "against_sales_order"]],
			"Stock Entry": [
				["Work Order", "work_order"],
				["Subcontracting Inward Order", "subcontracting_inward_order"],
			],
		}.get(self.doc.doctype)

		qty_field = {
			"Sales Invoice": "qty",
			"Delivery Note": "qty",
			"Stock Entry": "fg_completed_qty",
		}.get(self.doc.doctype)

		reserved_batches_data = self.get_reserved_batches(batches)
		items = self.doc.items
		if self.doc.doctype == "Stock Entry":
			items = [self.doc]

		for item in items:
			for field in field_mapper:
				if not item.get(field[1]):
					continue

				value = item.get(field[1])
				for row in reserved_batches_data:
					if self.doc.doctype in ["Sales Invoice", "Delivery Note"] and row.item_code != item.get(
						"item_code"
					):
						continue

					if row.voucher_no == value:
						continue

					batch_qty = get_batch_qty(
						row.batch_no,
						row.warehouse,
						posting_date=self.doc.posting_date,
						posting_time=self.doc.posting_time,
						consider_negative_batches=True,
					)

					if item.get(qty_field) < batch_qty:
						continue

					frappe.throw(
						_(
							"The batch {0} is already reserved in {1} {2}. So, cannot proceed with the {3} {4}, which is created against the {5} {6}."
						).format(
							frappe.bold(row.batch_no),
							frappe.bold(row.voucher_type),
							frappe.bold(row.voucher_no),
							frappe.bold(self.doc.doctype),
							frappe.bold(self.doc.name),
							frappe.bold(field[0]),
							frappe.bold(value),
						),
						title=_("Reserved Batch Conflict"),
					)

	def get_reserved_batches(self, batches):
		doctype = frappe.qb.DocType("Stock Reservation Entry")
		child_doc = frappe.qb.DocType("Serial and Batch Entry")

		return (
			frappe.qb.from_(doctype)
			.join(child_doc)
			.on(doctype.name == child_doc.parent)
			.select(
				child_doc.batch_no,
				doctype.voucher_type,
				doctype.voucher_no,
				doctype.item_code,
				doctype.warehouse,
			)
			.where((doctype.docstatus == 1) & (child_doc.batch_no.isin(batches)))
		).run(as_dict=True)
