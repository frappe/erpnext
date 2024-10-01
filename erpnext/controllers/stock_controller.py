# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate

import erpnext
from erpnext.accounts.general_ledger import (
	make_gl_entries,
	make_reverse_gl_entries,
	process_gl_map,
)
from erpnext.accounts.utils import cancel_exchange_gain_loss_journal, get_fiscal_year
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.controllers.sales_and_purchase_return import (
	available_serial_batch_for_return,
	filter_serial_batches,
	make_serial_batch_bundle_for_return,
)
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
	get_evaluated_inventory_dimension,
)
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	get_type_of_transaction,
)
from erpnext.stock.stock_ledger import get_items_to_be_repost


class QualityInspectionRequiredError(frappe.ValidationError):
	pass


class QualityInspectionRejectedError(frappe.ValidationError):
	pass


class QualityInspectionNotSubmittedError(frappe.ValidationError):
	pass


class BatchExpiredError(frappe.ValidationError):
	pass


class StockController(AccountsController):
	def validate(self):
		super().validate()

		if self.docstatus == 0:
			for table_name in ["items", "packed_items", "supplied_items"]:
				self.validate_duplicate_serial_and_batch_bundle(table_name)

		if not self.get("is_return"):
			self.validate_inspection()
		self.validate_serialized_batch()
		self.clean_serial_nos()
		self.validate_customer_provided_item()
		self.set_rate_of_stock_uom()
		self.validate_internal_transfer()
		self.validate_putaway_capacity()

	def validate_duplicate_serial_and_batch_bundle(self, table_name):
		if not self.get(table_name):
			return

		sbb_list = []
		for item in self.get(table_name):
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

	def make_gl_entries(self, gl_entries=None, from_repost=False, via_landed_cost_voucher=False):
		if self.docstatus == 2:
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

		provisional_accounting_for_non_stock_items = cint(
			frappe.get_cached_value(
				"Company", self.company, "enable_provisional_accounting_for_non_stock_items"
			)
		)

		is_asset_pr = any(d.get("is_fixed_asset") for d in self.get("items"))

		if (
			cint(erpnext.is_perpetual_inventory_enabled(self.company))
			or provisional_accounting_for_non_stock_items
			or is_asset_pr
		):
			warehouse_account = get_warehouse_account_map(self.company)

			if self.docstatus == 1:
				if not gl_entries:
					gl_entries = (
						self.get_gl_entries(warehouse_account, via_landed_cost_voucher)
						if self.doctype == "Purchase Receipt"
						else self.get_gl_entries(warehouse_account)
					)
				make_gl_entries(gl_entries, from_repost=from_repost)

	def validate_serialized_batch(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		is_material_issue = False
		if self.doctype == "Stock Entry" and self.purpose == "Material Issue":
			is_material_issue = True

		for d in self.get("items"):
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

			if flt(d.qty) > 0.0 and d.get("batch_no") and self.get("posting_date") and self.docstatus < 2:
				expiry_date = frappe.get_cached_value("Batch", d.get("batch_no"), "expiry_date")

				if expiry_date and getdate(expiry_date) < getdate(self.posting_date):
					frappe.throw(
						_("Row #{0}: The batch {1} has already expired.").format(
							d.idx, get_link_to_form("Batch", d.get("batch_no"))
						),
						BatchExpiredError,
					)

	def clean_serial_nos(self):
		from erpnext.stock.doctype.serial_no.serial_no import clean_serial_no_string

		for row in self.get("items"):
			if hasattr(row, "serial_no") and row.serial_no:
				# remove extra whitespace and store one serial no on each line
				row.serial_no = clean_serial_no_string(row.serial_no)

		for row in self.get("packed_items") or []:
			if hasattr(row, "serial_no") and row.serial_no:
				# remove extra whitespace and store one serial no on each line
				row.serial_no = clean_serial_no_string(row.serial_no)

	def make_bundle_using_old_serial_batch_fields(self, table_name=None, via_landed_cost_voucher=False):
		if self.get("_action") == "update_after_submit":
			return

		# To handle test cases
		if frappe.flags.in_test and frappe.flags.use_serial_and_batch_fields:
			return

		if not table_name:
			table_name = "items"

		if self.doctype == "Asset Capitalization":
			table_name = "stock_items"

		for row in self.get(table_name):
			if row.serial_and_batch_bundle and (row.serial_no or row.batch_no):
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
					"posting_date": self.posting_date,
					"posting_time": self.posting_time,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"voucher_detail_no": row.name,
					"company": self.company,
					"is_rejected": 1 if row.get("rejected_warehouse") else 0,
					"use_serial_batch_fields": row.use_serial_batch_fields,
					"via_landed_cost_voucher": via_landed_cost_voucher,
					"do_not_submit": True if not via_landed_cost_voucher else False,
				}

				if row.get("qty") or row.get("consumed_qty") or row.get("stock_qty"):
					self.update_bundle_details(bundle_details, table_name, row)
					self.create_serial_batch_bundle(bundle_details, row)

				if row.get("rejected_qty"):
					self.update_bundle_details(bundle_details, table_name, row, is_rejected=True)
					self.create_serial_batch_bundle(bundle_details, row)

	def make_bundle_for_sales_purchase_return(self, table_name=None):
		if not self.get("is_return"):
			return

		if not table_name:
			table_name = "items"

		self.make_bundle_for_non_rejected_qty(table_name)

		if self.doctype in ["Purchase Invoice", "Purchase Receipt"]:
			self.make_bundle_for_rejected_qty(table_name)

	def make_bundle_for_rejected_qty(self, table_name=None):
		field, reference_ids = self.get_reference_ids(
			table_name, "rejected_qty", "rejected_serial_and_batch_bundle"
		)

		if not reference_ids:
			return

		child_doctype = self.doctype + " Item"
		available_dict = available_serial_batch_for_return(
			field, child_doctype, reference_ids, is_rejected=True
		)

		for row in self.get(table_name):
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
					self, data, row, warehouse_field=warehouse_field, qty_field=qty_field
				)
				bundle = make_serial_batch_bundle_for_return(data, row, self, warehouse_field, qty_field)
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

		child_doctype = self.doctype + " Item"
		available_dict = available_serial_batch_for_return(field, child_doctype, reference_ids)

		for row in self.get(table_name):
			if data := available_dict.get(row.get(field)):
				data = filter_serial_batches(self, data, row)
				bundle = make_serial_batch_bundle_for_return(data, row, self)
				row.db_set(
					{
						"serial_and_batch_bundle": bundle,
						"batch_no": "",
						"serial_no": "",
					}
				)

	def get_reference_ids(self, table_name, qty_field=None, bundle_field=None) -> tuple[str, list[str]]:
		field = {
			"Sales Invoice": "sales_invoice_item",
			"Delivery Note": "dn_detail",
			"Purchase Receipt": "purchase_receipt_item",
			"Purchase Invoice": "purchase_invoice_item",
			"POS Invoice": "pos_invoice_item",
		}.get(self.doctype)

		if not bundle_field:
			bundle_field = "serial_and_batch_bundle"

		if not qty_field:
			qty_field = "qty"

		reference_ids = []

		for row in self.get(table_name):
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

		return field, reference_ids

	@frappe.request_cache
	def is_serial_batch_item(self, item_code) -> bool:
		item_details = frappe.db.get_value("Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=1)

		if item_details.has_serial_no or item_details.has_batch_no:
			return True

		return False

	def update_bundle_details(self, bundle_details, table_name, row, is_rejected=False):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		# Since qty field is different for different doctypes
		qty = row.get("qty")
		warehouse = row.get("warehouse")

		if table_name == "packed_items":
			type_of_transaction = "Inward"
			if not self.is_return:
				type_of_transaction = "Outward"
		elif table_name == "supplied_items":
			qty = row.consumed_qty
			warehouse = self.supplier_warehouse
			type_of_transaction = "Outward"
			if self.is_return:
				type_of_transaction = "Inward"
		else:
			type_of_transaction = get_type_of_transaction(self, row)

		if hasattr(row, "stock_qty"):
			qty = row.stock_qty

		if self.doctype == "Stock Entry":
			qty = row.transfer_qty
			warehouse = row.s_warehouse or row.t_warehouse

		serial_nos = row.serial_no
		if is_rejected:
			serial_nos = row.get("rejected_serial_no")
			type_of_transaction = "Inward" if not self.is_return else "Outward"
			qty = row.get("rejected_qty")
			warehouse = row.get("rejected_warehouse")

		if (
			self.is_internal_transfer()
			and self.doctype in ["Sales Invoice", "Delivery Note"]
			and self.is_return
		):
			warehouse = row.get("target_warehouse") or row.get("warehouse")
			type_of_transaction = "Outward"

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
			batches = frappe.get_all(
				"Serial and Batch Entry", fields=["batch_no"], filters={"parent": row.serial_and_batch_bundle}
			)
			batches = sorted([d.batch_no for d in batches])

			if batches != [row.batch_no]:
				throw_error = True

		if throw_error:
			frappe.throw(
				_(
					"At row {0}: Serial and Batch Bundle {1} has already created. Please remove the values from the serial no or batch no fields."
				).format(row.idx, row.serial_and_batch_bundle)
			)

	def set_use_serial_batch_fields(self):
		if frappe.db.get_single_value("Stock Settings", "use_serial_batch_fields"):
			for row in self.items:
				row.use_serial_batch_fields = 1

	def get_gl_entries(self, warehouse_account=None, default_expense_account=None, default_cost_center=None):
		if not warehouse_account:
			warehouse_account = get_warehouse_account_map(self.company)

		sle_map = self.get_stock_ledger_details()
		voucher_details = self.get_voucher_details(default_expense_account, default_cost_center, sle_map)

		gl_list = []
		warehouse_with_no_account = []
		precision = self.get_debit_field_precision()
		for item_row in voucher_details:
			sle_list = sle_map.get(item_row.name)
			sle_rounding_diff = 0.0
			if sle_list:
				for sle in sle_list:
					if warehouse_account.get(sle.warehouse):
						# from warehouse account

						sle_rounding_diff += flt(sle.stock_value_difference)

						self.check_expense_account(item_row)

						# expense account/ target_warehouse / source_warehouse
						if item_row.get("target_warehouse"):
							warehouse = item_row.get("target_warehouse")
							expense_account = warehouse_account[warehouse]["account"]
						else:
							expense_account = item_row.expense_account

						gl_list.append(
							self.get_gl_dict(
								{
									"account": warehouse_account[sle.warehouse]["account"],
									"against": expense_account,
									"cost_center": item_row.cost_center,
									"project": item_row.project or self.get("project"),
									"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
									"debit": flt(sle.stock_value_difference, precision),
									"is_opening": item_row.get("is_opening")
									or self.get("is_opening")
									or "No",
								},
								warehouse_account[sle.warehouse]["account_currency"],
								item=item_row,
							)
						)

						gl_list.append(
							self.get_gl_dict(
								{
									"account": expense_account,
									"against": warehouse_account[sle.warehouse]["account"],
									"cost_center": item_row.cost_center,
									"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
									"debit": -1 * flt(sle.stock_value_difference, precision),
									"project": item_row.get("project") or self.get("project"),
									"is_opening": item_row.get("is_opening")
									or self.get("is_opening")
									or "No",
								},
								item=item_row,
							)
						)
					elif sle.warehouse not in warehouse_with_no_account:
						warehouse_with_no_account.append(sle.warehouse)

			if abs(sle_rounding_diff) > (1.0 / (10**precision)) and self.is_internal_transfer():
				warehouse_asset_account = ""
				if self.get("is_internal_customer"):
					warehouse_asset_account = warehouse_account[item_row.get("target_warehouse")]["account"]
				elif self.get("is_internal_supplier"):
					warehouse_asset_account = warehouse_account[item_row.get("warehouse")]["account"]

				expense_account = frappe.get_cached_value("Company", self.company, "default_expense_account")
				if not expense_account:
					frappe.throw(
						_(
							"Please set default cost of goods sold account in company {0} for booking rounding gain and loss during stock transfer"
						).format(frappe.bold(self.company))
					)

				gl_list.append(
					self.get_gl_dict(
						{
							"account": expense_account,
							"against": warehouse_asset_account,
							"cost_center": item_row.cost_center,
							"project": item_row.project or self.get("project"),
							"remarks": _("Rounding gain/loss Entry for Stock Transfer"),
							"debit": sle_rounding_diff,
							"is_opening": item_row.get("is_opening") or self.get("is_opening") or "No",
						},
						warehouse_account[sle.warehouse]["account_currency"],
						item=item_row,
					)
				)

				gl_list.append(
					self.get_gl_dict(
						{
							"account": warehouse_asset_account,
							"against": expense_account,
							"cost_center": item_row.cost_center,
							"remarks": _("Rounding gain/loss Entry for Stock Transfer"),
							"credit": sle_rounding_diff,
							"project": item_row.get("project") or self.get("project"),
							"is_opening": item_row.get("is_opening") or self.get("is_opening") or "No",
						},
						item=item_row,
					)
				)

		if warehouse_with_no_account:
			for wh in warehouse_with_no_account:
				if frappe.get_cached_value("Warehouse", wh, "company"):
					frappe.throw(
						_(
							"Warehouse {0} is not linked to any account, please mention the account in the warehouse record or set default inventory account in company {1}."
						).format(wh, self.company)
					)

		return process_gl_map(gl_list, precision=precision)

	def get_debit_field_precision(self):
		if not frappe.flags.debit_field_precision:
			frappe.flags.debit_field_precision = frappe.get_precision("GL Entry", "debit_in_account_currency")

		return frappe.flags.debit_field_precision

	def get_voucher_details(self, default_expense_account, default_cost_center, sle_map):
		if self.doctype == "Stock Reconciliation":
			reconciliation_purpose = frappe.db.get_value(self.doctype, self.name, "purpose")
			is_opening = "Yes" if reconciliation_purpose == "Opening Stock" else "No"
			details = []
			for voucher_detail_no in sle_map:
				details.append(
					frappe._dict(
						{
							"name": voucher_detail_no,
							"expense_account": default_expense_account,
							"cost_center": default_cost_center,
							"is_opening": is_opening,
						}
					)
				)
			return details
		else:
			details = self.get("items")

			if default_expense_account or default_cost_center:
				for d in details:
					if default_expense_account and not d.get("expense_account"):
						d.expense_account = default_expense_account
					if default_cost_center and not d.get("cost_center"):
						d.cost_center = default_cost_center

			return details

	def get_items_and_warehouses(self) -> tuple[list[str], list[str]]:
		"""Get list of items and warehouses affected by a transaction"""

		if not (hasattr(self, "items") or hasattr(self, "packed_items")):
			return [], []

		item_rows = (self.get("items") or []) + (self.get("packed_items") or [])

		items = {d.item_code for d in item_rows if d.item_code}

		warehouses = set()
		for d in item_rows:
			if d.get("warehouse"):
				warehouses.add(d.warehouse)

			if self.doctype == "Stock Entry":
				if d.get("s_warehouse"):
					warehouses.add(d.s_warehouse)
				if d.get("t_warehouse"):
					warehouses.add(d.t_warehouse)

		return list(items), list(warehouses)

	def get_stock_ledger_details(self):
		stock_ledger = {}
		stock_ledger_entries = frappe.db.sql(
			"""
			select
				name, warehouse, stock_value_difference, valuation_rate,
				voucher_detail_no, item_code, posting_date, posting_time,
				actual_qty, qty_after_transaction
			from
				`tabStock Ledger Entry`
			where
				voucher_type=%s and voucher_no=%s and is_cancelled = 0
		""",
			(self.doctype, self.name),
			as_dict=True,
		)

		for sle in stock_ledger_entries:
			stock_ledger.setdefault(sle.voucher_detail_no, []).append(sle)
		return stock_ledger

	def check_expense_account(self, item):
		if not item.get("expense_account"):
			msg = _("Please set an Expense Account in the Items table")
			frappe.throw(
				_("Row #{0}: Expense Account not set for the Item {1}. {2}").format(
					item.idx, frappe.bold(item.item_code), msg
				),
				title=_("Expense Account Missing"),
			)

		else:
			is_expense_account = (
				frappe.get_cached_value("Account", item.get("expense_account"), "report_type")
				== "Profit and Loss"
			)
			if (
				self.doctype
				not in (
					"Purchase Receipt",
					"Purchase Invoice",
					"Stock Reconciliation",
					"Stock Entry",
					"Subcontracting Receipt",
				)
				and not is_expense_account
			):
				frappe.throw(
					_("Expense / Difference account ({0}) must be a 'Profit or Loss' account").format(
						item.get("expense_account")
					)
				)
			if is_expense_account and not item.get("cost_center"):
				frappe.throw(
					_("{0} {1}: Cost Center is mandatory for Item {2}").format(
						_(self.doctype), self.name, item.get("item_code")
					)
				)

	def delete_auto_created_batches(self):
		for table_name in ["items", "packed_items", "supplied_items"]:
			if not self.get(table_name):
				continue

			for row in self.get(table_name):
				update_values = {}
				if row.get("batch_no"):
					update_values["batch_no"] = None

				if row.serial_and_batch_bundle:
					update_values["serial_and_batch_bundle"] = None
					frappe.db.set_value(
						"Serial and Batch Bundle", row.serial_and_batch_bundle, {"is_cancelled": 1}
					)

				if update_values:
					row.db_set(update_values)

				if table_name == "items" and row.get("rejected_serial_and_batch_bundle"):
					frappe.db.set_value(
						"Serial and Batch Bundle", row.rejected_serial_and_batch_bundle, {"is_cancelled": 1}
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

		for row in self.get(table_name):
			for field in QTY_FIELD.keys():
				if row.get(field):
					frappe.get_doc("Serial and Batch Bundle", row.get(field)).set_serial_and_batch_values(
						self, row, qty_field=QTY_FIELD[field]
					)

	def make_package_for_transfer(
		self, serial_and_batch_bundle, warehouse, type_of_transaction=None, do_not_submit=None
	):
		return make_bundle_for_material_transfer(
			is_new=self.is_new(),
			docstatus=self.docstatus,
			voucher_type=self.doctype,
			voucher_no=self.name,
			serial_and_batch_bundle=serial_and_batch_bundle,
			warehouse=warehouse,
			type_of_transaction=type_of_transaction,
			do_not_submit=do_not_submit,
		)

	def get_sl_entries(self, d, args):
		sl_dict = frappe._dict(
			{
				"item_code": d.get("item_code", None),
				"warehouse": d.get("warehouse", None),
				"serial_and_batch_bundle": d.get("serial_and_batch_bundle"),
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"fiscal_year": get_fiscal_year(self.posting_date, company=self.company)[0],
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"voucher_detail_no": d.name,
				"actual_qty": (self.docstatus == 1 and 1 or -1) * flt(d.get("stock_qty")),
				"stock_uom": frappe.get_cached_value(
					"Item", args.get("item_code") or d.get("item_code"), "stock_uom"
				),
				"incoming_rate": 0,
				"company": self.company,
				"project": d.get("project") or self.get("project"),
				"is_cancelled": 1 if self.docstatus == 2 else 0,
			}
		)

		sl_dict.update(args)
		self.update_inventory_dimensions(d, sl_dict)

		if self.docstatus == 2:
			# To handle denormalized serial no records, will br deprecated in v16
			for field in ["serial_no", "batch_no"]:
				if d.get(field):
					sl_dict[field] = d.get(field)

		return sl_dict

	def update_inventory_dimensions(self, row, sl_dict) -> None:
		# To handle delivery note and sales invoice
		if row.get("item_row"):
			row = row.get("item_row")

		dimensions = get_evaluated_inventory_dimension(row, sl_dict, parent_doc=self)
		for dimension in dimensions:
			if not dimension:
				continue

			if self.doctype in [
				"Purchase Invoice",
				"Purchase Receipt",
				"Sales Invoice",
				"Delivery Note",
				"Stock Entry",
			]:
				if (
					(
						sl_dict.actual_qty > 0
						and not self.get("is_return")
						or sl_dict.actual_qty < 0
						and self.get("is_return")
					)
					and self.doctype in ["Purchase Invoice", "Purchase Receipt"]
				) or (
					(
						sl_dict.actual_qty < 0
						and not self.get("is_return")
						or sl_dict.actual_qty > 0
						and self.get("is_return")
					)
					and self.doctype in ["Sales Invoice", "Delivery Note", "Stock Entry"]
				):
					sl_dict[dimension.target_fieldname] = row.get(dimension.source_fieldname)
				else:
					fieldname_start_with = "to"
					if self.doctype in ["Purchase Invoice", "Purchase Receipt"]:
						fieldname_start_with = "from"

					fieldname = f"{fieldname_start_with}_{dimension.source_fieldname}"
					sl_dict[dimension.target_fieldname] = row.get(fieldname)

					if not sl_dict.get(dimension.target_fieldname):
						sl_dict[dimension.target_fieldname] = row.get(dimension.source_fieldname)

			elif row.get(dimension.source_fieldname):
				sl_dict[dimension.target_fieldname] = row.get(dimension.source_fieldname)

			if not sl_dict.get(dimension.target_fieldname) and dimension.fetch_from_parent:
				sl_dict[dimension.target_fieldname] = self.get(dimension.fetch_from_parent)

				# Get value based on doctype name
				if not sl_dict.get(dimension.target_fieldname):
					fieldname = next(
						(
							field.fieldname
							for field in frappe.get_meta(self.doctype).fields
							if field.options == dimension.fetch_from_parent
						),
						None,
					)

					if fieldname and self.get(fieldname):
						sl_dict[dimension.target_fieldname] = self.get(fieldname)

				if sl_dict[dimension.target_fieldname] and self.docstatus == 1:
					row.db_set(dimension.source_fieldname, sl_dict[dimension.target_fieldname])

	def make_sl_entries(self, sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
		from erpnext.stock.stock_ledger import make_sl_entries

		make_sl_entries(sl_entries, allow_negative_stock, via_landed_cost_voucher)

	def make_gl_entries_on_cancel(self):
		cancel_exchange_gain_loss_journal(frappe._dict(doctype=self.doctype, name=self.name))
		if frappe.db.sql(
			"""select name from `tabGL Entry` where voucher_type=%s
			and voucher_no=%s""",
			(self.doctype, self.name),
		):
			self.make_gl_entries()

	def get_serialized_items(self):
		serialized_items = []
		item_codes = list(set(d.item_code for d in self.get("items")))
		if item_codes:
			serialized_items = frappe.db.sql_list(
				"""select name from `tabItem`
				where has_serial_no=1 and name in ({})""".format(", ".join(["%s"] * len(item_codes))),
				tuple(item_codes),
			)

		return serialized_items

	def validate_warehouse(self):
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		warehouses = list(set(d.warehouse for d in self.get("items") if getattr(d, "warehouse", None)))

		target_warehouses = list(
			set([d.target_warehouse for d in self.get("items") if getattr(d, "target_warehouse", None)])
		)

		warehouses.extend(target_warehouses)

		from_warehouse = list(
			set([d.from_warehouse for d in self.get("items") if getattr(d, "from_warehouse", None)])
		)

		warehouses.extend(from_warehouse)

		for w in warehouses:
			validate_disabled_warehouse(w)
			validate_warehouse_company(w, self.company)

	def update_billing_percentage(self, update_modified=True):
		target_ref_field = "amount"
		if self.doctype == "Delivery Note":
			target_ref_field = "amount - (returned_qty * rate)"

		self._update_percent_field(
			{
				"target_dt": self.doctype + " Item",
				"target_parent_dt": self.doctype,
				"target_parent_field": "per_billed",
				"target_ref_field": target_ref_field,
				"target_field": "billed_amt",
				"name": self.name,
			},
			update_modified,
		)

	def validate_inspection(self):
		"""Checks if quality inspection is set/ is valid for Items that require inspection."""
		inspection_fieldname_map = {
			"Purchase Receipt": "inspection_required_before_purchase",
			"Purchase Invoice": "inspection_required_before_purchase",
			"Subcontracting Receipt": "inspection_required_before_purchase",
			"Sales Invoice": "inspection_required_before_delivery",
			"Delivery Note": "inspection_required_before_delivery",
		}
		inspection_required_fieldname = inspection_fieldname_map.get(self.doctype)

		# return if inspection is not required on document level
		if (
			(not inspection_required_fieldname and self.doctype != "Stock Entry")
			or (self.doctype == "Stock Entry" and not self.inspection_required)
			or (self.doctype in ["Sales Invoice", "Purchase Invoice"] and not self.update_stock)
		):
			return

		for row in self.get("items"):
			qi_required = False
			if inspection_required_fieldname and frappe.db.get_value(
				"Item", row.item_code, inspection_required_fieldname
			):
				qi_required = True
			elif self.doctype == "Stock Entry" and row.t_warehouse:
				qi_required = True  # inward stock needs inspection

			if qi_required:  # validate row only if inspection is required on item level
				self.validate_qi_presence(row)
				if self.docstatus == 1:
					self.validate_qi_submission(row)
					self.validate_qi_rejection(row)

	def validate_qi_presence(self, row):
		"""Check if QI is present on row level. Warn on save and stop on submit if missing."""
		if not row.quality_inspection:
			msg = f"Row #{row.idx}: Quality Inspection is required for Item {frappe.bold(row.item_code)}"
			if self.docstatus == 1:
				frappe.throw(_(msg), title=_("Inspection Required"), exc=QualityInspectionRequiredError)
			else:
				frappe.msgprint(_(msg), title=_("Inspection Required"), indicator="blue")

	def validate_qi_submission(self, row):
		"""Check if QI is submitted on row level, during submission"""
		action = frappe.db.get_single_value("Stock Settings", "action_if_quality_inspection_is_not_submitted")
		qa_docstatus = frappe.db.get_value("Quality Inspection", row.quality_inspection, "docstatus")

		if not qa_docstatus == 1:
			link = frappe.utils.get_link_to_form("Quality Inspection", row.quality_inspection)
			msg = f"Row #{row.idx}: Quality Inspection {link} is not submitted for the item: {row.item_code}"
			if action == "Stop":
				frappe.throw(_(msg), title=_("Inspection Submission"), exc=QualityInspectionNotSubmittedError)
			else:
				frappe.msgprint(_(msg), alert=True, indicator="orange")

	def validate_qi_rejection(self, row):
		"""Check if QI is rejected on row level, during submission"""
		action = frappe.db.get_single_value("Stock Settings", "action_if_quality_inspection_is_rejected")
		qa_status = frappe.db.get_value("Quality Inspection", row.quality_inspection, "status")

		if qa_status == "Rejected":
			link = frappe.utils.get_link_to_form("Quality Inspection", row.quality_inspection)
			msg = f"Row #{row.idx}: Quality Inspection {link} was rejected for item {row.item_code}"
			if action == "Stop":
				frappe.throw(_(msg), title=_("Inspection Rejected"), exc=QualityInspectionRejectedError)
			else:
				frappe.msgprint(_(msg), alert=True, indicator="orange")

	def update_blanket_order(self):
		blanket_orders = list(set([d.blanket_order for d in self.items if d.blanket_order]))
		for blanket_order in blanket_orders:
			frappe.get_doc("Blanket Order", blanket_order).update_ordered_qty()

	def validate_customer_provided_item(self):
		for d in self.get("items"):
			# Customer Provided parts will have zero valuation rate
			if frappe.get_cached_value("Item", d.item_code, "is_customer_provided_item"):
				d.allow_zero_valuation_rate = 1

	def set_rate_of_stock_uom(self):
		if self.doctype in [
			"Purchase Receipt",
			"Purchase Invoice",
			"Purchase Order",
			"Sales Invoice",
			"Sales Order",
			"Delivery Note",
			"Quotation",
		]:
			for d in self.get("items"):
				d.stock_uom_rate = d.rate / (d.conversion_factor or 1)

	def validate_internal_transfer(self):
		if self.doctype in ("Sales Invoice", "Delivery Note", "Purchase Invoice", "Purchase Receipt"):
			if self.is_internal_transfer():
				self.validate_in_transit_warehouses()
				self.validate_multi_currency()
				self.validate_packed_items()

				if self.get("is_internal_supplier") and self.docstatus == 1:
					self.validate_internal_transfer_qty()
			else:
				self.validate_internal_transfer_warehouse()

	def validate_internal_transfer_warehouse(self):
		for row in self.items:
			if row.get("target_warehouse"):
				row.target_warehouse = None

			if row.get("from_warehouse"):
				row.from_warehouse = None

	def validate_in_transit_warehouses(self):
		if (self.doctype == "Sales Invoice" and self.get("update_stock")) or self.doctype == "Delivery Note":
			for item in self.get("items"):
				if not item.target_warehouse:
					frappe.throw(
						_("Row {0}: Target Warehouse is mandatory for internal transfers").format(item.idx)
					)

		if (
			self.doctype == "Purchase Invoice" and self.get("update_stock")
		) or self.doctype == "Purchase Receipt":
			for item in self.get("items"):
				if not item.from_warehouse:
					frappe.throw(
						_("Row {0}: From Warehouse is mandatory for internal transfers").format(item.idx)
					)

	def validate_multi_currency(self):
		if self.currency != self.company_currency:
			frappe.throw(_("Internal transfers can only be done in company's default currency"))

	def validate_packed_items(self):
		if self.doctype in ("Sales Invoice", "Delivery Note Item") and self.get("packed_items"):
			frappe.throw(_("Packed Items cannot be transferred internally"))

	def validate_internal_transfer_qty(self):
		if self.doctype not in ["Purchase Invoice", "Purchase Receipt"]:
			return

		item_wise_transfer_qty = self.get_item_wise_inter_transfer_qty()
		if not item_wise_transfer_qty:
			return

		item_wise_received_qty = self.get_item_wise_inter_received_qty()
		precision = frappe.get_precision(self.doctype + " Item", "qty")

		over_receipt_allowance = frappe.db.get_single_value(
			"Stock Settings", "over_delivery_receipt_allowance"
		)

		parent_doctype = {
			"Purchase Receipt": "Delivery Note",
			"Purchase Invoice": "Sales Invoice",
		}.get(self.doctype)

		for key, transferred_qty in item_wise_transfer_qty.items():
			recevied_qty = flt(item_wise_received_qty.get(key), precision)
			if over_receipt_allowance:
				transferred_qty = transferred_qty + flt(
					transferred_qty * over_receipt_allowance / 100, precision
				)

			if recevied_qty > flt(transferred_qty, precision):
				frappe.throw(
					_("For Item {0} cannot be received more than {1} qty against the {2} {3}").format(
						bold(key[1]),
						bold(flt(transferred_qty, precision)),
						bold(parent_doctype),
						get_link_to_form(parent_doctype, self.get("inter_company_reference")),
					)
				)

	def get_item_wise_inter_transfer_qty(self):
		reference_field = "inter_company_reference"
		if self.doctype == "Purchase Invoice":
			reference_field = "inter_company_invoice_reference"

		parent_doctype = {
			"Purchase Receipt": "Delivery Note",
			"Purchase Invoice": "Sales Invoice",
		}.get(self.doctype)

		child_doctype = parent_doctype + " Item"

		parent_tab = frappe.qb.DocType(parent_doctype)
		child_tab = frappe.qb.DocType(child_doctype)

		query = (
			frappe.qb.from_(parent_doctype)
			.inner_join(child_tab)
			.on(child_tab.parent == parent_tab.name)
			.select(
				child_tab.name,
				child_tab.item_code,
				child_tab.qty,
			)
			.where((parent_tab.name == self.get(reference_field)) & (parent_tab.docstatus == 1))
		)

		data = query.run(as_dict=True)
		item_wise_transfer_qty = defaultdict(float)
		for row in data:
			item_wise_transfer_qty[(row.name, row.item_code)] += flt(row.qty)

		return item_wise_transfer_qty

	def get_item_wise_inter_received_qty(self):
		child_doctype = self.doctype + " Item"

		parent_tab = frappe.qb.DocType(self.doctype)
		child_tab = frappe.qb.DocType(child_doctype)

		query = (
			frappe.qb.from_(self.doctype)
			.inner_join(child_tab)
			.on(child_tab.parent == parent_tab.name)
			.select(
				child_tab.item_code,
				child_tab.qty,
			)
			.where(parent_tab.docstatus < 2)
		)

		if self.doctype == "Purchase Invoice":
			query = query.select(
				child_tab.sales_invoice_item.as_("name"),
			)

			query = query.where(
				parent_tab.inter_company_invoice_reference == self.inter_company_invoice_reference
			)
		else:
			query = query.select(
				child_tab.delivery_note_item.as_("name"),
			)

			query = query.where(parent_tab.inter_company_reference == self.inter_company_reference)

		data = query.run(as_dict=True)
		item_wise_transfer_qty = defaultdict(float)
		for row in data:
			item_wise_transfer_qty[(row.name, row.item_code)] += flt(row.qty)

		return item_wise_transfer_qty

	def validate_putaway_capacity(self):
		# if over receipt is attempted while 'apply putaway rule' is disabled
		# and if rule was applied on the transaction, validate it.
		from erpnext.stock.doctype.putaway_rule.putaway_rule import get_available_putaway_capacity

		valid_doctype = self.doctype in (
			"Purchase Receipt",
			"Stock Entry",
			"Purchase Invoice",
			"Stock Reconciliation",
		)

		if not frappe.get_all("Putaway Rule", limit=1):
			return

		if self.doctype == "Purchase Invoice" and self.get("update_stock") == 0:
			valid_doctype = False

		if valid_doctype:
			rule_map = defaultdict(dict)
			for item in self.get("items"):
				warehouse_field = "t_warehouse" if self.doctype == "Stock Entry" else "warehouse"
				rule = frappe.db.get_value(
					"Putaway Rule",
					{"item_code": item.get("item_code"), "warehouse": item.get(warehouse_field)},
					["name", "disable"],
					as_dict=True,
				)
				if rule:
					if rule.get("disabled"):
						continue  # dont validate for disabled rule

					if self.doctype == "Stock Reconciliation":
						stock_qty = flt(item.qty)
					else:
						stock_qty = (
							flt(item.transfer_qty) if self.doctype == "Stock Entry" else flt(item.stock_qty)
						)

					rule_name = rule.get("name")
					if not rule_map[rule_name]:
						rule_map[rule_name]["warehouse"] = item.get(warehouse_field)
						rule_map[rule_name]["item"] = item.get("item_code")
						rule_map[rule_name]["qty_put"] = 0
						rule_map[rule_name]["capacity"] = get_available_putaway_capacity(rule_name)
					rule_map[rule_name]["qty_put"] += flt(stock_qty)

			for rule, values in rule_map.items():
				if flt(values["qty_put"]) > flt(values["capacity"]):
					message = self.prepare_over_receipt_message(rule, values)
					frappe.throw(msg=message, title=_("Over Receipt"))

	def prepare_over_receipt_message(self, rule, values):
		message = _("{0} qty of Item {1} is being received into Warehouse {2} with capacity {3}.").format(
			frappe.bold(values["qty_put"]),
			frappe.bold(values["item"]),
			frappe.bold(values["warehouse"]),
			frappe.bold(values["capacity"]),
		)
		message += "<br><br>"
		rule_link = frappe.utils.get_link_to_form("Putaway Rule", rule)
		message += _("Please adjust the qty or edit {0} to proceed.").format(rule_link)
		return message

	def repost_future_sle_and_gle(self, force=False, via_landed_cost_voucher=False):
		args = frappe._dict(
			{
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"company": self.company,
				"via_landed_cost_voucher": via_landed_cost_voucher,
			}
		)

		if self.docstatus == 2:
			force = True

		if force or future_sle_exists(args) or repost_required_for_queue(self):
			item_based_reposting = cint(
				frappe.db.get_single_value("Stock Reposting Settings", "item_based_reposting")
			)
			if item_based_reposting:
				create_item_wise_repost_entries(
					voucher_type=self.doctype,
					voucher_no=self.name,
					via_landed_cost_voucher=via_landed_cost_voucher,
				)
			else:
				create_repost_item_valuation_entry(args)

	def add_gl_entry(
		self,
		gl_entries,
		account,
		cost_center,
		debit,
		credit,
		remarks,
		against_account,
		debit_in_account_currency=None,
		credit_in_account_currency=None,
		account_currency=None,
		project=None,
		voucher_detail_no=None,
		item=None,
		posting_date=None,
	):
		gl_entry = {
			"account": account,
			"cost_center": cost_center,
			"debit": debit,
			"credit": credit,
			"against": against_account,
			"remarks": remarks,
		}

		if voucher_detail_no:
			gl_entry.update({"voucher_detail_no": voucher_detail_no})

		if debit_in_account_currency:
			gl_entry.update({"debit_in_account_currency": debit_in_account_currency})

		if credit_in_account_currency:
			gl_entry.update({"credit_in_account_currency": credit_in_account_currency})

		if posting_date:
			gl_entry.update({"posting_date": posting_date})

		gl_entries.append(self.get_gl_dict(gl_entry, item=item))


@frappe.whitelist()
def show_accounting_ledger_preview(company, doctype, docname):
	filters = frappe._dict(company=company, include_dimensions=1)
	doc = frappe.get_doc(doctype, docname)
	doc.run_method("before_gl_preview")

	gl_columns, gl_data = get_accounting_ledger_preview(doc, filters)

	frappe.db.rollback()

	return {"gl_columns": gl_columns, "gl_data": gl_data}


@frappe.whitelist()
def show_stock_ledger_preview(company, doctype, docname):
	filters = frappe._dict(company=company)
	doc = frappe.get_doc(doctype, docname)
	doc.run_method("before_sl_preview")

	sl_columns, sl_data = get_stock_ledger_preview(doc, filters)

	frappe.db.rollback()

	return {
		"sl_columns": sl_columns,
		"sl_data": sl_data,
	}


def get_accounting_ledger_preview(doc, filters):
	from erpnext.accounts.report.general_ledger.general_ledger import get_columns as get_gl_columns

	gl_columns, gl_data = [], []
	fields = [
		"posting_date",
		"account",
		"debit",
		"credit",
		"against",
		"party_type",
		"party",
		"cost_center",
		"against_voucher_type",
		"against_voucher",
	]

	doc.docstatus = 1

	if doc.get("update_stock") or doc.doctype in ("Purchase Receipt", "Delivery Note"):
		doc.update_stock_ledger()

	doc.make_gl_entries()
	columns = get_gl_columns(filters)
	gl_entries = get_gl_entries_for_preview(doc.doctype, doc.name, fields)

	gl_columns = get_columns(columns, fields)
	gl_data = get_data(fields, gl_entries)

	return gl_columns, gl_data


def get_stock_ledger_preview(doc, filters):
	from erpnext.stock.report.stock_ledger.stock_ledger import get_columns as get_sl_columns

	sl_columns, sl_data = [], []
	fields = [
		"item_code",
		"stock_uom",
		"actual_qty",
		"qty_after_transaction",
		"warehouse",
		"incoming_rate",
		"valuation_rate",
		"stock_value",
		"stock_value_difference",
	]
	columns_fields = [
		"item_code",
		"stock_uom",
		"in_qty",
		"out_qty",
		"qty_after_transaction",
		"warehouse",
		"incoming_rate",
		"in_out_rate",
		"stock_value",
		"stock_value_difference",
	]

	if doc.get("update_stock") or doc.doctype in ("Purchase Receipt", "Delivery Note"):
		doc.docstatus = 1
		doc.update_stock_ledger()
		columns = get_sl_columns(filters)
		sl_entries = get_sl_entries_for_preview(doc.doctype, doc.name, fields)

		sl_columns = get_columns(columns, columns_fields)
		sl_data = get_data(columns_fields, sl_entries)

	return sl_columns, sl_data


def get_sl_entries_for_preview(doctype, docname, fields):
	sl_entries = frappe.get_all(
		"Stock Ledger Entry", filters={"voucher_type": doctype, "voucher_no": docname}, fields=fields
	)

	for entry in sl_entries:
		if entry.actual_qty > 0:
			entry["in_qty"] = entry.actual_qty
			entry["out_qty"] = 0
		else:
			entry["out_qty"] = abs(entry.actual_qty)
			entry["in_qty"] = 0

		entry["in_out_rate"] = entry["valuation_rate"]

	return sl_entries


def get_gl_entries_for_preview(doctype, docname, fields):
	return frappe.get_all("GL Entry", filters={"voucher_type": doctype, "voucher_no": docname}, fields=fields)


def get_columns(raw_columns, fields):
	return [
		{"name": d.get("label"), "editable": False, "width": 110}
		for d in raw_columns
		if not d.get("hidden") and d.get("fieldname") in fields
	]


def get_data(raw_columns, raw_data):
	datatable_data = []
	for row in raw_data:
		data_row = []
		for column in raw_columns:
			data_row.append(row.get(column) or "")

		datatable_data.append(data_row)

	return datatable_data


def repost_required_for_queue(doc: StockController) -> bool:
	"""check if stock document contains repeated item-warehouse with queue based valuation.

	if queue exists for repeated items then SLEs need to reprocessed in background again.
	"""

	consuming_sles = frappe.db.get_all(
		"Stock Ledger Entry",
		filters={
			"voucher_type": doc.doctype,
			"voucher_no": doc.name,
			"actual_qty": ("<", 0),
			"is_cancelled": 0,
		},
		fields=["item_code", "warehouse", "stock_queue"],
	)
	item_warehouses = [(sle.item_code, sle.warehouse) for sle in consuming_sles]

	unique_item_warehouses = set(item_warehouses)

	if len(unique_item_warehouses) == len(item_warehouses):
		return False

	for sle in consuming_sles:
		if sle.stock_queue != "[]":  # using FIFO/LIFO valuation
			return True
	return False


@frappe.whitelist()
def make_quality_inspections(doctype, docname, items):
	if isinstance(items, str):
		items = json.loads(items)

	inspections = []
	for item in items:
		if flt(item.get("sample_size")) > flt(item.get("qty")):
			frappe.throw(
				_(
					"{item_name}'s Sample Size ({sample_size}) cannot be greater than the Accepted Quantity ({accepted_quantity})"
				).format(
					item_name=item.get("item_name"),
					sample_size=item.get("sample_size"),
					accepted_quantity=item.get("qty"),
				)
			)

		quality_inspection = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"inspected_by": frappe.session.user,
				"reference_type": doctype,
				"reference_name": docname,
				"item_code": item.get("item_code"),
				"description": item.get("description"),
				"sample_size": flt(item.get("sample_size")),
				"item_serial_no": item.get("serial_no").split("\n")[0] if item.get("serial_no") else None,
				"batch_no": item.get("batch_no"),
			}
		).insert()
		quality_inspection.save()
		inspections.append(quality_inspection.name)

	return inspections


def is_reposting_pending():
	return frappe.db.exists(
		"Repost Item Valuation", {"docstatus": 1, "status": ["in", ["Queued", "In Progress"]]}
	)


def future_sle_exists(args, sl_entries=None, allow_force_reposting=True):
	if allow_force_reposting and frappe.db.get_single_value(
		"Stock Reposting Settings", "do_reposting_for_each_stock_transaction"
	):
		return True

	key = (args.voucher_type, args.voucher_no)
	if not hasattr(frappe.local, "future_sle"):
		frappe.local.future_sle = {}

	if validate_future_sle_not_exists(args, key, sl_entries):
		return False
	elif get_cached_data(args, key):
		return True

	if not sl_entries:
		sl_entries = get_sle_entries_against_voucher(args)
		if not sl_entries:
			return

	or_conditions = get_conditions_to_validate_future_sle(sl_entries)

	data = frappe.db.sql(
		"""
		select item_code, warehouse, count(name) as total_row
		from `tabStock Ledger Entry` force index (item_warehouse)
		where
			({})
			and timestamp(posting_date, posting_time)
				>= timestamp(%(posting_date)s, %(posting_time)s)
			and voucher_no != %(voucher_no)s
			and is_cancelled = 0
		GROUP BY
			item_code, warehouse
		""".format(" or ".join(or_conditions)),
		args,
		as_dict=1,
	)

	for d in data:
		frappe.local.future_sle[key][(d.item_code, d.warehouse)] = d.total_row

	return len(data)


def validate_future_sle_not_exists(args, key, sl_entries=None):
	item_key = ""
	if args.get("item_code"):
		item_key = (args.get("item_code"), args.get("warehouse"))

	if not sl_entries and hasattr(frappe.local, "future_sle"):
		if key not in frappe.local.future_sle:
			return False

		if not frappe.local.future_sle.get(key) or (
			item_key and item_key not in frappe.local.future_sle.get(key)
		):
			return True


def get_cached_data(args, key):
	if key not in frappe.local.future_sle:
		frappe.local.future_sle[key] = frappe._dict({})

	if args.get("item_code"):
		item_key = (args.get("item_code"), args.get("warehouse"))
		count = frappe.local.future_sle[key].get(item_key)

		return True if (count or count == 0) else False
	else:
		return frappe.local.future_sle[key]


def get_sle_entries_against_voucher(args):
	return frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_type": args.voucher_type, "voucher_no": args.voucher_no},
		fields=["item_code", "warehouse"],
		order_by="creation asc",
	)


def get_conditions_to_validate_future_sle(sl_entries):
	warehouse_items_map = {}
	for entry in sl_entries:
		if entry.warehouse not in warehouse_items_map:
			warehouse_items_map[entry.warehouse] = set()

		warehouse_items_map[entry.warehouse].add(entry.item_code)

	or_conditions = []
	for warehouse, items in warehouse_items_map.items():
		or_conditions.append(
			f"""warehouse = {frappe.db.escape(warehouse)}
				and item_code in ({', '.join(frappe.db.escape(item) for item in items)})"""
		)

	return or_conditions


def create_repost_item_valuation_entry(args):
	args = frappe._dict(args)
	repost_entry = frappe.new_doc("Repost Item Valuation")
	repost_entry.based_on = args.based_on
	if not args.based_on:
		repost_entry.based_on = "Transaction" if args.voucher_no else "Item and Warehouse"
	repost_entry.voucher_type = args.voucher_type
	repost_entry.voucher_no = args.voucher_no
	repost_entry.item_code = args.item_code
	repost_entry.warehouse = args.warehouse
	repost_entry.posting_date = args.posting_date
	repost_entry.posting_time = args.posting_time
	repost_entry.company = args.company
	repost_entry.allow_zero_rate = args.allow_zero_rate
	repost_entry.flags.ignore_links = True
	repost_entry.flags.ignore_permissions = True
	repost_entry.via_landed_cost_voucher = args.via_landed_cost_voucher
	repost_entry.save()
	repost_entry.submit()


def create_item_wise_repost_entries(
	voucher_type, voucher_no, allow_zero_rate=False, via_landed_cost_voucher=False
):
	"""Using a voucher create repost item valuation records for all item-warehouse pairs."""

	stock_ledger_entries = get_items_to_be_repost(voucher_type, voucher_no)

	distinct_item_warehouses = set()
	repost_entries = []

	for sle in stock_ledger_entries:
		item_wh = (sle.item_code, sle.warehouse)
		if item_wh in distinct_item_warehouses:
			continue
		distinct_item_warehouses.add(item_wh)

		repost_entry = frappe.new_doc("Repost Item Valuation")
		repost_entry.based_on = "Item and Warehouse"

		repost_entry.item_code = sle.item_code
		repost_entry.warehouse = sle.warehouse
		repost_entry.posting_date = sle.posting_date
		repost_entry.posting_time = sle.posting_time
		repost_entry.allow_zero_rate = allow_zero_rate
		repost_entry.flags.ignore_links = True
		repost_entry.flags.ignore_permissions = True
		repost_entry.via_landed_cost_voucher = via_landed_cost_voucher
		repost_entry.submit()
		repost_entries.append(repost_entry)

	return repost_entries


def make_bundle_for_material_transfer(**kwargs):
	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	bundle_doc = frappe.get_doc("Serial and Batch Bundle", kwargs.serial_and_batch_bundle)

	if not kwargs.type_of_transaction:
		kwargs.type_of_transaction = "Inward"

	bundle_doc = frappe.copy_doc(bundle_doc)
	bundle_doc.warehouse = kwargs.warehouse
	bundle_doc.type_of_transaction = kwargs.type_of_transaction
	bundle_doc.voucher_type = kwargs.voucher_type
	bundle_doc.voucher_no = "" if kwargs.is_new or kwargs.docstatus == 2 else kwargs.voucher_no
	bundle_doc.is_cancelled = 0

	for row in bundle_doc.entries:
		row.is_outward = 0
		row.qty = abs(row.qty)
		row.stock_value_difference = abs(row.stock_value_difference)
		if kwargs.type_of_transaction == "Outward":
			row.qty *= -1
			row.stock_value_difference *= row.stock_value_difference
			row.is_outward = 1

		row.warehouse = kwargs.warehouse

	bundle_doc.calculate_qty_and_amount()
	bundle_doc.flags.ignore_permissions = True
	bundle_doc.flags.ignore_validate = True
	bundle_doc.save(ignore_permissions=True)

	return bundle_doc.name
