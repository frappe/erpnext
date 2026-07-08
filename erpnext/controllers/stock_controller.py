# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _, bold
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Count
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate

import erpnext
from erpnext.accounts.general_ledger import (
	make_gl_entries,
	make_reverse_gl_entries,
)
from erpnext.accounts.utils import cancel_exchange_gain_loss_journal
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.controllers.sales_and_purchase_return import (
	available_serial_batch_for_return,
	filter_serial_batches,
	make_serial_batch_bundle_for_return,
)

# Re-exported for backward compatibility; canonical home is erpnext.exceptions.
from erpnext.exceptions import (
	BatchExpiredError,
	QualityInspectionNotSubmittedError,
	QualityInspectionRejectedError,
	QualityInspectionRequiredError,
)
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.services.internal_transfer import StockInternalTransferService
from erpnext.stock.stock_ledger import get_items_to_be_repost


class StockController(AccountsController):
	def validate(self):
		from erpnext.stock.doctype.putaway_rule.putaway_rule import validate_putaway_capacity
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService

		sbb = SerialBatchBundleService(self)

		super().validate()

		if self.docstatus == 0:
			for table_name in ["items", "packed_items", "supplied_items"]:
				sbb.validate_duplicate_serial_and_batch_bundle(table_name)

		if not self.get("is_return"):
			self.validate_inspection()

		sbb.validate_warehouse_of_sabb()
		sbb.validate_serialized_batch()
		sbb.clean_serial_nos()
		self.validate_customer_provided_item()
		self.set_rate_of_stock_uom()
		StockInternalTransferService(self).validate_internal_transfer()
		validate_putaway_capacity(self)
		self.reset_conversion_factor()

	def on_update(self):
		super().on_update()
		self.check_zero_rate()

	def reset_conversion_factor(self):
		for row in self.get("items"):
			if row.uom != row.stock_uom:
				continue

			if row.conversion_factor != 1.0:
				row.conversion_factor = 1.0
				frappe.msgprint(
					_(
						"Conversion factor for item {0} has been reset to 1.0 as the uom {1} is same as stock uom {2}."
					).format(bold(row.item_code), bold(row.uom), bold(row.stock_uom)),
					alert=True,
				)

	def check_zero_rate(self):
		if self.doctype in [
			"POS Invoice",
			"Purchase Invoice",
			"Sales Invoice",
			"Delivery Note",
			"Purchase Receipt",
			"Stock Entry",
			"Stock Reconciliation",
		]:
			for item in self.get("items"):
				if (
					(
						item.get("valuation_rate") == 0
						or (item.get("incoming_rate") == 0 and self.get("update_stock", 1))
					)
					and item.get("allow_zero_valuation_rate") == 0
					and frappe.get_cached_value("Item", item.item_code, "is_stock_item")
				):
					frappe.toast(
						_("Row #{0}: Item {1} has zero rate but '{2}' is not enabled.").format(
							item.idx,
							frappe.bold(item.item_code),
							item.meta.get_label("allow_zero_valuation_rate"),
						),
						indicator="orange",
					)

	def validate_items_exist(self):
		if not self.get("items"):
			return

		items = [d.item_code for d in self.get("items")]

		exists_items = frappe.get_all("Item", filters={"name": ("in", items)}, pluck="name")
		non_exists_items = set(items) - set(exists_items)

		if non_exists_items:
			frappe.throw(_("Items {0} do not exist in the Item master.").format(", ".join(non_exists_items)))

	def get_item_wise_inventory_account_map(self):
		inventory_account_map = frappe._dict()
		for table in ["items", "packed_items", "supplied_items"]:
			if not self.get(table):
				continue

			_map = get_item_wise_inventory_account_map(self.get(table), self.company)
			inventory_account_map.update(_map)

		return inventory_account_map

	@property
	def use_item_inventory_account(self):
		return frappe.get_cached_value("Company", self.company, "enable_item_wise_inventory_account")

	def get_inventory_account_dict(self, row, inventory_account_map, warehouse_field=None):
		account_dict = frappe._dict()

		if isinstance(row, dict):
			row = frappe._dict(row)

		if self.use_item_inventory_account:
			item_code = (
				row.rm_item_code if hasattr(row, "rm_item_code") and row.rm_item_code else row.item_code
			)

			account_dict = inventory_account_map.get(item_code)

			if not account_dict:
				frappe.throw(
					_(
						"Please set default inventory account for item {0}, or their item group or brand."
					).format(bold(item_code))
				)

			return account_dict

		if not warehouse_field:
			warehouse_field = "warehouse"

		warehouse = row.get(warehouse_field)
		if not warehouse:
			warehouse = self.get(warehouse_field)

		if warehouse and warehouse in inventory_account_map:
			account_dict = inventory_account_map[warehouse]

		return account_dict

	def get_inventory_account_map(self):
		if self.use_item_inventory_account:
			return self.get_item_wise_inventory_account_map()

		return get_warehouse_account_map(self.company)

	def make_gl_entries(self, gl_entries=None, from_repost=False, via_landed_cost_voucher=False):
		if self.docstatus == 2:
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

		provisional_accounting_for_non_stock_items = cint(
			frappe.get_cached_value(
				"Company", self.company, "enable_provisional_accounting_for_non_stock_items"
			)
		)

		is_asset_pr = any(d.get("is_fixed_asset") for d in self.get("items"))
		need_inventory_map = (self.get_stock_items() or self.get("packed_items")) and (
			cint(erpnext.is_perpetual_inventory_enabled(self.company))
		)

		inventory_account_map = frappe._dict()
		if need_inventory_map:
			inventory_account_map = self.get_inventory_account_map()

		if need_inventory_map or provisional_accounting_for_non_stock_items or is_asset_pr:
			if self.docstatus == 1:
				if not gl_entries:
					gl_entries = (
						self.get_gl_entries(inventory_account_map, via_landed_cost_voucher)
						if self.doctype == "Purchase Receipt"
						else self.get_gl_entries(inventory_account_map)
					)
				make_gl_entries(gl_entries, from_repost=from_repost)

	def make_bundle_using_old_serial_batch_fields(self, table_name=None, via_landed_cost_voucher=False):
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService

		return SerialBatchBundleService(self).make_bundle_using_old_serial_batch_fields(
			table_name, via_landed_cost_voucher
		)

	def make_bundle_for_sales_purchase_return(self, table_name=None):
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService

		return SerialBatchBundleService(self).make_bundle_for_sales_purchase_return(table_name)

	def set_use_serial_batch_fields(self):
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService

		return SerialBatchBundleService(self).set_use_serial_batch_fields()

	def get_gl_entries(
		self, inventory_account_map=None, default_expense_account=None, default_cost_center=None
	):
		from erpnext.stock.services.base_stock_gl_composer import BaseStockGLComposer

		return BaseStockGLComposer(self).compose(
			inventory_account_map, default_expense_account, default_cost_center
		)

	def get_items_and_warehouses(self) -> tuple[list[str], list[str]]:
		from erpnext.stock.services.stock_ledger_service import StockLedgerService

		return StockLedgerService(self).get_items_and_warehouses()

	def get_stock_ledger_details(self):
		from erpnext.stock.services.stock_ledger_service import StockLedgerService

		return StockLedgerService(self).get_stock_ledger_details()

	def delete_auto_created_batches(self):
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService

		return SerialBatchBundleService(self).delete_auto_created_batches()

	def set_serial_and_batch_bundle(self, table_name=None, ignore_validate=False):
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService

		return SerialBatchBundleService(self).set_serial_and_batch_bundle(table_name, ignore_validate)

	def make_package_for_transfer(
		self, serial_and_batch_bundle, warehouse, type_of_transaction=None, do_not_submit=None, qty=0
	):
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService

		return SerialBatchBundleService(self).make_package_for_transfer(
			serial_and_batch_bundle, warehouse, type_of_transaction, do_not_submit, qty
		)

	def get_sl_entries(self, d, args):
		from erpnext.stock.services.stock_ledger_service import StockLedgerService

		return StockLedgerService(self).get_sl_entries(d, args)

	def get_item_account_wise_lcv_entries(self):
		from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import (
			get_item_account_wise_lcv_entries,
		)

		return get_item_account_wise_lcv_entries(self)

	def make_sl_entries(self, sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
		from erpnext.stock.services.stock_ledger_service import StockLedgerService

		return StockLedgerService(self).make_sl_entries(
			sl_entries, allow_negative_stock, via_landed_cost_voucher
		)

	def make_gl_entries_on_cancel(self, from_repost=False):
		if not from_repost:
			cancel_exchange_gain_loss_journal(frappe._dict(doctype=self.doctype, name=self.name))
		if frappe.db.exists("GL Entry", {"voucher_type": self.doctype, "voucher_no": self.name}):
			self.make_gl_entries()

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
			total_amount = total_returned = 0
			for item in self.items:
				total_amount += flt(item.amount)
				total_returned += flt(item.returned_qty * item.rate)

			if total_returned < total_amount:
				target_ref_field = {"SUB": ["amount", {"MUL": ["returned_qty", "rate"]}], "as": "ref_amount"}

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
		from erpnext.stock.services.quality_inspection_service import QualityInspectionService

		return QualityInspectionService(self).validate_inspection()

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

	def repost_future_sle_and_gle(self, force=False, via_landed_cost_voucher=False):
		from erpnext.stock.services.stock_ledger_service import StockLedgerService

		return StockLedgerService(self).repost_future_sle_and_gle(force, via_landed_cost_voucher)

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
		from erpnext.accounts.services.base_gl_composer import add_gl_entry

		add_gl_entry(
			self,
			gl_entries,
			account,
			cost_center,
			debit,
			credit,
			remarks,
			against_account,
			debit_in_account_currency,
			credit_in_account_currency,
			account_currency,
			project,
			voucher_detail_no,
			item,
			posting_date,
		)

	def update_stock_reservation_entries(self):
		def get_sre_list():
			table = frappe.qb.DocType("Stock Reservation Entry")
			query = (
				frappe.qb.from_(table)
				.select(table.name)
				.where(
					(table.docstatus == 1)
					& (table.voucher_type == data_map[purpose or self.doctype]["voucher_type"])
					& (
						table.voucher_no
						== data_map[purpose or self.doctype].get(
							"voucher_no", item.get("subcontracting_order")
						)
					)
				)
				.orderby(table.creation)
			)
			if reference_field := data_map[purpose or self.doctype].get("voucher_detail_no_field"):
				query = query.where(table.voucher_detail_no == item.get(reference_field))
			else:
				query = query.where(
					(table.item_code == item.rm_item_code) & (table.warehouse == self.supplier_warehouse)
				)

			return query.run(pluck="name")

		def get_data_map():
			return {
				"Subcontracting Delivery": {
					"table_name": "items",
					"voucher_type": "Subcontracting Inward Order",
					"voucher_no": self.get("subcontracting_inward_order"),
					"voucher_detail_no_field": "scio_detail",
					"field": "delivered_qty",
				},
				"Send to Subcontractor": {
					"table_name": "items",
					"voucher_type": "Subcontracting Order",
					"voucher_no": self.get("subcontracting_order"),
					"voucher_detail_no_field": "sco_rm_detail",
					"field": "transferred_qty",
				},
				"Subcontracting Receipt": {
					"table_name": "supplied_items",
					"voucher_type": "Subcontracting Order",
					"field": "consumed_qty",
				},
			}

		purpose = self.get("purpose")
		if (
			purpose == "Subcontracting Delivery"
			or (
				purpose == "Send to Subcontractor"
				and frappe.get_value("Subcontracting Order", self.subcontracting_order, "reserve_stock")
			)
			or (self.doctype == "Subcontracting Receipt" and self.has_reserved_stock() and not self.is_return)
		):
			data_map = get_data_map()

			field = data_map[purpose or self.doctype]["field"]
			for item in self.get(data_map[purpose or self.doctype]["table_name"]):
				sre_list = get_sre_list()

				if not sre_list:
					continue

				qty = item.get("transfer_qty", item.get("consumed_qty"))
				for sre in sre_list:
					if qty <= 0:
						break

					sre_doc = frappe.get_doc("Stock Reservation Entry", sre)

					working_qty = 0
					if sre_doc.reservation_based_on == "Serial and Batch":
						sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
						if sre_doc.has_serial_no:
							serial_nos = [d.serial_no for d in sbb.entries]
							for entry in sre_doc.sb_entries:
								if entry.serial_no in serial_nos:
									entry.delivered_qty = 1 if self._action == "submit" else 0
									entry.db_update()
									working_qty += 1
									serial_nos.remove(entry.serial_no)
						else:
							batch_qty = {d.batch_no: -1 * d.qty for d in sbb.entries}
							for entry in sre_doc.sb_entries:
								if entry.batch_no in batch_qty:
									delivered_qty = min(
										(entry.qty - entry.delivered_qty)
										if self._action == "submit"
										else entry.delivered_qty,
										batch_qty[entry.batch_no],
									)
									entry.delivered_qty += (
										delivered_qty if self._action == "submit" else (-1 * delivered_qty)
									)
									entry.db_update()
									working_qty += delivered_qty
									batch_qty[entry.batch_no] -= delivered_qty
					else:
						working_qty = min(
							(sre_doc.reserved_qty - sre_doc.get(field))
							if self._action == "submit"
							else sre_doc.get(field),
							qty,
						)

					sre_doc.set(
						field,
						sre_doc.get(field)
						+ (working_qty if self._action == "submit" else (-1 * working_qty)),
					)
					sre_doc.db_update()
					sre_doc.update_reserved_qty_in_voucher()
					sre_doc.update_status()
					sre_doc.update_reserved_stock_in_bin()

					qty -= working_qty

	def check_for_on_hold_or_closed_status(
		self, ref_doctype: str, ref_fieldname: str, exclude_if_field: str | None = None
	) -> None:
		def _include(d):
			return d.get(ref_fieldname) and not (exclude_if_field and d.get(exclude_if_field))

		included = [(d, d.get(ref_fieldname)) for d in self.get("items") if _include(d)]
		if not included:
			return

		status_map = {
			r.name: r.status
			for r in frappe.get_all(
				ref_doctype,
				filters={"name": ["in", {name for _, name in included}]},
				fields=["name", "status"],
			)
		}

		errors = []
		seen = set()
		for _d, ref_name in included:
			if ref_name in seen:
				continue
			seen.add(ref_name)
			if (status := status_map.get(ref_name)) in ("Closed", "On Hold"):
				errors.append(
					_("{ref_doctype} {ref_name} status is {status}.").format(
						ref_doctype=frappe.bold(_(ref_doctype)),
						ref_name=frappe.bold(ref_name),
						status=frappe.bold(_(status)),
					)
				)

		if errors:
			frappe.throw("<br>".join(errors), frappe.InvalidStatusError)


@frappe.whitelist()
def show_accounting_ledger_preview(company: str, doctype: str, docname: str):
	from erpnext.controllers.ledger_preview import get_accounting_ledger_preview

	filters = frappe._dict(company=company, include_dimensions=1)
	doc = frappe.get_lazy_doc(doctype, docname)
	doc.run_method("before_gl_preview")

	gl_columns, gl_data = get_accounting_ledger_preview(doc, filters)

	frappe.db.rollback()

	return {"gl_columns": gl_columns, "gl_data": gl_data}


@frappe.whitelist()
def show_stock_ledger_preview(company: str, doctype: str, docname: str):
	from erpnext.controllers.ledger_preview import get_stock_ledger_preview

	filters = frappe._dict(company=company)
	doc = frappe.get_lazy_doc(doctype, docname)
	doc.run_method("before_sl_preview")

	sl_columns, sl_data = get_stock_ledger_preview(doc, filters)

	frappe.db.rollback()

	return {
		"sl_columns": sl_columns,
		"sl_data": sl_data,
	}


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
def check_item_quality_inspection(doctype: str, docstatus: str | int, items: str | list[dict]):
	from erpnext.stock.services.quality_inspection_service import INSPECTION_FIELDNAME_MAP

	items = frappe.parse_json(items)

	inspection_fieldname = INSPECTION_FIELDNAME_MAP.get(doctype)
	if inspection_fieldname is None:
		return items if doctype == "Stock Entry" else []

	allow_after_transaction = cint(docstatus) == 1 and frappe.get_single_value(
		"Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery"
	)

	if allow_after_transaction:
		return items

	item_codes = list({item.get("item_code") for item in items})

	Item = frappe.qb.DocType("Item")
	results = (
		frappe.qb.from_(Item)
		.select(Item.name)
		.where((Item.name.isin(item_codes)) & (Item[inspection_fieldname] == 1))
		.run(as_dict=True)
	)

	inspection_required_items = {row.name for row in results}

	return [item for item in items if item.get("item_code") in inspection_required_items]


@frappe.whitelist(methods=["POST"])
def make_quality_inspections(
	company: str, doctype: str, docname: str, items: str | list, inspection_type: str
):
	items = frappe.parse_json(items)

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
				"company": company,
				"doctype": "Quality Inspection",
				"inspection_type": inspection_type,
				"inspected_by": frappe.session.user,
				"reference_type": doctype,
				"reference_name": docname,
				"item_code": item.get("item_code"),
				"description": item.get("description"),
				"sample_size": flt(item.get("sample_size")),
				"item_serial_no": item.get("serial_no").split("\n")[0] if item.get("serial_no") else None,
				"batch_no": item.get("batch_no"),
				"child_row_reference": item.get("child_row_reference"),
			}
		)
		quality_inspection.save()
		inspections.append(quality_inspection.name)

	return inspections


def is_reposting_pending():
	return frappe.db.exists(
		"Repost Item Valuation", {"docstatus": 1, "status": ["in", ["Queued", "In Progress"]]}
	)


def future_sle_exists(args, sl_entries=None):
	from erpnext.stock.utils import get_combine_datetime

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

	args["posting_datetime"] = get_combine_datetime(args["posting_date"], args["posting_time"])

	sle = frappe.qb.DocType("Stock Ledger Entry")
	data = (
		frappe.qb.from_(sle)
		.select(sle.item_code, sle.warehouse, Count(sle.name).as_("total_row"))
		.where(
			Criterion.any(or_conditions)
			& (sle.posting_datetime >= args["posting_datetime"])
			& (sle.voucher_no != args["voucher_no"])
			& (sle.is_cancelled == 0)
		)
		.groupby(sle.item_code, sle.warehouse)
		.run(as_dict=1)
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

	sle = frappe.qb.DocType("Stock Ledger Entry")
	or_conditions = []
	for warehouse, items in warehouse_items_map.items():
		or_conditions.append((sle.warehouse == warehouse) & sle.item_code.isin(list(items)))

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

	from erpnext.stock.utils import get_valuation_method

	stock_ledger_entries = get_items_to_be_repost(voucher_type, voucher_no)

	distinct_item_warehouses = set()
	repost_entries = []

	for sle in stock_ledger_entries:
		item_wh = (sle.item_code, sle.warehouse)
		if item_wh in distinct_item_warehouses:
			continue
		distinct_item_warehouses.add(item_wh)

		# Standard Cost items don't need a full repost: a backdated entry only shifts future balances
		# (qty and value at the standard rate), which is done in place by update_qty_in_future_sle.
		if get_valuation_method(sle.item_code) == "Standard Cost":
			continue

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
	bundle_doc.docstatus = 0
	bundle_doc.warehouse = kwargs.warehouse
	bundle_doc.type_of_transaction = kwargs.type_of_transaction
	bundle_doc.voucher_type = kwargs.voucher_type
	bundle_doc.voucher_no = "" if kwargs.is_new or kwargs.docstatus == 2 else kwargs.voucher_no
	bundle_doc.is_cancelled = 0

	qty = 0
	if (
		len(bundle_doc.entries) == 1
		and flt(kwargs.qty) < flt(bundle_doc.total_qty)
		and not bundle_doc.has_serial_no
	):
		qty = kwargs.qty

	for row in bundle_doc.entries:
		row.is_outward = 0
		row.qty = abs(qty or row.qty)
		row.stock_value_difference = abs(row.stock_value_difference)
		if kwargs.type_of_transaction == "Outward":
			row.qty *= -1
			row.stock_value_difference *= row.stock_value_difference
			row.is_outward = 1

		row.warehouse = kwargs.warehouse
		row.posting_datetime = bundle_doc.posting_datetime
		row.voucher_type = bundle_doc.voucher_type
		row.voucher_no = bundle_doc.voucher_no
		row.voucher_detail_no = bundle_doc.voucher_detail_no
		row.type_of_transaction = bundle_doc.type_of_transaction
		row.item_code = bundle_doc.item_code

	bundle_doc.set_incoming_rate()
	bundle_doc.calculate_qty_and_amount()
	bundle_doc.flags.ignore_permissions = True
	bundle_doc.flags.ignore_validate = True
	if kwargs.do_not_submit:
		bundle_doc.save(ignore_permissions=True)
	else:
		bundle_doc.submit()

	return bundle_doc.name


def get_item_wise_inventory_account_map(rows, company):
	# returns dict of item_code and its inventory account details
	# Example: {"ITEM-001": {"account": "Stock - ABC", "account_currency": "INR"}, ...}

	inventory_map = frappe._dict()

	for row in rows:
		item_code = row.rm_item_code if hasattr(row, "rm_item_code") and row.rm_item_code else row.item_code
		if not item_code:
			continue

		if inventory_map.get(item_code):
			continue

		item_defaults = get_item_defaults(item_code, company)
		if item_defaults.default_inventory_account:
			inventory_map[item_code] = frappe._dict(
				{
					"account": item_defaults.default_inventory_account,
					"account_currency": item_defaults.inventory_account_currency,
				}
			)

		if not inventory_map.get(item_code):
			item_group_defaults = get_item_group_defaults(item_code, company)
			if item_group_defaults.default_inventory_account:
				inventory_map[item_code] = frappe._dict(
					{
						"account": item_group_defaults.default_inventory_account,
						"account_currency": item_group_defaults.inventory_account_currency,
					}
				)

		if not inventory_map.get(item_code):
			brand_defaults = get_brand_defaults(item_code, company)
			if brand_defaults.default_inventory_account:
				inventory_map[item_code] = frappe._dict(
					{
						"account": brand_defaults.default_inventory_account,
						"account_currency": brand_defaults.inventory_account_currency,
					}
				)

	return inventory_map
