# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, bold, json, msgprint
from frappe.query_builder.functions import CombineDatetime, Sum
from frappe.utils import add_to_date, cint, cstr, flt

import erpnext
from erpnext.accounts.utils import get_company_default
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.doctype.batch.batch import get_available_batches, get_batch_qty
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	get_available_serial_nos,
)
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.utils import get_incoming_rate, get_stock_balance


class OpeningEntryAccountError(frappe.ValidationError):
	pass


class EmptyStockReconciliationItemsError(frappe.ValidationError):
	pass


class StockReconciliation(StockController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.stock_reconciliation_item.stock_reconciliation_item import (
			StockReconciliationItem,
		)

		amended_from: DF.Link | None
		company: DF.Link
		cost_center: DF.Link | None
		difference_amount: DF.Currency
		expense_account: DF.Link | None
		items: DF.Table[StockReconciliationItem]
		naming_series: DF.Literal["MAT-RECO-.YYYY.-"]
		posting_date: DF.Date
		posting_time: DF.Time
		purpose: DF.Literal["", "Opening Stock", "Stock Reconciliation"]
		scan_barcode: DF.Data | None
		scan_mode: DF.Check
		set_posting_time: DF.Check
		set_warehouse: DF.Link | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.head_row = ["Item Code", "Warehouse", "Quantity", "Valuation Rate"]

	def validate(self):
		self.validate_items_exist()
		if not self.expense_account:
			self.expense_account = frappe.get_cached_value(
				"Company", self.company, "stock_adjustment_account"
			)
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
		self.validate_posting_time()
		self.set_current_serial_and_batch_bundle()
		self.set_new_serial_and_batch_bundle()
		self.validate_duplicate_serial_and_batch_bundle("items")
		self.remove_items_with_no_change()
		self.validate_data()
		self.validate_expense_account()
		self.validate_customer_provided_item()
		self.set_zero_value_for_customer_provided_items()
		self.clean_serial_nos()
		self.set_total_qty_and_amount()
		self.validate_putaway_capacity()
		self.validate_inventory_dimension()

		if self._action == "submit":
			self.validate_reserved_stock()

	def on_update(self):
		self.set_serial_and_batch_bundle(ignore_validate=True)

	def validate_inventory_dimension(self):
		dimensions = get_inventory_dimensions()
		for dimension in dimensions:
			for row in self.items:
				if not row.batch_no and row.current_qty and row.get(dimension.get("fieldname")):
					frappe.throw(
						_(
							"Row #{0}: You cannot use the inventory dimension '{1}' in Stock Reconciliation to modify the quantity or valuation rate. Stock reconciliation with inventory dimensions is intended solely for performing opening entries."
						).format(row.idx, bold(dimension.get("doctype")))
					)

	def on_submit(self):
		self.make_bundle_for_current_qty()
		self.make_bundle_using_old_serial_batch_fields()
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()

	def on_cancel(self):
		self.validate_reserved_stock()
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Serial and Batch Bundle",
		)
		self.make_sle_on_cancel()
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.delete_auto_created_batches()

	def make_bundle_for_current_qty(self):
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		for row in self.items:
			if not row.use_serial_batch_fields:
				continue

			if row.current_serial_and_batch_bundle:
				continue

			if row.current_qty and (row.current_serial_no or row.batch_no):
				sn_doc = SerialBatchCreation(
					{
						"item_code": row.item_code,
						"warehouse": row.warehouse,
						"posting_date": self.posting_date,
						"posting_time": self.posting_time,
						"voucher_type": self.doctype,
						"voucher_no": self.name,
						"voucher_detail_no": row.name,
						"qty": row.current_qty,
						"type_of_transaction": "Outward",
						"company": self.company,
						"is_rejected": 0,
						"serial_nos": get_serial_nos(row.current_serial_no)
						if row.current_serial_no
						else None,
						"batches": frappe._dict({row.batch_no: row.current_qty}) if row.batch_no else None,
						"batch_no": row.batch_no,
						"do_not_submit": True,
					}
				).make_serial_and_batch_bundle()

				row.current_serial_and_batch_bundle = sn_doc.name
				row.db_set(
					{
						"current_serial_and_batch_bundle": sn_doc.name,
						"current_serial_no": "",
					}
				)

	def set_current_serial_and_batch_bundle(self, voucher_detail_no=None, save=False) -> None:
		"""Set Serial and Batch Bundle for each item"""
		for item in self.items:
			if not frappe.db.exists("Item", item.item_code):
				frappe.throw(_("Item {0} does not exist").format(item.item_code))

			if not item.reconcile_all_serial_batch and item.serial_and_batch_bundle:
				bundle = self.get_bundle_for_specific_serial_batch(item)
				item.current_serial_and_batch_bundle = bundle.name
				item.current_valuation_rate = abs(bundle.avg_rate)

				if not item.valuation_rate:
					item.valuation_rate = item.current_valuation_rate
				continue

			if not save and item.use_serial_batch_fields:
				continue

			if voucher_detail_no and voucher_detail_no != item.name:
				continue

			item_details = frappe.get_cached_value(
				"Item", item.item_code, ["has_serial_no", "has_batch_no"], as_dict=1
			)

			if not (item_details.has_serial_no or item_details.has_batch_no):
				continue

			if not item.current_serial_and_batch_bundle:
				serial_and_batch_bundle = frappe.get_doc(
					{
						"doctype": "Serial and Batch Bundle",
						"item_code": item.item_code,
						"warehouse": item.warehouse,
						"posting_date": self.posting_date,
						"posting_time": self.posting_time,
						"voucher_type": self.doctype,
						"type_of_transaction": "Outward",
					}
				)
			else:
				serial_and_batch_bundle = frappe.get_doc(
					"Serial and Batch Bundle", item.current_serial_and_batch_bundle
				)

				serial_and_batch_bundle.set("entries", [])

			if item_details.has_serial_no:
				serial_nos_details = get_available_serial_nos(
					frappe._dict(
						{
							"item_code": item.item_code,
							"warehouse": item.warehouse,
							"posting_date": self.posting_date,
							"posting_time": self.posting_time,
							"ignore_warehouse": 1,
						}
					)
				)

				for serial_no_row in serial_nos_details:
					serial_and_batch_bundle.append(
						"entries",
						{
							"serial_no": serial_no_row.serial_no,
							"qty": -1,
							"warehouse": serial_no_row.warehouse,
							"batch_no": serial_no_row.batch_no,
						},
					)

			elif item_details.has_batch_no:
				batch_nos_details = get_available_batches(
					frappe._dict(
						{
							"item_code": item.item_code,
							"warehouse": item.warehouse,
							"posting_date": self.posting_date,
							"posting_time": self.posting_time,
							"ignore_voucher_nos": [self.name],
						}
					)
				)

				for batch_no, qty in batch_nos_details.items():
					serial_and_batch_bundle.append(
						"entries",
						{
							"batch_no": batch_no,
							"qty": qty * -1,
							"warehouse": item.warehouse,
						},
					)

			if not serial_and_batch_bundle.entries:
				if voucher_detail_no:
					return

				continue

			serial_and_batch_bundle.save()
			item.current_serial_and_batch_bundle = serial_and_batch_bundle.name
			item.current_qty = abs(serial_and_batch_bundle.total_qty)
			item.current_valuation_rate = abs(serial_and_batch_bundle.avg_rate)
			if save:
				sle_creation = frappe.db.get_value(
					"Serial and Batch Bundle", item.serial_and_batch_bundle, "creation"
				)
				creation = add_to_date(sle_creation, seconds=-1)
				item.db_set(
					{
						"current_serial_and_batch_bundle": item.current_serial_and_batch_bundle,
						"current_qty": item.current_qty,
						"current_valuation_rate": item.current_valuation_rate,
						"creation": creation,
					}
				)

				serial_and_batch_bundle.db_set(
					{
						"creation": creation,
						"voucher_no": self.name,
						"voucher_detail_no": voucher_detail_no,
					}
				)

	def get_bundle_for_specific_serial_batch(self, row) -> str:
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		if row.current_serial_and_batch_bundle and not self.has_change_in_serial_batch(row):
			return frappe._dict(
				{
					"name": row.current_serial_and_batch_bundle,
					"avg_rate": row.current_valuation_rate,
				}
			)

		cls_obj = SerialBatchCreation(
			{
				"type_of_transaction": "Outward",
				"serial_and_batch_bundle": row.serial_and_batch_bundle,
				"item_code": row.get("item_code"),
				"warehouse": row.get("warehouse"),
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"do_not_save": True,
			}
		)

		reco_obj = cls_obj.duplicate_package()

		total_current_qty = 0.0
		for entry in reco_obj.entries:
			if not entry.batch_no or entry.serial_no:
				total_current_qty += entry.qty
				entry.qty *= -1
				continue

			current_qty = get_batch_qty(
				entry.batch_no,
				row.warehouse,
				row.item_code,
				posting_date=self.posting_date,
				posting_time=self.posting_time,
				for_stock_levels=True,
			)

			total_current_qty += current_qty
			entry.qty = current_qty * -1

		reco_obj.save()

		row.current_qty = total_current_qty

		return reco_obj

	def has_change_in_serial_batch(self, row) -> bool:
		bundles = {row.serial_and_batch_bundle: [], row.current_serial_and_batch_bundle: []}

		data = frappe.get_all(
			"Serial and Batch Entry",
			fields=["serial_no", "batch_no", "parent"],
			filters={"parent": ("in", [row.serial_and_batch_bundle, row.current_serial_and_batch_bundle])},
			order_by="idx",
		)

		for d in data:
			bundles[d.parent].append(d.serial_no or d.batch_no)

		diff = set(bundles[row.serial_and_batch_bundle]) - set(bundles[row.current_serial_and_batch_bundle])

		if diff:
			bundle = row.current_serial_and_batch_bundle
			row.current_serial_and_batch_bundle = None
			frappe.delete_doc("Serial and Batch Bundle", bundle)

			return True

		return False

	def set_new_serial_and_batch_bundle(self):
		for item in self.items:
			if not item.item_code:
				continue

			if item.use_serial_batch_fields:
				continue

			if not item.qty:
				continue

			if item.current_serial_and_batch_bundle and not item.serial_and_batch_bundle:
				current_doc = frappe.get_doc("Serial and Batch Bundle", item.current_serial_and_batch_bundle)

				item.qty = abs(current_doc.total_qty)
				item.valuation_rate = abs(current_doc.avg_rate)

				bundle_doc = frappe.copy_doc(current_doc)
				bundle_doc.warehouse = item.warehouse
				bundle_doc.type_of_transaction = "Inward"

				for row in bundle_doc.entries:
					if row.qty < 0:
						row.qty = abs(row.qty)

					if row.stock_value_difference < 0:
						row.stock_value_difference = abs(row.stock_value_difference)

					row.is_outward = 0

				bundle_doc.calculate_qty_and_amount()
				bundle_doc.flags.ignore_permissions = True
				bundle_doc.save()
				item.serial_and_batch_bundle = bundle_doc.name
			elif item.serial_and_batch_bundle and not item.qty and not item.valuation_rate:
				bundle_doc = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)

				item.qty = bundle_doc.total_qty
				item.valuation_rate = bundle_doc.avg_rate

	def remove_items_with_no_change(self):
		"""Remove items if qty or rate is not changed"""
		self.difference_amount = 0.0

		def _changed(item):
			if item.current_serial_and_batch_bundle:
				bundle_data = frappe.get_all(
					"Serial and Batch Bundle",
					filters={"name": item.current_serial_and_batch_bundle},
					fields=["total_qty as qty", "avg_rate as rate"],
				)[0]

				bundle_data.qty = abs(bundle_data.qty)
				self.calculate_difference_amount(item, bundle_data)

				return True

			inventory_dimensions_dict = {}
			if not item.batch_no and not item.serial_no:
				for dimension in get_inventory_dimensions():
					if item.get(dimension.get("fieldname")):
						inventory_dimensions_dict[dimension.get("fieldname")] = item.get(
							dimension.get("fieldname")
						)

			item_dict = get_stock_balance_for(
				item.item_code,
				item.warehouse,
				self.posting_date,
				self.posting_time,
				batch_no=item.batch_no,
				inventory_dimensions_dict=inventory_dimensions_dict,
				row=item,
			)

			if (
				(item.qty is None or item.qty == item_dict.get("qty"))
				and (item.valuation_rate is None or item.valuation_rate == item_dict.get("rate"))
				and (not item.serial_no or (item.serial_no == item_dict.get("serial_nos")))
			):
				return False
			else:
				# set default as current rates
				if item.qty is None:
					item.qty = item_dict.get("qty")

				if item.valuation_rate is None:
					item.valuation_rate = item_dict.get("rate")

				if item_dict.get("serial_nos"):
					item.current_serial_no = item_dict.get("serial_nos")
					if self.purpose == "Stock Reconciliation" and not item.serial_no and item.qty:
						item.serial_no = item.current_serial_no

				item.current_qty = item_dict.get("qty")
				item.current_valuation_rate = item_dict.get("rate")
				self.calculate_difference_amount(item, item_dict)
				return True

		items = list(filter(lambda d: _changed(d), self.items))

		if not items:
			frappe.throw(
				_("None of the items have any change in quantity or value."),
				EmptyStockReconciliationItemsError,
			)

		elif len(items) != len(self.items):
			self.items = items
			for i, item in enumerate(self.items):
				item.idx = i + 1
			frappe.msgprint(_("Removed items with no change in quantity or value."))

	def calculate_difference_amount(self, item, item_dict):
		qty_precision = item.precision("qty")
		val_precision = item.precision("valuation_rate")

		new_qty = flt(item.qty, qty_precision)
		new_valuation_rate = flt(item.valuation_rate or item_dict.get("rate"), val_precision)

		current_qty = flt(item_dict.get("qty"), qty_precision)
		current_valuation_rate = flt(item_dict.get("rate"), val_precision)

		self.difference_amount += (new_qty * new_valuation_rate) - (current_qty * current_valuation_rate)

	def validate_data(self):
		def _get_msg(row_num, msg):
			return _("Row # {0}:").format(row_num + 1) + " " + msg

		self.validation_messages = []
		item_warehouse_combinations = []

		default_currency = frappe.db.get_default("currency")

		for row_num, row in enumerate(self.items):
			# find duplicates
			key = [row.item_code, row.warehouse]
			for field in ["serial_no", "batch_no"]:
				if row.get(field):
					key.append(row.get(field))

			if key in item_warehouse_combinations:
				self.validation_messages.append(
					_get_msg(row_num, _("Same item and warehouse combination already entered."))
				)
			else:
				item_warehouse_combinations.append(key)

			self.validate_item(row.item_code, row)

			if row.serial_no and not row.qty:
				self.validation_messages.append(
					_get_msg(
						row_num,
						f"Quantity should not be zero for the {bold(row.item_code)} since serial nos are specified",
					)
				)

			# validate warehouse
			if not frappe.db.get_value("Warehouse", row.warehouse):
				self.validation_messages.append(_get_msg(row_num, _("Warehouse not found in the system")))

			# if both not specified
			if row.qty in ["", None] and row.valuation_rate in ["", None]:
				self.validation_messages.append(
					_get_msg(row_num, _("Please specify either Quantity or Valuation Rate or both"))
				)

			# do not allow negative quantity
			if flt(row.qty) < 0:
				self.validation_messages.append(_get_msg(row_num, _("Negative Quantity is not allowed")))

			# do not allow negative valuation
			if flt(row.valuation_rate) < 0:
				self.validation_messages.append(
					_get_msg(row_num, _("Negative Valuation Rate is not allowed"))
				)

			if row.qty and row.valuation_rate in ["", None]:
				row.valuation_rate = get_stock_balance(
					row.item_code,
					row.warehouse,
					self.posting_date,
					self.posting_time,
					with_valuation_rate=True,
				)[1]
				if not row.valuation_rate:
					# try if there is a buying price list in default currency
					buying_rate = frappe.db.get_value(
						"Item Price",
						{"item_code": row.item_code, "buying": 1, "currency": default_currency},
						"price_list_rate",
					)
					if buying_rate:
						row.valuation_rate = buying_rate

					else:
						# get valuation rate from Item
						row.valuation_rate = frappe.get_value("Item", row.item_code, "valuation_rate")

		# throw all validation messages
		if self.validation_messages:
			for msg in self.validation_messages:
				msgprint(msg)

			raise frappe.ValidationError(self.validation_messages)

	def validate_item(self, item_code, row):
		from erpnext.stock.doctype.item.item import (
			validate_cancelled_item,
			validate_end_of_life,
			validate_is_stock_item,
		)

		# using try except to catch all validation msgs and display together

		try:
			item = frappe.get_doc("Item", item_code)

			# end of life and stock item
			validate_end_of_life(item_code, item.end_of_life, item.disabled)
			validate_is_stock_item(item_code, item.is_stock_item)

			# docstatus should be < 2
			validate_cancelled_item(item_code, item.docstatus)

		except Exception as e:
			self.validation_messages.append(_("Row #") + " " + ("%d: " % (row.idx)) + cstr(e))

	def validate_reserved_stock(self) -> None:
		"""Raises an exception if there is any reserved stock for the items in the Stock Reconciliation."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_sre_reserved_qty_for_items_and_warehouses as get_sre_reserved_qty_details,
		)

		item_code_list, warehouse_list = [], []
		for item in self.items:
			item_code_list.append(item.item_code)
			warehouse_list.append(item.warehouse)

		sre_reserved_qty_details = get_sre_reserved_qty_details(item_code_list, warehouse_list)

		if sre_reserved_qty_details:
			data = []
			for (item_code, warehouse), reserved_qty in sre_reserved_qty_details.items():
				data.append([item_code, warehouse, reserved_qty])

			msg = ""
			if len(data) == 1:
				msg = _(
					"{0} units are reserved for Item {1} in Warehouse {2}, please un-reserve the same to {3} the Stock Reconciliation."
				).format(bold(data[0][2]), bold(data[0][0]), bold(data[0][1]), self._action)
			else:
				items_html = ""
				for d in data:
					items_html += "<li>{} units of Item {} in Warehouse {}</li>".format(
						bold(d[2]), bold(d[0]), bold(d[1])
					)

				msg = _(
					"The stock has been reserved for the following Items and Warehouses, un-reserve the same to {0} the Stock Reconciliation: <br /><br /> {1}"
				).format(self._action, items_html)

			frappe.throw(
				msg,
				title=_("Stock Reservation"),
			)

	def update_stock_ledger(self):
		"""find difference between current and expected entries
		and create stock ledger entries based on the difference"""
		from erpnext.stock.stock_ledger import get_previous_sle

		sl_entries = []
		for row in self.items:
			if not row.qty and not row.valuation_rate and not row.current_qty:
				self.make_adjustment_entry(row, sl_entries)
				continue

			item = frappe.get_cached_value(
				"Item", row.item_code, ["has_serial_no", "has_batch_no"], as_dict=1
			)

			if item.has_serial_no or item.has_batch_no:
				self.get_sle_for_serialized_items(row, sl_entries)
			else:
				if row.serial_and_batch_bundle:
					frappe.throw(
						_(
							"Row #{0}: Item {1} is not a Serialized/Batched Item. It cannot have a Serial No/Batch No against it."
						).format(row.idx, frappe.bold(row.item_code))
					)

				previous_sle = get_previous_sle(
					{
						"item_code": row.item_code,
						"warehouse": row.warehouse,
						"posting_date": self.posting_date,
						"posting_time": self.posting_time,
					}
				)

				if previous_sle:
					if row.qty in ("", None):
						row.qty = previous_sle.get("qty_after_transaction", 0)

					if row.valuation_rate in ("", None):
						row.valuation_rate = previous_sle.get("valuation_rate", 0)

				if row.qty and not row.valuation_rate and not row.allow_zero_valuation_rate:
					frappe.throw(
						_("Valuation Rate required for Item {0} at row {1}").format(row.item_code, row.idx)
					)

				if (
					previous_sle
					and row.qty == previous_sle.get("qty_after_transaction")
					and (row.valuation_rate == previous_sle.get("valuation_rate") or row.qty == 0)
				) or (not previous_sle and not row.qty):
					continue

				sl_entries.append(self.get_sle_for_items(row))

		if sl_entries:
			allow_negative_stock = cint(frappe.db.get_single_value("Stock Settings", "allow_negative_stock"))
			self.make_sl_entries(sl_entries, allow_negative_stock=allow_negative_stock)

	def make_adjustment_entry(self, row, sl_entries):
		from erpnext.stock.stock_ledger import get_stock_value_difference

		difference_amount = get_stock_value_difference(
			row.item_code, row.warehouse, self.posting_date, self.posting_time, self.name
		)

		if not difference_amount:
			return

		args = self.get_sle_for_items(row)
		args.update({"stock_value_difference": -1 * difference_amount, "is_adjustment_entry": 1})

		sl_entries.append(args)

	def get_sle_for_serialized_items(self, row, sl_entries):
		if row.current_serial_and_batch_bundle:
			args = self.get_sle_for_items(row)
			args.update(
				{
					"actual_qty": -1 * row.current_qty,
					"serial_and_batch_bundle": row.current_serial_and_batch_bundle,
					"valuation_rate": row.current_valuation_rate,
				}
			)

			sl_entries.append(args)

		if row.qty != 0:
			args = self.get_sle_for_items(row)
			args.update(
				{
					"actual_qty": row.qty,
					"incoming_rate": row.valuation_rate,
					"serial_and_batch_bundle": row.serial_and_batch_bundle,
				}
			)

			sl_entries.append(args)

	def update_valuation_rate_for_serial_no(self):
		for d in self.items:
			if not d.serial_no:
				continue

			serial_nos = get_serial_nos(d.serial_no)
			self.update_valuation_rate_for_serial_nos(d, serial_nos)

	def update_valuation_rate_for_serial_nos(self, row, serial_nos):
		valuation_rate = row.valuation_rate if self.docstatus == 1 else row.current_valuation_rate
		if valuation_rate is None:
			return

		for d in serial_nos:
			frappe.db.set_value("Serial No", d, "purchase_rate", valuation_rate)

	def get_sle_for_items(self, row, serial_nos=None, current_bundle=True):
		"""Insert Stock Ledger Entries"""

		if not serial_nos and row.serial_no:
			serial_nos = get_serial_nos(row.serial_no)

		data = frappe._dict(
			{
				"doctype": "Stock Ledger Entry",
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"voucher_detail_no": row.name,
				"actual_qty": 0,
				"company": self.company,
				"stock_uom": frappe.db.get_value("Item", row.item_code, "stock_uom"),
				"is_cancelled": 1 if self.docstatus == 2 else 0,
				"valuation_rate": flt(row.valuation_rate, row.precision("valuation_rate")),
			}
		)

		if not row.batch_no:
			data.qty_after_transaction = flt(row.qty, row.precision("qty"))

		dimensions = get_inventory_dimensions()
		has_dimensions = False
		for dimension in dimensions:
			if row.get(dimension.get("fieldname")):
				has_dimensions = True

		if self.docstatus == 2 and (not row.batch_no or not row.serial_and_batch_bundle):
			if row.current_qty and current_bundle:
				data.actual_qty = -1 * row.current_qty
				data.qty_after_transaction = flt(row.current_qty)
				data.previous_qty_after_transaction = flt(row.qty)
				data.valuation_rate = flt(row.current_valuation_rate)
				data.serial_and_batch_bundle = row.current_serial_and_batch_bundle
				data.stock_value = data.qty_after_transaction * data.valuation_rate
				data.stock_value_difference = -1 * flt(row.amount_difference)
			else:
				data.actual_qty = row.qty
				data.qty_after_transaction = 0.0
				data.serial_and_batch_bundle = row.serial_and_batch_bundle
				data.valuation_rate = flt(row.valuation_rate)
				data.stock_value_difference = -1 * flt(row.amount_difference)

		elif self.docstatus == 1 and has_dimensions and (not row.batch_no or not row.serial_and_batch_bundle):
			data.actual_qty = row.qty
			data.qty_after_transaction = 0.0
			data.incoming_rate = flt(row.valuation_rate)

		self.update_inventory_dimensions(row, data)

		return data

	def make_sle_on_cancel(self):
		sl_entries = []

		has_serial_no = False
		for row in self.items:
			sl_entries.append(self.get_sle_for_items(row))
			if row.serial_and_batch_bundle and row.current_serial_and_batch_bundle:
				sl_entries.append(self.get_sle_for_items(row, current_bundle=False))

		if sl_entries:
			if has_serial_no:
				sl_entries = self.merge_similar_item_serial_nos(sl_entries)

			sl_entries.reverse()
			allow_negative_stock = cint(frappe.db.get_single_value("Stock Settings", "allow_negative_stock"))
			self.make_sl_entries(sl_entries, allow_negative_stock=allow_negative_stock)

	def merge_similar_item_serial_nos(self, sl_entries):
		# If user has put the same item in multiple row with different serial no
		new_sl_entries = []
		merge_similar_entries = {}

		for d in sl_entries:
			if not d.serial_no or flt(d.get("actual_qty")) < 0:
				new_sl_entries.append(d)
				continue

			key = (d.item_code, d.warehouse)
			if key not in merge_similar_entries:
				d.total_amount = flt(d.actual_qty) * d.valuation_rate
				merge_similar_entries[key] = d
			elif d.serial_no:
				data = merge_similar_entries[key]
				data.actual_qty += d.actual_qty
				data.qty_after_transaction += d.qty_after_transaction

				data.total_amount += d.actual_qty * d.valuation_rate
				data.valuation_rate = (data.total_amount) / data.actual_qty
				data.serial_no += "\n" + d.serial_no

				data.incoming_rate = (data.total_amount) / data.actual_qty

		new_sl_entries.extend(merge_similar_entries.values())
		return new_sl_entries

	def get_gl_entries(self, warehouse_account=None):
		if not self.cost_center:
			msgprint(_("Please enter Cost Center"), raise_exception=1)

		return super().get_gl_entries(warehouse_account, self.expense_account, self.cost_center)

	def validate_expense_account(self):
		if not cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			return

		if not self.expense_account:
			frappe.throw(_("Please enter Expense Account"))
		elif self.purpose == "Opening Stock" or not frappe.db.sql(
			"""select name from `tabStock Ledger Entry` limit 1"""
		):
			if frappe.db.get_value("Account", self.expense_account, "report_type") == "Profit and Loss":
				frappe.throw(
					_(
						"Difference Account must be a Asset/Liability type account, since this Stock Reconciliation is an Opening Entry"
					),
					OpeningEntryAccountError,
				)

	def set_zero_value_for_customer_provided_items(self):
		changed_any_values = False

		for d in self.get("items"):
			is_customer_item = frappe.db.get_value("Item", d.item_code, "is_customer_provided_item")
			if is_customer_item and d.valuation_rate:
				d.valuation_rate = 0.0
				changed_any_values = True

		if changed_any_values:
			msgprint(
				_("Valuation rate for customer provided items has been set to zero."),
				title=_("Note"),
				indicator="blue",
			)

	def set_total_qty_and_amount(self):
		for d in self.get("items"):
			d.amount = flt(d.qty, d.precision("qty")) * flt(d.valuation_rate, d.precision("valuation_rate"))
			d.current_amount = flt(d.current_qty, d.precision("current_qty")) * flt(
				d.current_valuation_rate, d.precision("current_valuation_rate")
			)

			d.quantity_difference = flt(d.qty) - flt(d.current_qty)
			d.amount_difference = flt(d.amount) - flt(d.current_amount)

	def get_items_for(self, warehouse):
		self.items = []
		for item in get_items(warehouse, self.posting_date, self.posting_time, self.company):
			self.append("items", item)

	def submit(self):
		if len(self.items) > 100:
			msgprint(
				_(
					"The task has been enqueued as a background job. In case there is any issue on processing in background, the system will add a comment about the error on this Stock Reconciliation and revert to the Draft stage"
				)
			)
			self.queue_action("submit", timeout=4600)
		else:
			self._submit()

	def cancel(self):
		if len(self.items) > 100:
			msgprint(
				_(
					"The task has been enqueued as a background job. In case there is any issue on processing in background, the system will add a comment about the error on this Stock Reconciliation and revert to the Submitted stage"
				)
			)
			self.queue_action("cancel", timeout=2000)
		else:
			self._cancel()

	def recalculate_current_qty(self, voucher_detail_no):
		from erpnext.stock.stock_ledger import get_valuation_rate

		for row in self.items:
			if voucher_detail_no != row.name:
				continue

			val_rate = 0.0
			current_qty = 0.0
			if row.current_serial_and_batch_bundle:
				current_qty = self.get_current_qty_for_serial_or_batch(row)
			elif row.serial_no:
				item_dict = get_stock_balance_for(
					row.item_code,
					row.warehouse,
					self.posting_date,
					self.posting_time,
					row=row,
				)

				current_qty = item_dict.get("qty")
				row.current_serial_no = item_dict.get("serial_nos")
				row.current_valuation_rate = item_dict.get("rate")
				val_rate = item_dict.get("rate")
			elif row.batch_no:
				current_qty = get_batch_qty_for_stock_reco(
					row.item_code,
					row.warehouse,
					row.batch_no,
					self.posting_date,
					self.posting_time,
					self.name,
				)

			precesion = row.precision("current_qty")
			if flt(current_qty, precesion) != flt(row.current_qty, precesion):
				if not row.serial_no:
					val_rate = get_incoming_rate(
						frappe._dict(
							{
								"item_code": row.item_code,
								"warehouse": row.warehouse,
								"qty": current_qty * -1,
								"serial_and_batch_bundle": row.current_serial_and_batch_bundle,
								"batch_no": row.batch_no,
								"voucher_type": self.doctype,
								"voucher_no": self.name,
								"company": self.company,
								"posting_date": self.posting_date,
								"posting_time": self.posting_time,
							}
						)
					)

				row.current_valuation_rate = val_rate
				row.current_qty = current_qty
				row.db_set(
					{
						"current_qty": row.current_qty,
						"current_valuation_rate": row.current_valuation_rate,
						"current_amount": flt(row.current_qty * row.current_valuation_rate),
					}
				)

	def has_negative_stock_allowed(self):
		allow_negative_stock = cint(frappe.db.get_single_value("Stock Settings", "allow_negative_stock"))
		if allow_negative_stock:
			return True

		if any(
			((d.serial_and_batch_bundle or d.batch_no) and flt(d.qty) == flt(d.current_qty))
			for d in self.items
		):
			allow_negative_stock = True

		return allow_negative_stock

	def get_current_qty_for_serial_or_batch(self, row):
		doc = frappe.get_doc("Serial and Batch Bundle", row.current_serial_and_batch_bundle)
		current_qty = 0.0
		if doc.has_serial_no:
			current_qty = self.get_current_qty_for_serial_nos(doc)
		elif doc.has_batch_no:
			current_qty = self.get_current_qty_for_batch_nos(doc)

		return abs(current_qty)

	def get_current_qty_for_serial_nos(self, doc):
		serial_nos_details = get_available_serial_nos(
			frappe._dict(
				{
					"item_code": doc.item_code,
					"warehouse": doc.warehouse,
					"posting_date": self.posting_date,
					"posting_time": self.posting_time,
					"voucher_no": self.name,
					"ignore_warehouse": 1,
				}
			)
		)

		if not serial_nos_details:
			return 0.0

		doc.delete_serial_batch_entries()
		current_qty = 0.0
		for serial_no_row in serial_nos_details:
			current_qty += 1
			doc.append(
				"entries",
				{
					"serial_no": serial_no_row.serial_no,
					"qty": -1,
					"warehouse": doc.warehouse,
					"batch_no": serial_no_row.batch_no,
				},
			)

		doc.set_incoming_rate(save=True)
		doc.calculate_qty_and_amount(save=True)
		doc.db_update_all()

		return current_qty

	def get_current_qty_for_batch_nos(self, doc):
		current_qty = 0.0
		precision = doc.entries[0].precision("qty")
		for d in doc.entries:
			qty = (
				get_batch_qty(
					d.batch_no,
					doc.warehouse,
					posting_date=doc.posting_date,
					posting_time=doc.posting_time,
					ignore_voucher_nos=[doc.voucher_no],
				)
				or 0
			) * -1

			if flt(d.qty, precision) != flt(qty, precision):
				d.db_set("qty", qty)

			current_qty += qty

		return current_qty


def get_batch_qty_for_stock_reco(item_code, warehouse, batch_no, posting_date, posting_time, voucher_no):
	ledger = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(ledger)
		.select(
			Sum(ledger.actual_qty).as_("batch_qty"),
		)
		.where(
			(ledger.item_code == item_code)
			& (ledger.warehouse == warehouse)
			& (ledger.docstatus == 1)
			& (ledger.is_cancelled == 0)
			& (ledger.batch_no == batch_no)
			& (ledger.posting_date <= posting_date)
			& (
				CombineDatetime(ledger.posting_date, ledger.posting_time)
				<= CombineDatetime(posting_date, posting_time)
			)
			& (ledger.voucher_no != voucher_no)
		)
		.groupby(ledger.batch_no)
	)

	sle = query.run(as_dict=True)

	return flt(sle[0].batch_qty) if sle else 0


@frappe.whitelist()
def get_items(warehouse, posting_date, posting_time, company, item_code=None, ignore_empty_stock=False):
	ignore_empty_stock = cint(ignore_empty_stock)
	items = []
	if item_code and warehouse:
		items = get_item_and_warehouses(item_code, warehouse)

	if not item_code:
		items = get_items_for_stock_reco(warehouse, company)

	res = []
	itemwise_batch_data = get_itemwise_batch(warehouse, posting_date, company, item_code)

	for d in items:
		if d.item_code in itemwise_batch_data:
			valuation_rate = get_stock_balance(
				d.item_code, d.warehouse, posting_date, posting_time, with_valuation_rate=True
			)[1]

			for row in itemwise_batch_data.get(d.item_code):
				if ignore_empty_stock and not row.qty:
					continue

				args = get_item_data(row, row.qty, valuation_rate)
				res.append(args)
		else:
			stock_bal = get_stock_balance(
				d.item_code,
				d.warehouse,
				posting_date,
				posting_time,
				with_valuation_rate=True,
				with_serial_no=cint(d.has_serial_no),
			)
			qty, valuation_rate, serial_no = (
				stock_bal[0],
				stock_bal[1],
				stock_bal[2] if cint(d.has_serial_no) else "",
			)

			if ignore_empty_stock and not stock_bal[0]:
				continue

			args = get_item_data(d, qty, valuation_rate, serial_no)

			res.append(args)

	return res


def get_item_and_warehouses(item_code, warehouse):
	from frappe.utils.nestedset import get_descendants_of

	items = []
	if frappe.get_cached_value("Warehouse", warehouse, "is_group"):
		childrens = get_descendants_of("Warehouse", warehouse, ignore_permissions=True, order_by="lft")
		for ch_warehouse in childrens:
			items.append(frappe._dict({"item_code": item_code, "warehouse": ch_warehouse}))
	else:
		items = [frappe._dict({"item_code": item_code, "warehouse": warehouse})]

	return items


def get_items_for_stock_reco(warehouse, company):
	lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
	items = frappe.db.sql(
		f"""
		select
			i.name as item_code, i.item_name, bin.warehouse as warehouse, i.has_serial_no, i.has_batch_no
		from
			`tabBin` bin, `tabItem` i
		where
			i.name = bin.item_code
			and IFNULL(i.disabled, 0) = 0
			and i.is_stock_item = 1
			and i.has_variants = 0
			and exists(
				select name from `tabWarehouse` where lft >= {lft} and rgt <= {rgt} and name = bin.warehouse and is_group = 0
			)
	""",
		as_dict=1,
	)

	items += frappe.db.sql(
		"""
		select
			i.name as item_code, i.item_name, id.default_warehouse as warehouse, i.has_serial_no, i.has_batch_no
		from
			`tabItem` i, `tabItem Default` id
		where
			i.name = id.parent
			and exists(
				select name from `tabWarehouse` where lft >= %s and rgt <= %s and name=id.default_warehouse and is_group = 0
			)
			and i.is_stock_item = 1
			and i.has_variants = 0
			and IFNULL(i.disabled, 0) = 0
			and id.company = %s
		group by i.name
	""",
		(lft, rgt, company),
		as_dict=1,
	)

	# remove duplicates
	# check if item-warehouse key extracted from each entry exists in set iw_keys
	# and update iw_keys
	iw_keys = set()
	items = [
		item
		for item in items
		if [
			(item.item_code, item.warehouse) not in iw_keys,
			iw_keys.add((item.item_code, item.warehouse)),
		][0]
	]

	return items


def get_item_data(row, qty, valuation_rate, serial_no=None):
	return {
		"item_code": row.item_code,
		"warehouse": row.warehouse,
		"qty": qty,
		"item_name": row.item_name,
		"valuation_rate": valuation_rate,
		"current_qty": qty,
		"current_valuation_rate": valuation_rate,
		"current_serial_no": serial_no,
		"serial_no": serial_no,
		"batch_no": row.get("batch_no"),
	}


def get_itemwise_batch(warehouse, posting_date, company, item_code=None):
	from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute

	itemwise_batch_data = {}

	filters = frappe._dict(
		{"warehouse": warehouse, "from_date": posting_date, "to_date": posting_date, "company": company}
	)

	if item_code:
		filters.item_code = item_code

	columns, data = execute(filters)

	for row in data:
		itemwise_batch_data.setdefault(row[0], []).append(
			frappe._dict(
				{
					"item_code": row[0],
					"warehouse": row[3],
					"qty": row[8],
					"item_name": row[1],
					"batch_no": row[4],
				}
			)
		)

	return itemwise_batch_data


@frappe.whitelist()
def get_stock_balance_for(
	item_code: str,
	warehouse: str,
	posting_date,
	posting_time,
	batch_no: str | None = None,
	with_valuation_rate: bool = True,
	inventory_dimensions_dict=None,
	row=None,
):
	frappe.has_permission("Stock Reconciliation", "write", throw=True)

	item_dict = frappe.get_cached_value("Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=1)

	if isinstance(row, str):
		row = json.loads(row)

	if isinstance(row, dict):
		row = frappe._dict(row)

	if not item_dict:
		# In cases of data upload to Items table
		msg = _("Item {} does not exist.").format(item_code)
		frappe.throw(msg, title=_("Missing"))

	serial_nos = None
	has_serial_no = bool(item_dict.get("has_serial_no"))
	has_batch_no = bool(item_dict.get("has_batch_no"))

	use_serial_batch_fields = frappe.db.get_single_value("Stock Settings", "use_serial_batch_fields")

	if not batch_no and has_batch_no:
		# Not enough information to fetch data
		return {
			"qty": 0,
			"rate": 0,
			"serial_nos": None,
			"use_serial_batch_fields": row.use_serial_batch_fields if row else use_serial_batch_fields,
		}

	# TODO: fetch only selected batch's values
	data = get_stock_balance(
		item_code,
		warehouse,
		posting_date,
		posting_time,
		with_valuation_rate=with_valuation_rate,
		with_serial_no=has_serial_no,
		inventory_dimensions_dict=inventory_dimensions_dict,
	)

	if has_serial_no:
		qty, rate, serial_nos = data
	else:
		qty, rate = data

	if item_dict.get("has_batch_no"):
		qty = (
			get_batch_qty(
				batch_no,
				warehouse,
				posting_date=posting_date,
				posting_time=posting_time,
				for_stock_levels=True,
			)
			or 0
		)

	return {
		"qty": qty,
		"rate": rate,
		"serial_nos": serial_nos,
		"use_serial_batch_fields": row.use_serial_batch_fields if row else use_serial_batch_fields,
	}


@frappe.whitelist()
def get_difference_account(purpose, company):
	if purpose == "Stock Reconciliation":
		account = get_company_default(company, "stock_adjustment_account")
	else:
		account = frappe.db.get_value(
			"Account", {"is_group": 0, "company": company, "account_type": "Temporary"}, "name"
		)

	return account
