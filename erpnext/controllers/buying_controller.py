# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import ValidationError, _, msgprint
from frappe.contacts.doctype.address.address import render_address
from frappe.query_builder.functions import Abs, Sum
from frappe.utils import cint, flt, get_link_to_form, getdate
from frappe.utils.data import nowtime

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget
from erpnext.accounts.party import _get_party_details
from erpnext.buying.doctype.buying_settings.buying_settings import (
	bills_rejected_quantity,
	is_rejected_material_valued,
)
from erpnext.buying.utils import update_last_purchase_rate, validate_duplicate_items, validate_for_items
from erpnext.controllers.accounts_controller import (
	_get_taxes_and_charges,
	is_deduct_with_valuation,
	validate_deduct_with_valuation_category,
)
from erpnext.controllers.sales_and_purchase_return import get_rate_for_return
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import validate_terms_and_conditions
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import _get_incoming_rate
from erpnext.utilities.transaction_base import get_whole_number_uoms


class QtyMismatchError(ValidationError):
	pass


class BuyingController(SubcontractingController):
	def __setup__(self):
		self.flags.ignore_permlevel_for_fields = ["buying_price_list", "price_list_currency"]

	def validate(self):
		validate_terms_and_conditions(self.get("tc_name"), "buying")
		self.set_rate_for_standalone_debit_note()

		super().validate()
		if getattr(self, "supplier", None) and not self.supplier_name:
			self.supplier_name = frappe.db.get_value("Supplier", self.supplier, "supplier_name")

		self.validate_items()
		self.set_received_qty()
		self.set_qty_as_per_stock_uom()
		self.validate_stock_or_nonstock_items()
		self.validate_deduct_with_valuation_taxes()
		self.validate_warehouse()
		self.validate_from_warehouse()
		self.set_supplier_address()
		self.validate_asset_return()
		self.validate_auto_repeat_subscription_dates()
		self.create_package_for_transfer()

		if self.doctype == "Purchase Invoice":
			self.validate_purchase_receipt_if_update_stock()
			if not self.update_stock:
				validate_duplicate_items(self)

		if self.doctype == "Purchase Receipt" or (self.doctype == "Purchase Invoice" and self.update_stock):
			self.validate_purchase_return()
			self.validate_rejected_warehouse()
			self.validate_accepted_rejected_qty()
			validate_for_items(self)

			# sub-contracting
			self.validate_for_subcontracting()
			if self.get("is_old_subcontracting_flow"):
				self.create_raw_materials_supplied()
			self.set_landed_cost_voucher_amount()

		if self.doctype in ("Purchase Receipt", "Purchase Invoice"):
			self.update_valuation_rate()
			self.sync_accepted_packages()
			self.set_serial_and_batch_bundle()

	def onload(self):
		super().onload()
		self.set_onload(
			"backflush_based_on",
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on"),
		)

		if self.docstatus == 1 and self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			self.set_onload(
				"allow_to_make_qc_after_submission",
				frappe.db.get_single_value(
					"Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery"
				),
			)

	def create_package_for_transfer(self) -> None:
		"""Create serial and batch package for Sourece Warehouse in case of inter transfer."""

		if self.is_internal_transfer() and (
			self.doctype == "Purchase Receipt" or (self.doctype == "Purchase Invoice" and self.update_stock)
		):
			field = "delivery_note_item" if self.doctype == "Purchase Receipt" else "sales_invoice_item"

			doctype = "Delivery Note Item" if self.doctype == "Purchase Receipt" else "Sales Invoice Item"

			ids = [d.get(field) for d in self.get("items") if d.get(field)]
			bundle_ids = {}
			if ids:
				for bundle in frappe.get_all(
					doctype, filters={"name": ("in", ids)}, fields=["serial_and_batch_bundle", "name"]
				):
					bundle_ids[bundle.name] = bundle.serial_and_batch_bundle

			bundle_ids.update(self.get_component_packages())

			if not bundle_ids:
				return

			for item in self.get("items"):
				reference = item.get(field) or item.get("delivery_note_packed_item")
				if reference and not item.serial_and_batch_bundle and bundle_ids.get(reference):
					item.serial_and_batch_bundle = self.make_accepted_package(item, bundle_ids.get(reference))

				elif (
					not self.is_new()
					and item.serial_and_batch_bundle
					and next(
						(
							old_item
							for old_item in self.get_doc_before_save().items
							if old_item.name == item.name and old_item.qty != item.qty
						),
						None,
					)
					and len(
						sabe := frappe.get_all(
							"Serial and Batch Entry",
							filters={"parent": item.serial_and_batch_bundle, "serial_no": ["is", "not set"]},
							pluck="name",
						)
					)
					== 1
				):
					frappe.set_value("Serial and Batch Entry", sabe[0], "qty", item.qty)

				if item.get(field) and bundle_ids.get(item.get(field)):
					self.set_rejected_package(item, bundle_ids.get(item.get(field)))

	def get_component_incoming_rates(self) -> dict:
		packed_items = [
			d.delivery_note_packed_item for d in self.get("items") if d.get("delivery_note_packed_item")
		]
		if not packed_items:
			return {}

		return frappe._dict(
			frappe.get_all(
				"Packed Item",
				filters={"name": ("in", packed_items)},
				fields=["name", "incoming_rate"],
				as_list=True,
			)
		)

	def get_component_packages(self) -> dict:
		packed_items = [
			d.delivery_note_packed_item for d in self.get("items") if d.get("delivery_note_packed_item")
		]
		if not packed_items:
			return {}

		return frappe._dict(
			frappe.get_all(
				"Packed Item",
				filters={"name": ("in", packed_items)},
				fields=["name", "serial_and_batch_bundle"],
				as_list=True,
			)
		)

	def make_accepted_package(self, row, package) -> str:
		"""Package of the material the row accepts.

		A row that rejects nothing keeps the package of the in-transit warehouse it came out of. A
		row that rejects material needs a package of the accepted warehouse instead, since that is
		the entry it belongs to; the material leaving the in-transit warehouse gets a package of its
		own when the receipt is submitted.
		"""
		if not (self.is_internal_receipt() and flt(row.rejected_qty)):
			return self.make_package_for_transfer(
				package,
				row.from_warehouse,
				type_of_transaction="Outward",
				do_not_submit=True,
				qty=flt(row.stock_qty),
			)

		if not flt(row.stock_qty):
			return ""

		return self.make_package_for_transfer(
			package,
			row.warehouse,
			type_of_transaction="Inward",
			do_not_submit=True,
			qty=flt(row.stock_qty),
			exclude_serial_nos=self.get_rejected_serial_nos(row),
		)

	def get_delivered_package(self, row) -> str | None:
		"""Package of the material the delivery note put in the in-transit warehouse."""
		field = "delivery_note_item" if self.doctype == "Purchase Receipt" else "sales_invoice_item"
		doctype = "Delivery Note Item" if self.doctype == "Purchase Receipt" else "Sales Invoice Item"
		if row.get("delivery_note_packed_item"):
			return frappe.db.get_value(
				"Packed Item", row.delivery_note_packed_item, "serial_and_batch_bundle"
			)

		if not row.get(field):
			return None

		return frappe.db.get_value(doctype, row.get(field), "serial_and_batch_bundle")

	def set_rejected_package(self, row, package) -> None:
		"""Package of the material the row rejects.

		A receipt of an internal transfer builds no package for it on its own, so rejected material
		of a tracked item would have nothing to say where it came from.
		"""
		if not (self.is_internal_receipt() and flt(row.rejected_qty)) or self.is_return:
			return

		if row.get("rejected_serial_and_batch_bundle") or not row.rejected_warehouse:
			return

		rejected_qty = flt(flt(row.rejected_qty) * flt(row.conversion_factor), row.precision("stock_qty"))

		row.rejected_serial_and_batch_bundle = self.make_package_for_transfer(
			package,
			row.rejected_warehouse,
			type_of_transaction="Inward",
			do_not_submit=True,
			qty=rejected_qty,
			exclude_serial_nos=self.get_accepted_serial_nos(row),
		)

		frappe.db.set_value("Serial and Batch Bundle", row.rejected_serial_and_batch_bundle, "is_rejected", 1)

	def get_accepted_serial_nos(self, row) -> list:
		if not row.get("serial_and_batch_bundle"):
			return []

		return frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": row.serial_and_batch_bundle, "serial_no": ("is", "set")},
			pluck="serial_no",
		)

	def sync_accepted_packages(self) -> None:
		"""Keep the package of a row in the shape its own entry needs.

		A row that rejects material carries the package of its accepted warehouse; a row that
		rejects nothing carries the package of the in-transit warehouse it came out of. Editing the
		split moves the package from one to the other.
		"""
		if not self.is_internal_receipt() or self.is_return:
			return

		for row in self.get("items"):
			package = row.get("serial_and_batch_bundle")
			if not package:
				continue

			details = frappe.db.get_value(
				"Serial and Batch Bundle",
				package,
				["warehouse", "type_of_transaction", "docstatus"],
				as_dict=True,
			)
			if not details or details.docstatus != 0:
				continue

			if flt(row.rejected_qty):
				wanted = (row.warehouse, "Inward")
			else:
				wanted = (row.from_warehouse, "Outward")

			if (details.warehouse, details.type_of_transaction) == wanted:
				continue

			row.serial_and_batch_bundle = self.make_accepted_package(
				row, self.get_delivered_package(row) or package
			)
			frappe.delete_doc("Serial and Batch Bundle", package, force=True, ignore_permissions=True)

	def get_rejected_serial_nos(self, row) -> list:
		if not flt(row.get("rejected_qty")):
			return []

		if row.get("rejected_serial_and_batch_bundle"):
			return frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": row.rejected_serial_and_batch_bundle, "serial_no": ("is", "set")},
				pluck="serial_no",
			)

		return get_serial_nos(row.get("rejected_serial_no"))

	def set_rate_for_standalone_debit_note(self):
		if self.get("is_return") and self.get("update_stock") and not self.return_against:
			for row in self.items:
				if row.rate <= 0:
					# override the rate with valuation rate, converted to the row's UOM
					conversion_factor = flt(row.conversion_factor) or get_conversion_factor(
						row.item_code, row.uom
					).get("conversion_factor")
					valuation_rate = _get_incoming_rate(
						{
							"item_code": row.item_code,
							"warehouse": row.warehouse,
							"posting_date": self.get("posting_date"),
							"posting_time": self.get("posting_time"),
							"qty": flt(flt(row.qty) * conversion_factor, row.precision("stock_qty")),
							"serial_and_batch_bundle": row.get("serial_and_batch_bundle"),
							"company": self.company,
							"voucher_type": self.doctype,
							"voucher_no": self.name,
							"voucher_detail_no": row.name,
						},
						raise_error_if_no_rate=False,
					)
					row.rate = flt(valuation_rate * conversion_factor, row.precision("rate"))

					row.discount_percentage = 0.0
					row.discount_amount = 0.0
					row.margin_rate_or_amount = 0.0

	def set_missing_values(self, for_validate=False):
		super().set_missing_values(for_validate)

		self.set_supplier_from_item_default()
		self.set_price_list_currency("Buying")

		# set contact and address details for supplier, if they are not mentioned
		if getattr(self, "supplier", None):
			self.update_if_missing(
				_get_party_details(
					self.supplier,
					party_type="Supplier",
					doctype=self.doctype,
					company=self.company,
					party_address=self.get("supplier_address"),
					shipping_address=self.get("shipping_address"),
					dispatch_address=self.get("dispatch_address"),
					company_address=self.get("billing_address"),
					fetch_payment_terms_template=not self.get("ignore_default_payment_terms_template"),
					ignore_permissions=self.flags.ignore_permissions,
				)
			)

		self.set_missing_item_details(for_validate)

		if self.doctype == "Purchase Receipt" or (self.doctype == "Purchase Invoice" and self.update_stock):
			from erpnext.stock.services.return_charges import ReturnChargesService

			ReturnChargesService(self).set_returned_valuation_charges()

		if self.meta.get_field("taxes"):
			if self.get("taxes_and_charges") and not self.get("taxes") and not for_validate:
				taxes = _get_taxes_and_charges("Purchase Taxes and Charges Template", self.taxes_and_charges)
				for tax in taxes:
					self.append("taxes", tax)

	def set_transaction_date_exchange_rate(self):
		"""Replace the exchange rate mapped from a Purchase Order with the posting date rate."""
		if not (
			self.currency
			and frappe.db.get_single_value("Buying Settings", "use_transaction_date_exchange_rate")
			and not any(item.get("purchase_receipt") or item.get("purchase_invoice") for item in self.items)
		):
			return

		self.use_transaction_date_exchange_rate = 1
		self.conversion_rate = get_exchange_rate(
			self.currency, self.company_currency, self.posting_date, "for_buying"
		)

	def set_supplier_from_item_default(self):
		if self.meta.get_field("supplier") and not self.supplier:
			for d in self.get("items"):
				supplier = frappe.db.get_value(
					"Item Default", {"parent": d.item_code, "company": self.company}, "default_supplier"
				)
				if not supplier:
					item_group = frappe.db.get_value("Item", d.item_code, "item_group")
					supplier = frappe.db.get_value(
						"Item Default", {"parent": item_group, "company": self.company}, "default_supplier"
					)
				if supplier:
					self.supplier = supplier
					break

	def validate_stock_or_nonstock_items(self):
		if self.meta.get_field("taxes") and not self.get_stock_items() and not self.get_asset_items():
			msg = _('Tax Category has been changed to "Total" because all the Items are non-stock items')
			self.update_tax_category(msg)

	def validate_deduct_with_valuation_taxes(self):
		taxes = [tax for tax in self.get("taxes") or [] if is_deduct_with_valuation(tax)]
		if taxes:
			validate_deduct_with_valuation_category(taxes, self.get_deduct_with_valuation_heads_from_source())

	def get_deduct_with_valuation_source_names(self) -> set:
		source_fields = ("purchase_order", "purchase_receipt", "purchase_invoice", "supplier_quotation")
		source_names = {item.get(field) for item in self.get("items") for field in source_fields}
		source_names.update((self.get("amended_from"), self.get("return_against")))
		if self.get("auto_repeat"):
			source_names.add(frappe.db.get_value("Auto Repeat", self.auto_repeat, "reference_document"))
		return source_names - {None, ""}

	def get_deduct_with_valuation_heads_from_source(self) -> set:
		source_names = self.get_deduct_with_valuation_source_names()
		if not source_names:
			return set()

		taxes = frappe.qb.DocType("Purchase Taxes and Charges")
		account_heads = (
			frappe.qb.from_(taxes)
			.select(taxes.account_head)
			.distinct()
			.where(
				taxes.parent.isin(source_names)
				& (taxes.docstatus != 0)
				& (taxes.category == "Valuation")
				& (taxes.add_deduct_tax == "Deduct")
			)
			.run(pluck=True)
		)
		return set(account_heads)

	def update_tax_category(self, msg):
		tax_for_valuation = [
			d for d in self.get("taxes") if d.category in ["Valuation", "Valuation and Total"]
		]

		if tax_for_valuation:
			for d in tax_for_valuation:
				d.category = "Total"

			msgprint(msg)

	def validate_asset_return(self):
		if self.doctype not in ["Purchase Receipt", "Purchase Invoice"] or not self.is_return:
			return

		purchase_doc_field = "purchase_receipt" if self.doctype == "Purchase Receipt" else "purchase_invoice"
		detail_field = purchase_doc_field + "_item"
		asset_filters = {purchase_doc_field: self.return_against, "docstatus": 1}
		if (self.doctype == "Purchase Receipt" or self.get("update_stock")) and all(
			row.get(detail_field) for row in self.items if row.is_fixed_asset
		):
			# Linked assets are checked against the quantity retained in each purchase row below.
			asset_filters[detail_field] = ("is", "not set")

		if self.return_against and frappe.db.exists("Asset", asset_filters):
			frappe.throw(
				_(
					"{0} has submitted assets linked to it. You need to cancel the assets to create purchase return."
				).format(self.return_against),
				title=_("Not Allowed"),
			)

		self.validate_assets_left_after_return()

	def validate_assets_left_after_return(self):
		if self.doctype == "Purchase Invoice" and not self.get("update_stock"):
			return

		detail_field = (
			"purchase_receipt_item" if self.doctype == "Purchase Receipt" else "purchase_invoice_item"
		)
		returned_qty, rows = self.get_returned_asset_qty(detail_field)
		if not returned_qty:
			return

		kept_qty = self.get_qty_kept_after_return(detail_field, returned_qty)
		for detail, asset_qty in get_linked_asset_qty(detail_field, list(returned_qty)).items():
			if flt(asset_qty) > kept_qty[detail]:
				frappe.throw(
					_(
						"Row #{0}: {1} assets of {2} are linked to {3}, which keeps only {4} after this return. Cancel the extra submitted assets or delete the extra draft assets first."
					).format(
						rows[detail].idx,
						flt(asset_qty),
						frappe.bold(rows[detail].item_code),
						get_link_to_form(self.doctype, self.return_against),
						kept_qty[detail],
					),
					title=_("Not Allowed"),
				)

	def get_returned_asset_qty(self, detail_field):
		returned_qty, rows = {}, {}
		for d in self.items:
			if d.is_fixed_asset and d.get(detail_field):
				returned_qty[d.get(detail_field)] = returned_qty.get(d.get(detail_field), 0) + abs(flt(d.qty))
				rows.setdefault(d.get(detail_field), d)

		return returned_qty, rows

	def get_qty_kept_after_return(self, detail_field, returned_qty):
		item_doctype = f"{self.doctype} Item"
		kept_qty = dict(
			frappe.get_all(
				item_doctype, filters={"name": ("in", list(returned_qty))}, fields=["name", "qty"], as_list=1
			)
		)

		parent, child = frappe.qb.DocType(self.doctype), frappe.qb.DocType(item_doctype)
		earlier_returns = (
			frappe.qb.from_(child)
			.join(parent)
			.on(parent.name == child.parent)
			.select(child[detail_field], Sum(Abs(child.qty)))
			.where(
				(child[detail_field].isin(list(returned_qty)))
				& (parent.docstatus == 1)
				& (parent.is_return == 1)
				& (parent.name != self.name)
			)
			.groupby(child[detail_field])
		).run()

		for detail, qty in earlier_returns:
			kept_qty[detail] = flt(kept_qty.get(detail)) - flt(qty)

		return {detail: flt(kept_qty.get(detail)) - qty for detail, qty in returned_qty.items()}

	def get_asset_items(self):
		if self.doctype not in ["Purchase Order", "Purchase Invoice", "Purchase Receipt"]:
			return []

		return [d.item_code for d in self.items if d.is_fixed_asset]

	def set_landed_cost_voucher_amount(self):
		for d in self.get("items"):
			lc_voucher_data = frappe.db.sql(
				"""select sum(applicable_charges), cost_center
				from `tabLanded Cost Item`
				where docstatus = 1 and purchase_receipt_item = %s and receipt_document = %s""",
				(d.name, self.name),
			)
			d.landed_cost_voucher_amount = lc_voucher_data[0][0] if lc_voucher_data else 0.0
			if not d.cost_center and lc_voucher_data and lc_voucher_data[0][1]:
				d.db_set("cost_center", lc_voucher_data[0][1])

	def validate_from_warehouse(self):
		for item in self.get("items"):
			if item.get("from_warehouse") and (item.get("from_warehouse") == item.get("warehouse")):
				frappe.throw(
					_("Row #{0}: Accepted Warehouse and Supplier Warehouse cannot be same").format(item.idx)
				)

			if item.get("from_warehouse") and self.get("is_subcontracted"):
				frappe.throw(
					_(
						"Row #{0}: Cannot select Supplier Warehouse while suppling raw materials to subcontractor"
					).format(item.idx)
				)

	def set_supplier_address(self):
		address_dict = {
			"supplier_address": "address_display",
			"shipping_address": "shipping_address_display",
			"dispatch_address": "dispatch_address_display",
			"billing_address": "billing_address_display",
		}

		for address_field, address_display_field in address_dict.items():
			if self.get(address_field):
				self.set(
					address_display_field, render_address(self.get(address_field), check_permissions=False)
				)

	def set_total_in_words(self):
		from frappe.utils import money_in_words

		if self.meta.get_field("base_in_words"):
			if self.meta.get_field("base_rounded_total") and not self.is_rounded_total_disabled():
				amount = abs(self.base_rounded_total)
			else:
				amount = abs(self.base_grand_total)
			self.base_in_words = money_in_words(amount, self.company_currency)

		if self.meta.get_field("in_words"):
			if self.meta.get_field("rounded_total") and not self.is_rounded_total_disabled():
				amount = abs(self.rounded_total)
			else:
				amount = abs(self.grand_total)

			self.in_words = money_in_words(amount, self.currency)

	# update valuation rate
	def update_valuation_rate(self, reset_outgoing_rate=True):
		"""
		item_tax_amount is the total tax amount applied on that item
		stored for valuation

		TODO: rename item_tax_amount to valuation_tax_amount
		"""
		stock_and_asset_items = []
		stock_and_asset_items = self.get_stock_items() + self.get_asset_items()

		stock_and_asset_items_qty, stock_and_asset_items_amount = 0, 0
		last_item_idx = 1

		total_rejected_qty = 0
		for d in self.get("items"):
			if d.item_code and d.item_code in stock_and_asset_items:
				stock_and_asset_items_qty += flt(d.qty)
				total_rejected_qty += flt(d.get("rejected_qty", 0))
				stock_and_asset_items_amount += flt(d.base_net_amount)
				last_item_idx = d.idx

		total_valuation_amount = sum(
			flt(d.base_tax_amount_after_discount_amount) * (-1 if d.get("add_deduct_tax") == "Deduct" else 1)
			for d in self.get("taxes")
			if d.category in ["Valuation", "Valuation and Total"]
		)

		if not stock_and_asset_items_qty and not frappe.db.get_single_value(
			"Buying Settings", "set_valuation_rate_for_rejected_materials"
		):
			# Rejected material that is not valued cannot carry valuation charges.
			total_valuation_amount = 0

		valuation_amount_adjustment = total_valuation_amount
		for i, item in enumerate(self.get("items")):
			if (
				item.item_code
				and (item.qty or item.get("rejected_qty"))
				and item.item_code in stock_and_asset_items
			):
				if stock_and_asset_items_qty:
					item_proportion = (
						flt(item.base_net_amount) / stock_and_asset_items_amount
						if stock_and_asset_items_amount
						else flt(item.qty) / stock_and_asset_items_qty
					)
				elif total_rejected_qty:
					item_proportion = flt(item.get("rejected_qty")) / flt(total_rejected_qty)

				if i == (last_item_idx - 1):
					item.item_tax_amount = flt(
						valuation_amount_adjustment, self.precision("item_tax_amount", item)
					)
				else:
					item.item_tax_amount = flt(
						item_proportion * total_valuation_amount, self.precision("item_tax_amount", item)
					)
					valuation_amount_adjustment -= item.item_tax_amount

				self.round_floats_in(item, do_not_round_fields=["conversion_factor"])
				if flt(item.conversion_factor) == 0.0:
					item.conversion_factor = (
						get_conversion_factor(item.item_code, item.uom).get("conversion_factor") or 1.0
					)

				net_rate = item.base_net_amount
				if item.sales_incoming_rate:  # for internal transfer
					net_rate = get_transit_amount(item, self.get_internal_transfer_qty(item))

				if (
					not net_rate
					and item.get("rejected_qty")
					and frappe.get_single_value(
						"Buying Settings", "set_valuation_rate_for_rejected_materials"
					)
				):
					net_rate = item.rejected_qty * item.base_net_rate

				qty_in_stock_uom = (
					self.get_valued_stock_qty(item)
					or get_stock_qty(item, item.rejected_qty)
					or flt(item.qty) * flt(item.conversion_factor)
				)

				if self.get("is_old_subcontracting_flow"):
					item.rm_supp_cost = self.get_supplied_items_cost(item.name, reset_outgoing_rate)
					item.valuation_rate = (
						net_rate
						+ item.item_tax_amount
						+ item.rm_supp_cost
						+ flt(item.landed_cost_voucher_amount)
					) / qty_in_stock_uom
				else:
					item.valuation_rate = (
						net_rate
						+ item.item_tax_amount
						+ flt(item.landed_cost_voucher_amount)
						+ flt(item.get("amount_difference_with_purchase_invoice"))
					) / qty_in_stock_uom
			else:
				item.valuation_rate = 0.0

		update_regional_item_valuation_rate(self)

	def get_rejected_valuation_rate(self, row) -> float:
		if not is_rejected_material_valued(self.doctype, row.name):
			return 0.0

		if self.is_internal_transfer() or bills_rejected_quantity(self) or not flt(row.qty):
			return flt(row.valuation_rate)

		return flt(row.base_net_rate) / (flt(row.conversion_factor) or 1.0)

	def get_valued_stock_qty(self, row):
		"""Stock qty the net amount of the row was billed for, which is what its valuation spreads
		over. Each part is rounded as the stock ledger posts it."""
		if not flt(row.get("rejected_qty")) or not bills_rejected_quantity(self):
			return get_stock_qty(row, row.qty)

		return get_stock_qty(row, row.qty) + get_stock_qty(row, row.rejected_qty)

	def set_incoming_rate(self):
		"""
		Override item rate with incoming rate for internal stock transfer
		"""
		if self.doctype not in ("Purchase Receipt", "Purchase Invoice"):
			return

		if not (self.doctype == "Purchase Receipt" or self.get("update_stock")):
			return

		if cint(self.get("is_return")):
			# Material of a transfer goes back at the rate it came in with. Anything else is
			# valued from the original item cost by its valuation method.
			if self.is_internal_transfer():
				self.set_sales_incoming_rate_for_internal_transfer()

			return

		if not self.is_internal_transfer():
			return

		self.set_sales_incoming_rate_for_internal_transfer()

		allow_at_arms_length_price = frappe.get_cached_value(
			"Stock Settings", None, "allow_internal_transfer_at_arms_length_price"
		)
		if allow_at_arms_length_price:
			return

		for d in self.get("items"):
			d.discount_percentage = 0.0
			d.discount_amount = 0.0
			d.margin_rate_or_amount = 0.0

			if d.rate == d.sales_incoming_rate:
				continue

			d.rate = d.sales_incoming_rate
			frappe.msgprint(
				_(
					"Row {0}: Item rate has been updated as per valuation rate since its an internal stock transfer"
				).format(d.idx),
				alert=1,
			)

	def set_sales_incoming_rate_for_internal_transfer(self):
		"""
		Set incoming rate from the sales transaction against which the
		purchase is made (internal transfer)
		"""
		ref_doctype_map = {
			"Purchase Receipt": "Delivery Note Item",
			"Purchase Invoice": "Sales Invoice Item",
		}

		ref_doctype = ref_doctype_map.get(self.doctype)
		returned_field = frappe.scrub(self.doctype) + "_item"
		component_rates = self.get_component_incoming_rates()
		for d in self.get("items"):
			if self.get("is_return") and d.get(returned_field):
				d.sales_incoming_rate = flt(
					frappe.db.get_value(self.doctype + " Item", d.get(returned_field), "sales_incoming_rate")
				)
			elif d.get("delivery_note_packed_item") in component_rates:
				d.sales_incoming_rate = flt(
					component_rates[d.delivery_note_packed_item] * (d.conversion_factor or 1)
				)
			elif not d.get(frappe.scrub(ref_doctype)):
				posting_time = self.get("posting_time")
				if not posting_time:
					posting_time = nowtime()

				outgoing_rate = _get_incoming_rate(
					{
						"item_code": d.item_code,
						"warehouse": d.get("from_warehouse"),
						"posting_date": self.get("posting_date") or self.get("transaction_date"),
						"posting_time": posting_time,
						"qty": -1 * flt(d.get("stock_qty")),
						"serial_and_batch_bundle": d.get("serial_and_batch_bundle"),
						"company": self.company,
						"voucher_type": self.doctype,
						"voucher_no": self.name,
						"allow_zero_valuation": d.get("allow_zero_valuation"),
						"voucher_detail_no": d.name,
					},
					raise_error_if_no_rate=False,
				)

				d.sales_incoming_rate = flt(outgoing_rate * (d.conversion_factor or 1))
			else:
				field = "incoming_rate" if self.get("is_internal_supplier") else "rate"
				d.sales_incoming_rate = flt(
					frappe.db.get_value(ref_doctype, d.get(frappe.scrub(ref_doctype)), field)
					* (d.conversion_factor or 1)
				)

	def validate_for_subcontracting(self):
		if self.is_subcontracted and self.get("is_old_subcontracting_flow"):
			if self.doctype in ["Purchase Receipt", "Purchase Invoice"] and not self.supplier_warehouse:
				frappe.throw(_("Supplier Warehouse mandatory for sub-contracted {0}").format(self.doctype))

			for item in self.get("items"):
				if item in self.sub_contracted_items and not item.bom:
					frappe.throw(_("Please select BOM in BOM field for Item {0}").format(item.item_code))
			if self.doctype != "Purchase Order":
				return
			for row in self.get("supplied_items"):
				if not row.reserve_warehouse:
					msg = f"Reserved Warehouse is mandatory for the Item {frappe.bold(row.rm_item_code)} in Raw Materials supplied"
					frappe.throw(_(msg))
		else:
			for item in self.get("items"):
				if item.get("bom"):
					item.bom = None

	def set_qty_as_per_stock_uom(self):
		allow_to_edit_stock_qty = frappe.db.get_single_value(
			"Stock Settings", "allow_to_edit_stock_uom_qty_for_purchase"
		)
		whole_number_uoms = get_whole_number_uoms(d.get("stock_uom") for d in self.get("items"))

		for d in self.get("items"):
			if d.meta.get_field("stock_qty"):
				# Check if item code is present
				# Conversion factor should not be mandatory for non itemized items
				if not d.conversion_factor and d.item_code:
					frappe.throw(_("Row {0}: Conversion Factor is mandatory").format(d.idx))
				d.stock_qty = flt(d.qty) * flt(d.conversion_factor)

				if self.doctype == "Purchase Receipt" and d.meta.get_field("received_stock_qty"):
					# Set Received Qty in Stock UOM
					d.received_stock_qty = flt(d.received_qty) * flt(
						d.conversion_factor, d.precision("conversion_factor")
					)

				if allow_to_edit_stock_qty or d.get("stock_uom") in whole_number_uoms:
					d.stock_qty = flt(d.stock_qty, d.precision("stock_qty"))
					if d.get("received_stock_qty") and d.meta.get_field("received_stock_qty"):
						d.received_stock_qty = flt(d.received_stock_qty, d.precision("received_stock_qty"))

	def validate_purchase_return(self):
		for d in self.get("items"):
			if self.is_return and not flt(d.rejected_qty) and d.rejected_warehouse:
				d.rejected_warehouse = None

	def set_received_qty(self):
		if not (
			self.doctype == "Purchase Receipt"
			or (self.doctype == "Purchase Invoice" and self.get("update_stock"))
		):
			return

		for d in self.get("items"):
			if not flt(d.received_qty) and (flt(d.qty) or flt(d.rejected_qty)):
				d.received_qty = flt(flt(d.qty) + flt(d.rejected_qty), d.precision("received_qty"))

	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in self.get("items"):
			self.validate_negative_quantity(d, ["received_qty", "qty", "rejected_qty"])

			# Check Received Qty = Accepted Qty + Rejected Qty
			val = flt(d.qty) + flt(d.rejected_qty)
			if flt(val, d.precision("received_qty")) != flt(d.received_qty, d.precision("received_qty")):
				message = _(
					"Row #{0}: Received Qty must be equal to Accepted + Rejected Qty for Item {1}"
				).format(d.idx, d.item_code)
				frappe.throw(msg=message, title=_("Mismatch"), exc=QtyMismatchError)

	def validate_negative_quantity(self, item_row, field_list):
		if self.is_return:
			return

		item_row = item_row.as_dict()
		for fieldname in field_list:
			if flt(item_row[fieldname]) < 0:
				frappe.throw(
					_("Row #{0}: {1} can not be negative for item {2}").format(
						item_row["idx"],
						frappe.get_meta(item_row.doctype).get_label(fieldname),
						item_row["item_code"],
					)
				)

	def check_for_on_hold_or_closed_status(self, ref_doctype, ref_fieldname):
		if reference := self.get_on_hold_or_closed_reference(ref_doctype, ref_fieldname):
			frappe.throw(_("{0} {1} is {2}").format(ref_doctype, *reference))

	def get_internal_transfer_qty(self, row) -> float:
		if flt(row.qty) or not self.is_internal_receipt():
			return flt(row.qty)

		return flt(row.rejected_qty)

	def is_internal_receipt(self) -> bool:
		return self.is_internal_transfer() and self.is_stock_receipt()

	def get_accepted_stock_qty(self, row) -> float:
		"""Accepted qty in the stock UOM. A return takes back no more than its receipt row put in the
		warehouse, less the row's other returns, so returns of parts add up to it. A row with a package
		is not capped, as its package holds the qty."""
		stock_qty = get_stock_qty(row, row.qty)
		if not self.is_return or row.get("serial_and_batch_bundle"):
			return stock_qty

		if self.docstatus == 2:
			return flt(self.get_posted_return_qty(row, row.warehouse)) or stock_qty

		qty_left = self.get_stock_qty_left_to_return(row, row.warehouse)
		return max(stock_qty, -qty_left) if flt(qty_left) > 0 else stock_qty

	def get_stock_qty_left_to_return(self, row, warehouse) -> float:
		"""Stock qty the returned receipt row put in the warehouse that its other returns have not taken back."""
		reference_field = (
			"purchase_receipt_item" if self.doctype == "Purchase Receipt" else "purchase_invoice_item"
		)
		receipt_row = row.get(reference_field)
		if not receipt_row:
			return 0.0

		receipt_item = frappe.qb.DocType(row.doctype)
		receipt_and_other_returns = (
			frappe.qb.from_(receipt_item)
			.select(receipt_item.name)
			.where(
				(receipt_item.name == receipt_row)
				| ((receipt_item[reference_field] == receipt_row) & (receipt_item.parent != self.name))
			)
		)
		sle = frappe.qb.DocType("Stock Ledger Entry")
		qty_left = (
			frappe.qb.from_(sle)
			.select(Sum(sle.actual_qty))
			.where(
				(sle.warehouse == warehouse)
				& (sle.is_cancelled == 0)
				& sle.voucher_detail_no.isin(receipt_and_other_returns)
			)
			.run()[0][0]
		)
		return flt(qty_left, row.precision("stock_qty"))

	def get_posted_return_qty(self, row, warehouse):
		"""Qty the return row's entry took out of the warehouse."""
		return frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_detail_no": row.name,
				"warehouse": warehouse,
				"is_cancelled": 0,
				"actual_qty": ("<", 0),
			},
			"actual_qty",
		)

	def get_source_warehouse_qty(self, row, accepted_qty):
		"""Stock qty the row takes out of the source warehouse. An internal receipt takes no more than its
		delivered row left in transit, so partial receipts that round up add up to the delivery, and its
		return puts back no more than the receipt took. A cap of nothing left falls back to the row's qty."""
		qty = self.get_received_stock_qty(row, accepted_qty)
		if not self.is_capped_in_transit(row):
			return qty

		if self.docstatus == 2:
			return -flt(self.get_posted_qty(row.name, row.from_warehouse, outward=not self.is_return)) or qty

		# a Landed Cost Voucher or repost cancels the row's entries and posts them again: keep what it moved
		if reposted_qty := self.get_posted_qty(
			row.name, row.from_warehouse, outward=not self.is_return, cancelled=True
		):
			return -flt(reposted_qty)

		if self.is_return:
			qty_left = self.get_qty_left_to_return(row)
			return max(qty, -qty_left) if flt(qty_left) > 0 else qty

		qty_left = self.get_qty_left_in_transit(row)
		return min(qty, qty_left) if flt(qty_left) > 0 else qty

	def is_capped_in_transit(self, row) -> bool:
		"""Whether the row moves the stock of a delivered row through transit. A row with a package is not
		capped, as its package holds the qty."""
		if not self.is_internal_receipt():
			return False

		if row.get("serial_and_batch_bundle") or row.get("rejected_serial_and_batch_bundle"):
			return False

		return bool(row.get("purchase_receipt_item") if self.is_return else row.get("delivery_note_item"))

	def get_qty_left_to_return(self, row) -> float:
		"""Stock qty the returned receipt row took out of transit that its other returns have not put back.
		Only the receipt's entry out of transit and the returns' entries into it count, as rejected stock
		can stay in transit."""
		receipt_item = frappe.qb.DocType("Purchase Receipt Item")
		other_returns = (
			frappe.qb.from_(receipt_item)
			.select(receipt_item.name)
			.where(
				(receipt_item.purchase_receipt_item == row.purchase_receipt_item)
				& (receipt_item.parent != self.name)
			)
		)
		sle = frappe.qb.DocType("Stock Ledger Entry")
		moved_qty = (
			frappe.qb.from_(sle)
			.select(Sum(sle.actual_qty))
			.where(
				(sle.warehouse == row.from_warehouse)
				& (sle.is_cancelled == 0)
				& (
					((sle.voucher_detail_no == row.purchase_receipt_item) & (sle.actual_qty < 0))
					| (sle.voucher_detail_no.isin(other_returns) & (sle.actual_qty > 0))
				)
			)
			.run()[0][0]
		)
		return -flt(moved_qty, row.precision("stock_qty"))

	def get_qty_left_in_transit(self, row) -> float | None:
		"""Stock qty the delivered row put in transit that its other receipts, net of their returns, have not
		taken out. None if the receipts take more than was delivered: only rounding is capped."""
		delivered_qty = self.get_posted_qty(row.delivery_note_item, row.from_warehouse, outward=False)
		if not delivered_qty:
			return None

		received_qty, taken_qty = self.get_other_receipts_of_delivered_row(row)
		received_qty += (flt(row.qty) + flt(row.rejected_qty)) * flt(row.conversion_factor)
		precision = row.precision("stock_qty")
		if flt(received_qty, precision) > delivered_qty:
			return None

		return flt(delivered_qty + taken_qty, precision)

	def get_other_receipts_of_delivered_row(self, row) -> tuple[float, float]:
		"""Unrounded stock qty the other receipts of the delivered row and their returns received, and the
		stock qty their entries took out of transit."""
		receipt_item = frappe.qb.DocType("Purchase Receipt Item")
		other_receipt_rows = (
			frappe.qb.from_(receipt_item)
			.select(receipt_item.name)
			.where(
				(receipt_item.delivery_note_item == row.delivery_note_item)
				& (receipt_item.parent != self.name)
			)
		)
		rows = (
			frappe.qb.from_(receipt_item)
			.select(
				receipt_item.name,
				((receipt_item.qty + receipt_item.rejected_qty) * receipt_item.conversion_factor).as_("qty"),
			)
			.where(
				(receipt_item.docstatus == 1)
				& (
					receipt_item.name.isin(other_receipt_rows)
					| receipt_item.purchase_receipt_item.isin(other_receipt_rows)
				)
			)
			.run(as_dict=True)
		)
		if not rows:
			return 0.0, 0.0

		sle = frappe.qb.DocType("Stock Ledger Entry")
		taken_qty = (
			frappe.qb.from_(sle)
			.select(Sum(sle.actual_qty))
			.where(
				(sle.warehouse == row.from_warehouse)
				& (sle.is_cancelled == 0)
				& sle.voucher_detail_no.isin([d.name for d in rows])
			)
			.run()[0][0]
		)
		return sum(flt(d.qty) for d in rows), flt(taken_qty)

	def get_posted_qty(self, voucher_detail_no, warehouse, outward, cancelled=False):
		"""Qty of the row's entry out of or into the warehouse; a row can have both when rejected stock
		stays in transit. Of cancelled entries, the first is the original: later ones include reversals."""
		return frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_detail_no": voucher_detail_no,
				"warehouse": warehouse,
				"is_cancelled": cint(cancelled),
				"actual_qty": ("<", 0) if outward else (">", 0),
			},
			"actual_qty",
			order_by="creation asc",
		)

	def get_received_stock_qty(self, row, accepted_qty):
		"""Accepted stock qty, plus the rejected stock qty when rejected stock leaves the source warehouse too."""
		if not (self.is_internal_receipt() and flt(row.rejected_qty)):
			return accepted_qty

		if row.get("serial_and_batch_bundle") and not row.get("rejected_serial_and_batch_bundle"):
			return accepted_qty

		return get_stock_qty(row, flt(row.qty) + flt(row.rejected_qty))

	def get_accepted_warehouse_package(self, row, type_of_transaction, via_landed_cost_voucher):
		"""Package for the entry into the accepted warehouse, which is the package of the row itself
		when the row rejects material."""
		if flt(row.rejected_qty) and self.is_internal_receipt() and not self.is_return:
			return row.serial_and_batch_bundle

		if self.is_internal_transfer() and not self.is_return and self.docstatus != 2:
			return self.get_package_for_target_warehouse(
				row,
				type_of_transaction=type_of_transaction,
				via_landed_cost_voucher=via_landed_cost_voucher,
			)

		return row.serial_and_batch_bundle

	def get_submitted_package(self, row, warehouse):
		return frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_detail_no": row.name, "warehouse": warehouse, "is_cancelled": 0},
			"serial_and_batch_bundle",
		)

	def get_source_warehouse_reversal_package(self, row, package):
		if not (self.is_internal_transfer() and self.is_return):
			return package

		if existing_package := self.get_package_of_source_warehouse(row):
			return existing_package

		if not row.get("rejected_serial_and_batch_bundle"):
			return self.get_package_for_target_warehouse(row, row.from_warehouse, "Inward")

		return self.get_returned_source_package(row)

	def get_source_warehouse_package(self, row, package):
		if not (row.get("rejected_serial_and_batch_bundle") and self.is_internal_receipt()):
			return package

		if existing_package := self.get_package_of_source_warehouse(row):
			return existing_package

		if not package:
			return self.make_package_for_transfer(
				row.rejected_serial_and_batch_bundle, row.from_warehouse, type_of_transaction="Outward"
			)

		return self.make_package_for_transfer(
			package,
			row.from_warehouse,
			type_of_transaction="Outward",
			include_bundle=row.rejected_serial_and_batch_bundle,
		)

	def get_package_of_source_warehouse(self, row) -> str | None:
		return frappe.db.get_value(
			"Serial and Batch Bundle",
			{
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"voucher_detail_no": row.name,
				"warehouse": row.from_warehouse,
				"docstatus": 1,
				"is_cancelled": 0,
			},
			"name",
		)

	def get_returned_source_package(self, row):
		if not row.serial_and_batch_bundle:
			return self.make_package_for_transfer(
				row.rejected_serial_and_batch_bundle, row.from_warehouse, type_of_transaction="Inward"
			)

		return self.make_package_for_transfer(
			row.serial_and_batch_bundle,
			row.from_warehouse,
			type_of_transaction="Inward",
			include_bundle=row.rejected_serial_and_batch_bundle,
		)

	def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
		self.update_ordered_and_reserved_qty()

		sl_entries = []
		stock_items = self.get_stock_items()

		for d in self.get("items"):
			if d.item_code not in stock_items:
				continue

			source_reversal_sle = None

			pr_qty = self.get_accepted_stock_qty(d)
			source_qty = self.get_source_warehouse_qty(d, pr_qty)

			if source_qty and (d.warehouse or not pr_qty):
				if d.from_warehouse and (
					(not cint(self.is_return) and self.docstatus == 1)
					or (cint(self.is_return) and self.docstatus == 2)
				):
					serial_and_batch_bundle = d.get("serial_and_batch_bundle")
					if self.is_internal_transfer() and self.is_return and self.docstatus == 2:
						serial_and_batch_bundle = frappe.db.get_value(
							"Stock Ledger Entry",
							{"voucher_detail_no": d.name, "warehouse": d.from_warehouse},
							"serial_and_batch_bundle",
						)

					from_warehouse_sle = self.get_sl_entries(
						d,
						{
							"actual_qty": -1 * source_qty,
							"warehouse": d.from_warehouse,
							"outgoing_rate": d.rate,
							"recalculate_rate": 1,
							"dependant_sle_voucher_detail_no": d.name,
							"serial_and_batch_bundle": self.get_source_warehouse_package(
								d, serial_and_batch_bundle
							),
						},
					)

					sl_entries.append(from_warehouse_sle)

				type_of_transaction = "Inward"
				if self.docstatus == 2:
					type_of_transaction = "Outward"

				sle = self.get_sl_entries(
					d,
					{
						"actual_qty": flt(pr_qty),
						"serial_and_batch_bundle": self.get_accepted_warehouse_package(
							d, type_of_transaction, via_landed_cost_voucher
						),
					},
				)

				if self.is_return:
					outgoing_rate = get_rate_for_return(
						self.doctype, self.name, d.item_code, self.return_against, item_row=d
					)

					sle.update(
						{
							"outgoing_rate": outgoing_rate,
							"recalculate_rate": 1,
							"serial_and_batch_bundle": d.serial_and_batch_bundle,
						}
					)
					if d.from_warehouse:
						sle.dependant_sle_voucher_detail_no = d.name
				else:
					sle.update(
						{
							"incoming_rate": d.valuation_rate,
							"recalculate_rate": 1
							if (self.is_subcontracted and (d.bom or d.get("fg_item"))) or d.from_warehouse
							else 0,
						}
					)
				sl_entries.append(sle)

				if d.from_warehouse and (
					(not cint(self.is_return) and self.docstatus == 2)
					or (cint(self.is_return) and self.docstatus == 1)
				):
					serial_and_batch_bundle = None
					if self.is_internal_transfer() and self.docstatus == 2:
						reversed_warehouse = (
							d.from_warehouse if d.get("rejected_serial_and_batch_bundle") else d.warehouse
						)
						serial_and_batch_bundle = self.get_submitted_package(d, reversed_warehouse)

					from_warehouse_sle = self.get_sl_entries(
						d,
						{
							"actual_qty": -1 * source_qty,
							"warehouse": d.from_warehouse,
							"recalculate_rate": 1,
							"serial_and_batch_bundle": self.get_source_warehouse_reversal_package(
								d, serial_and_batch_bundle
							),
						},
					)

					if self.is_internal_transfer() and self.is_return:
						from_warehouse_sle.incoming_rate = get_rate_for_return(
							self.doctype, self.name, d.item_code, self.return_against, item_row=d
						)

					source_reversal_sle = from_warehouse_sle

			if flt(d.rejected_qty) != 0:
				valuation_rate_for_rejected_item = self.get_rejected_valuation_rate(d)

				sl_entries.append(
					self.get_sl_entries(
						d,
						{
							"warehouse": d.rejected_warehouse,
							"actual_qty": get_stock_qty(d, d.rejected_qty),
							"incoming_rate": valuation_rate_for_rejected_item if not self.is_return else 0.0,
							"outgoing_rate": valuation_rate_for_rejected_item if self.is_return else 0.0,
							"serial_and_batch_bundle": d.rejected_serial_and_batch_bundle,
						},
					)
				)

			if source_reversal_sle:
				sl_entries.append(source_reversal_sle)

		if self.get("is_old_subcontracting_flow"):
			self.make_sl_entries_for_supplier_warehouse(sl_entries)

		self.make_sl_entries(
			sl_entries,
			allow_negative_stock=allow_negative_stock,
			via_landed_cost_voucher=via_landed_cost_voucher,
		)

	def get_package_for_target_warehouse(
		self, item, warehouse=None, type_of_transaction=None, via_landed_cost_voucher=None
	) -> str:
		if via_landed_cost_voucher and item.get("warehouse"):
			if sabb := frappe.db.get_value(
				"Serial and Batch Bundle",
				{
					"voucher_detail_no": item.name,
					"warehouse": item.get("warehouse"),
					"docstatus": 1,
					"is_cancelled": 0,
				},
				"name",
			):
				return sabb

		if not item.serial_and_batch_bundle:
			return ""

		if not warehouse:
			warehouse = item.warehouse

		return self.make_package_for_transfer(
			item.serial_and_batch_bundle, warehouse, type_of_transaction=type_of_transaction
		)

	def update_ordered_and_reserved_qty(self):
		po_map = {}
		for d in self.get("items"):
			if self.doctype == "Purchase Receipt" and d.purchase_order:
				po_map.setdefault(d.purchase_order, []).append(d.purchase_order_item)

			elif self.doctype == "Purchase Invoice" and d.purchase_order and d.po_detail:
				po_map.setdefault(d.purchase_order, []).append(d.po_detail)

		for po, po_item_rows in po_map.items():
			if po and po_item_rows:
				po_obj = frappe.get_doc("Purchase Order", po)

				if po_obj.status == "Cancelled" or (po_obj.status == "Closed" and not self.get("is_return")):
					frappe.throw(
						_("{0} {1} is cancelled or closed").format(_("Purchase Order"), po),
						frappe.InvalidStatusError,
					)

				po_obj.update_ordered_qty(po_item_rows)
				if self.get("is_old_subcontracting_flow"):
					po_obj.update_reserved_qty_for_subcontract()

	def on_submit(self):
		if self.get("is_return"):
			return

		if self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			self.process_fixed_asset()

		if self.doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
			update_last_purchase_rate(self, is_submit=1)

	def on_cancel(self):
		super().on_cancel()

		if self.get("is_return"):
			return

		if self.doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
			update_last_purchase_rate(self, is_submit=0)

		if self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			field = "purchase_invoice" if self.doctype == "Purchase Invoice" else "purchase_receipt"

			self.delete_linked_asset()
			self.update_fixed_asset(field, delete_asset=True)

	def validate_budget(self):
		if self.docstatus == 1:
			for data in self.get("items"):
				args = data.as_dict()
				args.update(
					{
						"doctype": self.doctype,
						"company": self.company,
						"posting_date": (
							self.schedule_date
							if self.doctype == "Material Request"
							else self.transaction_date
						),
					}
				)

				validate_expense_against_budget(args)

	def process_fixed_asset(self):
		if self.doctype == "Purchase Invoice" and not self.update_stock:
			return

		asset_items = self.get_asset_items()
		if asset_items:
			self.auto_make_assets(asset_items)

	def auto_make_assets(self, asset_items):
		items_data = get_asset_item_details(asset_items)
		messages = []
		accounting_dimensions = get_dimensions(with_cost_center_and_project=True)

		for d in self.items:
			if d.is_fixed_asset:
				item_data = items_data.get(d.item_code)

				if item_data.get("auto_create_assets"):
					# If asset has to be auto created
					# Check for asset naming series
					if item_data.get("asset_naming_series"):
						created_assets = []
						if item_data.get("is_grouped_asset"):
							asset = self.make_asset(d, accounting_dimensions, is_grouped_asset=True)
							created_assets.append(asset)
						else:
							for _qty in range(cint(d.qty)):
								asset = self.make_asset(d, accounting_dimensions)
								created_assets.append(asset)

						if len(created_assets) > 5:
							# dont show asset form links if more than 5 assets are created
							messages.append(
								_("{} Assets created for {}").format(
									len(created_assets), frappe.bold(d.item_code)
								)
							)
						else:
							assets_link = list(
								map(lambda d: frappe.utils.get_link_to_form("Asset", d), created_assets)
							)
							assets_link = frappe.bold(",".join(assets_link))

							is_plural = "s" if len(created_assets) != 1 else ""
							messages.append(
								_("Asset{is_plural} {assets_link} created for {item_code}").format(
									is_plural=is_plural,
									assets_link=assets_link,
									item_code=frappe.bold(d.item_code),
								)
							)
					else:
						frappe.throw(
							_(
								"Row {}: Asset Naming Series is mandatory for the auto creation for item {}"
							).format(d.idx, frappe.bold(d.item_code))
						)
				else:
					messages.append(
						_("Assets not created for {0}. You will have to create asset manually.").format(
							frappe.bold(d.item_code)
						)
					)

		for message in messages:
			frappe.msgprint(message, title="Success", indicator="green")

	def make_asset(self, row, accounting_dimensions, is_grouped_asset=False):
		if not row.asset_location:
			frappe.throw(_("Row {0}: Enter location for the asset item {1}").format(row.idx, row.item_code))

		item_data = frappe.get_cached_value(
			"Item", row.item_code, ["asset_naming_series", "asset_category"], as_dict=1
		)
		asset_quantity = row.qty if is_grouped_asset else 1
		purchase_amount = flt(row.valuation_rate) * flt(row.conversion_factor or 1) * asset_quantity

		asset = frappe.get_doc(
			{
				"doctype": "Asset",
				"item_code": row.item_code,
				"asset_name": row.item_name,
				"naming_series": item_data.get("asset_naming_series") or "AST",
				"asset_category": item_data.get("asset_category"),
				"location": row.asset_location,
				"company": self.company,
				"status": "Draft",
				"supplier": self.supplier,
				"purchase_date": self.posting_date,
				"calculate_depreciation": 0,
				"purchase_amount": purchase_amount,
				"gross_purchase_amount": purchase_amount,
				"asset_quantity": asset_quantity,
				"purchase_receipt": self.name if self.doctype == "Purchase Receipt" else None,
				"purchase_invoice": self.name if self.doctype == "Purchase Invoice" else None,
				"purchase_receipt_item": row.name if self.doctype == "Purchase Receipt" else None,
				"purchase_invoice_item": row.name if self.doctype == "Purchase Invoice" else None,
			}
		)
		for dimension in accounting_dimensions[0]:
			asset.update(
				{
					dimension["fieldname"]: self.get(dimension["fieldname"])
					or dimension.get("default_dimension")
				}
			)

		asset.flags.ignore_validate = True
		asset.flags.ignore_mandatory = True
		asset.set_missing_values()
		asset.db_insert()

		return asset.name

	def update_fixed_asset(self, field, delete_asset=False):
		for d in self.get("items"):
			if d.is_fixed_asset:
				is_auto_create_enabled = frappe.db.get_value("Item", d.item_code, "auto_create_assets")
				assets = frappe.db.get_all("Asset", filters={field: self.name, "item_code": d.item_code})

				for asset in assets:
					asset = frappe.get_doc("Asset", asset.name)
					if delete_asset and is_auto_create_enabled:
						# need to delete movements to delete assets otherwise throws link exists error
						movements = frappe.db.sql(
							"""SELECT asm.name
							FROM `tabAsset Movement` asm, `tabAsset Movement Item` asm_item
							WHERE asm_item.parent=asm.name and asm_item.asset=%s""",
							asset.name,
							as_dict=1,
						)
						for movement in movements:
							frappe.delete_doc("Asset Movement", movement.name, force=1)
						frappe.delete_doc("Asset", asset.name, force=1)
						continue

					if self.docstatus == 2:
						if asset.docstatus == 2:
							continue
						if asset.docstatus == 0:
							asset.set(field, None)
							asset.supplier = None
						if asset.docstatus == 1 and delete_asset:
							frappe.throw(
								_(
									"Cannot cancel this document as it is linked with submitted asset {0}. Please cancel it to continue."
								).format(frappe.utils.get_link_to_form("Asset", asset.name))
							)

					asset.flags.ignore_validate_update_after_submit = True
					asset.flags.ignore_mandatory = True
					if asset.docstatus == 0:
						asset.flags.ignore_validate = True

					asset.save()

	def delete_linked_asset(self):
		if self.doctype == "Purchase Invoice" and not self.get("update_stock"):
			return

		asset_movement = frappe.db.get_value("Asset Movement", {"reference_name": self.name}, "name")
		frappe.delete_doc("Asset Movement", asset_movement, force=1)

	def validate_schedule_date(self):
		if not self.get("items"):
			return

		if any(d.schedule_date for d in self.get("items")):
			# Select earliest schedule_date.
			self.schedule_date = min(
				d.schedule_date for d in self.get("items") if d.schedule_date is not None
			)

		if self.schedule_date:
			for d in self.get("items"):
				if not d.schedule_date:
					d.schedule_date = self.schedule_date

				if (
					d.schedule_date
					and self.transaction_date
					and getdate(d.schedule_date) < getdate(self.transaction_date)
				):
					frappe.throw(_("Row #{0}: Reqd by Date cannot be before Transaction Date").format(d.idx))
		else:
			frappe.throw(_("Please enter Reqd by Date"))

	def validate_items(self):
		# validate items to see if they have is_purchase_item or is_subcontracted_item enabled
		if self.doctype == "Material Request":
			return

		if self.get("is_old_subcontracting_flow"):
			validate_item_type(self, "is_sub_contracted_item", "subcontracted")
		else:
			validate_item_type(self, "is_purchase_item", "purchase")


def get_asset_item_details(asset_items):
	asset_items_data = {}
	for d in frappe.get_all(
		"Item",
		fields=["name", "auto_create_assets", "asset_naming_series", "is_grouped_asset"],
		filters={"name": ("in", asset_items)},
	):
		asset_items_data.setdefault(d.name, d)

	return asset_items_data


def validate_item_type(doc, fieldname, message):
	# iterate through items and check if they are valid sales or purchase items
	items = [d.item_code for d in doc.items if d.item_code]

	# No validation check inase of creating transaction using 'Opening Invoice Creation Tool'
	if not items:
		return

	item_list = ", ".join(["%s" % frappe.db.escape(d) for d in items])

	invalid_items = [
		d[0]
		for d in frappe.db.sql(
			f"""
		select item_code from tabItem where name in ({item_list}) and {fieldname}=0
		""",
			as_list=True,
		)
	]

	if invalid_items:
		items = ", ".join([d for d in invalid_items])

		if len(invalid_items) > 1:
			error_message = _(
				"Following items {0} are not marked as {1} item. You can enable them as {1} item from its Item master"
			).format(items, message)
		else:
			error_message = _(
				"Following item {0} is not marked as {1} item. You can enable them as {1} item from its Item master"
			).format(items, message)

		frappe.throw(error_message)


@erpnext.allow_regional
def update_regional_item_valuation_rate(doc):
	pass


def get_stock_qty(row, qty) -> float:
	"""Qty of a row in the stock UOM, rounded as the stock ledger posts it."""
	return flt(flt(qty) * flt(row.conversion_factor), row.precision("stock_qty"))


def get_transit_amount(row, qty) -> float:
	"""Value of qty of an internal transfer row at its transit rate, as the stock ledger moves it."""
	return get_stock_qty(row, qty) * flt(row.sales_incoming_rate) / flt(row.conversion_factor)


def get_linked_asset_qty(detail_field, details, exclude_asset=None):
	asset = frappe.qb.DocType("Asset")
	query = (
		frappe.qb.from_(asset)
		.select(asset[detail_field], Sum(asset.asset_quantity))
		.where((asset[detail_field].isin(details)) & (asset.docstatus < 2))
		.groupby(asset[detail_field])
	)
	if exclude_asset:
		query = query.where(asset.name != exclude_asset)
	return dict(query.run())


def get_stock_qty_status_args(round_total=True) -> dict:
	"""Status updater args that add up rows' stock qty. When rows round their stock qty, add up qty * conversion
	factor instead, rounded once at the total if the target rounds its stock qty too, so parts add up to it."""
	if not frappe.get_single_value("Stock Settings", "allow_to_edit_stock_uom_qty_for_purchase"):
		return {"source_field": "stock_qty"}

	return {"source_field": "qty * conversion_factor", "round_to_target_precision": round_total}


def get_received_stock_qty_status_args() -> dict:
	"""Status updater args that add up receipts' stock qty. A receipt rounds the stock qty of each row whatever the
	setting, so add up qty * conversion factor, rounded once at the total where the target rounds its stock qty too."""
	return {"source_field": "qty * conversion_factor", "round_to_target_precision": rounds_stock_qty}


def rounds_stock_qty(row) -> bool:
	"""Whether set_qty_as_per_stock_uom rounds the stock qty of a purchase row."""
	return bool(
		frappe.get_single_value("Stock Settings", "allow_to_edit_stock_uom_qty_for_purchase")
		or frappe.get_cached_value("UOM", row.stock_uom, "must_be_whole_number")
	)


def get_returned_stock_qty_status_args() -> dict:
	"""Status updater args that add up the received stock qty of a receipt's returns. Add up qty * conversion
	factor, rounded once at the total where the receipt row rounds its received stock qty, so parts add up to it."""
	return {
		"source_field": "-1 * received_qty * conversion_factor",
		"round_to_target_precision": rounds_received_stock_qty,
	}


def rounds_received_stock_qty(row) -> bool:
	"""Whether a receipt row stores its received stock qty rounded: a stock or asset row rounds it when valued."""
	is_stock_item, is_fixed_asset = frappe.get_cached_value(
		"Item", row.item_code, ["is_stock_item", "is_fixed_asset"]
	)
	return bool(is_stock_item or is_fixed_asset or rounds_stock_qty(row))
