# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import ValidationError, _, msgprint
from frappe.contacts.doctype.address.address import get_address_display
from frappe.utils import cint, cstr, flt, getdate

from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget
from erpnext.accounts.party import get_party_details
from erpnext.buying.utils import update_last_purchase_rate, validate_for_items
from erpnext.controllers.sales_and_purchase_return import get_rate_for_return
from erpnext.controllers.stock_controller import StockController
from erpnext.controllers.subcontracting import Subcontracting
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import get_incoming_rate


class QtyMismatchError(ValidationError):
	pass


class BuyingController(StockController, Subcontracting):
	def __setup__(self):
		self.flags.ignore_permlevel_for_fields = ["buying_price_list", "price_list_currency"]

	def get_feed(self):
		if self.get("supplier_name"):
			return _("From {0} | {1} {2}").format(self.supplier_name, self.currency, self.grand_total)

	def validate(self):
		super(BuyingController, self).validate()
		if getattr(self, "supplier", None) and not self.supplier_name:
			self.supplier_name = frappe.db.get_value("Supplier", self.supplier, "supplier_name")

		self.validate_items()
		self.set_qty_as_per_stock_uom()
		self.validate_stock_or_nonstock_items()
		self.validate_warehouse()
		self.validate_from_warehouse()
		self.set_supplier_address()
		self.validate_asset_return()

		if self.doctype == "Purchase Invoice":
			self.validate_purchase_receipt_if_update_stock()

		if self.doctype == "Purchase Receipt" or (
			self.doctype == "Purchase Invoice" and self.update_stock
		):
			# self.validate_purchase_return()
			self.validate_rejected_warehouse()
			self.validate_accepted_rejected_qty()
			validate_for_items(self)

			# sub-contracting
			self.validate_for_subcontracting()
			self.create_raw_materials_supplied("supplied_items")
			self.set_landed_cost_voucher_amount()

		if self.doctype in ("Purchase Receipt", "Purchase Invoice"):
			self.update_valuation_rate()

	def onload(self):
		super(BuyingController, self).onload()
		self.set_onload(
			"backflush_based_on",
			frappe.db.get_single_value(
				"Buying Settings", "backflush_raw_materials_of_subcontract_based_on"
			),
		)

	def set_missing_values(self, for_validate=False):
		super(BuyingController, self).set_missing_values(for_validate)

		self.set_supplier_from_item_default()
		self.set_price_list_currency("Buying")

		# set contact and address details for supplier, if they are not mentioned
		if getattr(self, "supplier", None):
			self.update_if_missing(
				get_party_details(
					self.supplier,
					party_type="Supplier",
					doctype=self.doctype,
					company=self.company,
					party_address=self.get("supplier_address"),
					shipping_address=self.get("shipping_address"),
					company_address=self.get("billing_address"),
					fetch_payment_terms_template=not self.get("ignore_default_payment_terms_template"),
					ignore_permissions=self.flags.ignore_permissions,
				)
			)

		self.set_missing_item_details(for_validate)

	def set_supplier_from_item_default(self):
		if self.meta.get_field("supplier") and not self.supplier:
			for d in self.get("items"):
				supplier = frappe.db.get_value(
					"Item Default", {"parent": d.item_code, "company": self.company}, "default_supplier"
				)
				if supplier:
					self.supplier = supplier
				else:
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

		purchase_doc_field = (
			"purchase_receipt" if self.doctype == "Purchase Receipt" else "purchase_invoice"
		)
		not_cancelled_asset = [
			d.name
			for d in frappe.db.get_all("Asset", {purchase_doc_field: self.return_against, "docstatus": 1})
		]
		if self.is_return and len(not_cancelled_asset):
			frappe.throw(
				_(
					"{} has submitted assets linked to it. You need to cancel the assets to create purchase return."
				).format(self.return_against),
				title=_("Not Allowed"),
			)

	def get_asset_items(self):
		if self.doctype not in ["Purchase Order", "Purchase Invoice", "Purchase Receipt"]:
			return []

		return [d.item_code for d in self.items if d.is_fixed_asset]

	def set_landed_cost_voucher_amount(self):
		for d in self.get("items"):
			lc_voucher_data = frappe.db.sql(
				"""select sum(applicable_charges), cost_center
				from `tabLanded Cost Item`
				where docstatus = 1 and purchase_receipt_item = %s""",
				d.name,
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

			if item.get("from_warehouse") and self.get("is_subcontracted") == "Yes":
				frappe.throw(
					_(
						"Row #{0}: Cannot select Supplier Warehouse while suppling raw materials to subcontractor"
					).format(item.idx)
				)

	def set_supplier_address(self):
		address_dict = {
			"supplier_address": "address_display",
			"shipping_address": "shipping_address_display",
		}

		for address_field, address_display_field in address_dict.items():
			if self.get(address_field):
				self.set(address_display_field, get_address_display(self.get(address_field)))

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
		for d in self.get("items"):
			if d.item_code and d.item_code in stock_and_asset_items:
				stock_and_asset_items_qty += flt(d.qty)
				stock_and_asset_items_amount += flt(d.base_net_amount)
				last_item_idx = d.idx

		total_valuation_amount = sum(
			flt(d.base_tax_amount_after_discount_amount)
			for d in self.get("taxes")
			if d.category in ["Valuation", "Valuation and Total"]
		)

		valuation_amount_adjustment = total_valuation_amount
		for i, item in enumerate(self.get("items")):
			if item.item_code and item.qty and item.item_code in stock_and_asset_items:
				item_proportion = (
					flt(item.base_net_amount) / stock_and_asset_items_amount
					if stock_and_asset_items_amount
					else flt(item.qty) / stock_and_asset_items_qty
				)

				if i == (last_item_idx - 1):
					item.item_tax_amount = flt(
						valuation_amount_adjustment, self.precision("item_tax_amount", item)
					)
				else:
					item.item_tax_amount = flt(
						item_proportion * total_valuation_amount, self.precision("item_tax_amount", item)
					)
					valuation_amount_adjustment -= item.item_tax_amount

				self.round_floats_in(item)
				if flt(item.conversion_factor) == 0.0:
					item.conversion_factor = (
						get_conversion_factor(item.item_code, item.uom).get("conversion_factor") or 1.0
					)

				qty_in_stock_uom = flt(item.qty * item.conversion_factor)
				item.rm_supp_cost = self.get_supplied_items_cost(item.name, reset_outgoing_rate)
				item.valuation_rate = (
					item.base_net_amount
					+ item.item_tax_amount
					+ item.rm_supp_cost
					+ flt(item.landed_cost_voucher_amount)
				) / qty_in_stock_uom
			else:
				item.valuation_rate = 0.0

	def set_incoming_rate(self):
		if self.doctype not in ("Purchase Receipt", "Purchase Invoice", "Purchase Order"):
			return

		ref_doctype_map = {
			"Purchase Order": "Sales Order Item",
			"Purchase Receipt": "Delivery Note Item",
			"Purchase Invoice": "Sales Invoice Item",
		}

		ref_doctype = ref_doctype_map.get(self.doctype)
		items = self.get("items")
		for d in items:
			if not cint(self.get("is_return")):
				# Get outgoing rate based on original item cost based on valuation method

				if not d.get(frappe.scrub(ref_doctype)):
					outgoing_rate = get_incoming_rate(
						{
							"item_code": d.item_code,
							"warehouse": d.get("from_warehouse"),
							"posting_date": self.get("posting_date") or self.get("transation_date"),
							"posting_time": self.get("posting_time"),
							"qty": -1 * flt(d.get("stock_qty")),
							"serial_no": d.get("serial_no"),
							"company": self.company,
							"voucher_type": self.doctype,
							"voucher_no": self.name,
							"allow_zero_valuation": d.get("allow_zero_valuation"),
						},
						raise_error_if_no_rate=False,
					)

					rate = flt(outgoing_rate * (d.conversion_factor or 1), d.precision("rate"))
				else:
					field = "incoming_rate" if self.get("is_internal_supplier") else "rate"
					rate = flt(
						frappe.db.get_value(ref_doctype, d.get(frappe.scrub(ref_doctype)), field)
						* (d.conversion_factor or 1),
						d.precision("rate"),
					)

				if self.is_internal_transfer():
					if rate != d.rate:
						d.rate = rate
						frappe.msgprint(
							_(
								"Row {0}: Item rate has been updated as per valuation rate since its an internal stock transfer"
							).format(d.idx),
							alert=1,
						)
					d.discount_percentage = 0.0
					d.discount_amount = 0.0
					d.margin_rate_or_amount = 0.0

	def get_supplied_items_cost(self, item_row_id, reset_outgoing_rate=True):
		supplied_items_cost = 0.0
		for d in self.get("supplied_items"):
			if d.reference_name == item_row_id:
				if reset_outgoing_rate and frappe.get_cached_value("Item", d.rm_item_code, "is_stock_item"):
					rate = get_incoming_rate(
						{
							"item_code": d.rm_item_code,
							"warehouse": self.supplier_warehouse,
							"posting_date": self.posting_date,
							"posting_time": self.posting_time,
							"qty": -1 * d.consumed_qty,
							"serial_no": d.serial_no,
						}
					)

					if rate > 0:
						d.rate = rate

				d.amount = flt(flt(d.consumed_qty) * flt(d.rate), d.precision("amount"))
				supplied_items_cost += flt(d.amount)

		return supplied_items_cost

	def validate_for_subcontracting(self):
		if not self.is_subcontracted and self.sub_contracted_items:
			frappe.throw(_("Please enter 'Is Subcontracted' as Yes or No"))

		if self.is_subcontracted == "Yes":
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
				if item.bom:
					item.bom = None

	def create_raw_materials_supplied(self, raw_material_table):
		if self.is_subcontracted == "Yes":
			self.set_materials_for_subcontracted_items(raw_material_table)

		elif self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			for item in self.get("items"):
				item.rm_supp_cost = 0.0

		if self.is_subcontracted == "No" and self.get("supplied_items"):
			self.set("supplied_items", [])

	@property
	def sub_contracted_items(self):
		if not hasattr(self, "_sub_contracted_items"):
			self._sub_contracted_items = []
			item_codes = list(set(item.item_code for item in self.get("items")))
			if item_codes:
				items = frappe.get_all(
					"Item", filters={"name": ["in", item_codes], "is_sub_contracted_item": 1}
				)
				self._sub_contracted_items = [item.name for item in items]

		return self._sub_contracted_items

	def set_qty_as_per_stock_uom(self):
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

	def validate_purchase_return(self):
		for d in self.get("items"):
			if self.is_return and flt(d.rejected_qty) != 0:
				frappe.throw(_("Row #{0}: Rejected Qty can not be entered in Purchase Return").format(d.idx))

			# validate rate with ref PR

	def validate_rejected_warehouse(self):
		for d in self.get("items"):
			if flt(d.rejected_qty) and not d.rejected_warehouse:
				if self.rejected_warehouse:
					d.rejected_warehouse = self.rejected_warehouse

				if not d.rejected_warehouse:
					frappe.throw(
						_("Row #{0}: Rejected Warehouse is mandatory against rejected Item {1}").format(
							d.idx, d.item_code
						)
					)

	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in self.get("items"):
			self.validate_negative_quantity(d, ["received_qty", "qty", "rejected_qty"])

			if not flt(d.received_qty) and (flt(d.qty) or flt(d.rejected_qty)):
				d.received_qty = flt(d.qty) + flt(d.rejected_qty)

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
		for d in self.get("items"):
			if d.get(ref_fieldname):
				status = frappe.db.get_value(ref_doctype, d.get(ref_fieldname), "status")
				if status in ("Closed", "On Hold"):
					frappe.throw(_("{0} {1} is {2}").format(ref_doctype, d.get(ref_fieldname), status))

	def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
		self.update_ordered_and_reserved_qty()

		sl_entries = []
		stock_items = self.get_stock_items()

		for d in self.get("items"):
			if d.item_code not in stock_items:
				continue

			if d.warehouse:
				pr_qty = flt(d.qty) * flt(d.conversion_factor)

				if pr_qty:

					if d.from_warehouse and (
						(not cint(self.is_return) and self.docstatus == 1)
						or (cint(self.is_return) and self.docstatus == 2)
					):
						from_warehouse_sle = self.get_sl_entries(
							d,
							{
								"actual_qty": -1 * pr_qty,
								"warehouse": d.from_warehouse,
								"outgoing_rate": d.rate,
								"recalculate_rate": 1,
								"dependant_sle_voucher_detail_no": d.name,
							},
						)

						sl_entries.append(from_warehouse_sle)

					sle = self.get_sl_entries(
						d, {"actual_qty": flt(pr_qty), "serial_no": cstr(d.serial_no).strip()}
					)

					if self.is_return:
						outgoing_rate = get_rate_for_return(
							self.doctype, self.name, d.item_code, self.return_against, item_row=d
						)

						sle.update({"outgoing_rate": outgoing_rate, "recalculate_rate": 1})
						if d.from_warehouse:
							sle.dependant_sle_voucher_detail_no = d.name
					else:
						val_rate_db_precision = 6 if cint(self.precision("valuation_rate", d)) <= 6 else 9
						incoming_rate = flt(d.valuation_rate, val_rate_db_precision)
						sle.update(
							{
								"incoming_rate": incoming_rate,
								"recalculate_rate": 1 if (self.is_subcontracted and d.bom) or d.from_warehouse else 0,
							}
						)
					sl_entries.append(sle)

					if d.from_warehouse and (
						(not cint(self.is_return) and self.docstatus == 2)
						or (cint(self.is_return) and self.docstatus == 1)
					):
						from_warehouse_sle = self.get_sl_entries(
							d, {"actual_qty": -1 * pr_qty, "warehouse": d.from_warehouse, "recalculate_rate": 1}
						)

						sl_entries.append(from_warehouse_sle)

			if flt(d.rejected_qty) != 0:
				sl_entries.append(
					self.get_sl_entries(
						d,
						{
							"warehouse": d.rejected_warehouse,
							"actual_qty": flt(d.rejected_qty) * flt(d.conversion_factor),
							"serial_no": cstr(d.rejected_serial_no).strip(),
							"incoming_rate": 0.0,
						},
					)
				)

		self.make_sl_entries_for_supplier_warehouse(sl_entries)
		self.make_sl_entries(
			sl_entries,
			allow_negative_stock=allow_negative_stock,
			via_landed_cost_voucher=via_landed_cost_voucher,
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

				if po_obj.status in ["Closed", "Cancelled"]:
					frappe.throw(
						_("{0} {1} is cancelled or closed").format(_("Purchase Order"), po),
						frappe.InvalidStatusError,
					)

				po_obj.update_ordered_qty(po_item_rows)
				if self.is_subcontracted:
					po_obj.update_reserved_qty_for_subcontract()

	def make_sl_entries_for_supplier_warehouse(self, sl_entries):
		if hasattr(self, "supplied_items"):
			for d in self.get("supplied_items"):
				# negative quantity is passed, as raw material qty has to be decreased
				# when PR is submitted and it has to be increased when PR is cancelled
				sl_entries.append(
					self.get_sl_entries(
						d,
						{
							"item_code": d.rm_item_code,
							"warehouse": self.supplier_warehouse,
							"actual_qty": -1 * flt(d.consumed_qty),
							"dependant_sle_voucher_detail_no": d.reference_name,
						},
					)
				)

	def on_submit(self):
		if self.get("is_return"):
			return

		if self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			field = "purchase_invoice" if self.doctype == "Purchase Invoice" else "purchase_receipt"

			self.process_fixed_asset()
			self.update_fixed_asset(field)

		if self.doctype in ["Purchase Order", "Purchase Receipt"]:
			update_last_purchase_rate(self, is_submit=1)

	def on_cancel(self):
		super(BuyingController, self).on_cancel()

		if self.get("is_return"):
			return

		if self.doctype in ["Purchase Order", "Purchase Receipt"]:
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
							self.schedule_date if self.doctype == "Material Request" else self.transaction_date
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

		for d in self.items:
			if d.is_fixed_asset:
				item_data = items_data.get(d.item_code)

				if item_data.get("auto_create_assets"):
					# If asset has to be auto created
					# Check for asset naming series
					if item_data.get("asset_naming_series"):
						created_assets = []

						for qty in range(cint(d.qty)):
							asset = self.make_asset(d)
							created_assets.append(asset)

						if len(created_assets) > 5:
							# dont show asset form links if more than 5 assets are created
							messages.append(
								_("{} Assets created for {}").format(len(created_assets), frappe.bold(d.item_code))
							)
						else:
							assets_link = list(map(lambda d: frappe.utils.get_link_to_form("Asset", d), created_assets))
							assets_link = frappe.bold(",".join(assets_link))

							is_plural = "s" if len(created_assets) != 1 else ""
							messages.append(
								_("Asset{} {assets_link} created for {}").format(
									is_plural, frappe.bold(d.item_code), assets_link=assets_link
								)
							)
					else:
						frappe.throw(
							_("Row {}: Asset Naming Series is mandatory for the auto creation for item {}").format(
								d.idx, frappe.bold(d.item_code)
							)
						)
				else:
					messages.append(
						_("Assets not created for {0}. You will have to create asset manually.").format(
							frappe.bold(d.item_code)
						)
					)

		for message in messages:
			frappe.msgprint(message, title="Success", indicator="green")

	def make_asset(self, row):
		if not row.asset_location:
			frappe.throw(_("Row {0}: Enter location for the asset item {1}").format(row.idx, row.item_code))

		item_data = frappe.db.get_value(
			"Item", row.item_code, ["asset_naming_series", "asset_category"], as_dict=1
		)

		purchase_amount = flt(row.base_rate + row.item_tax_amount)
		asset = frappe.get_doc(
			{
				"doctype": "Asset",
				"item_code": row.item_code,
				"asset_name": row.item_name,
				"naming_series": item_data.get("asset_naming_series") or "AST",
				"asset_category": item_data.get("asset_category"),
				"location": row.asset_location,
				"company": self.company,
				"supplier": self.supplier,
				"purchase_date": self.posting_date,
				"calculate_depreciation": 1,
				"purchase_receipt_amount": purchase_amount,
				"gross_purchase_amount": purchase_amount,
				"purchase_receipt": self.name if self.doctype == "Purchase Receipt" else None,
				"purchase_invoice": self.name if self.doctype == "Purchase Invoice" else None,
			}
		)

		asset.flags.ignore_validate = True
		asset.flags.ignore_mandatory = True
		asset.set_missing_values()
		asset.insert()

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

					if self.docstatus in [0, 1] and not asset.get(field):
						asset.set(field, self.name)
						asset.purchase_date = self.posting_date
						asset.supplier = self.supplier
					elif self.docstatus == 2:
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

		frappe.db.sql("delete from `tabAsset Movement` where reference_name=%s", self.name)

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

		if hasattr(self, "is_subcontracted") and self.is_subcontracted == "Yes":
			validate_item_type(self, "is_sub_contracted_item", "subcontracted")
		else:
			validate_item_type(self, "is_purchase_item", "purchase")


def get_asset_item_details(asset_items):
	asset_items_data = {}
	for d in frappe.get_all(
		"Item",
		fields=["name", "auto_create_assets", "asset_naming_series"],
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
			"""
		select item_code from tabItem where name in ({0}) and {1}=0
		""".format(
				item_list, fieldname
			),
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
