# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt,cint, cstr, getdate
from six import iteritems
from erpnext.accounts.party import get_party_details
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.buying.utils import validate_for_items, update_last_purchase_rate
from erpnext.stock.stock_ledger import get_valuation_rate
from erpnext.stock.doctype.stock_entry.stock_entry import get_used_alternative_items
from erpnext.stock.doctype.serial_no.serial_no import get_auto_serial_nos, auto_make_serial_nos, get_serial_nos
from frappe.contacts.doctype.address.address import get_address_display

from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget
from erpnext.controllers.stock_controller import StockController
from erpnext.controllers.sales_and_purchase_return import get_rate_for_return
from erpnext.stock.utils import get_incoming_rate

class BuyingController(StockController):
	def __setup__(self):
		if hasattr(self, "taxes"):
			self.flags.print_taxes_with_zero_amount = cint(frappe.db.get_single_value("Print Settings",
				 "print_taxes_with_zero_amount"))
			self.flags.show_inclusive_tax_in_print = self.is_inclusive_tax()

			self.print_templates = {
				"total": "templates/print_formats/includes/total.html",
				"taxes": "templates/print_formats/includes/taxes.html"
			}

	def get_feed(self):
		if self.get("supplier_name"):
			return _("From {0} | {1} {2}").format(self.supplier_name, self.currency,
				self.grand_total)

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

		if self.doctype=="Purchase Invoice":
			self.validate_purchase_receipt_if_update_stock()

		if self.doctype=="Purchase Receipt" or (self.doctype=="Purchase Invoice" and self.update_stock):
			# self.validate_purchase_return()
			self.validate_rejected_warehouse()
			self.validate_accepted_rejected_qty()
			validate_for_items(self)

			#sub-contracting
			self.validate_for_subcontracting()
			self.create_raw_materials_supplied("supplied_items")
			self.set_landed_cost_voucher_amount()

		if self.doctype in ("Purchase Receipt", "Purchase Invoice"):
			self.update_valuation_rate()

	def set_missing_values(self, for_validate=False):
		super(BuyingController, self).set_missing_values(for_validate)

		self.set_supplier_from_item_default()
		self.set_price_list_currency("Buying")

		# set contact and address details for supplier, if they are not mentioned
		if getattr(self, "supplier", None):
			self.update_if_missing(get_party_details(self.supplier, party_type="Supplier", ignore_permissions=self.flags.ignore_permissions,
			doctype=self.doctype, company=self.company, party_address=self.supplier_address, shipping_address=self.get('shipping_address')))

		self.set_missing_item_details(for_validate)

	def set_supplier_from_item_default(self):
		if self.meta.get_field("supplier") and not self.supplier:
			for d in self.get("items"):
				supplier = frappe.db.get_value("Item Default",
					{"parent": d.item_code, "company": self.company}, "default_supplier")
				if supplier:
					self.supplier = supplier
				else:
					item_group = frappe.db.get_value("Item", d.item_code, "item_group")
					supplier = frappe.db.get_value("Item Default",
					{"parent": item_group, "company": self.company}, "default_supplier")
					if supplier:
						self.supplier = supplier
					break

	def validate_stock_or_nonstock_items(self):
		if self.meta.get_field("taxes") and not self.get_stock_items() and not self.get_asset_items():
			msg = _('Tax Category has been changed to "Total" because all the Items are non-stock items')
			self.update_tax_category(msg)

	def update_tax_category(self, msg):
		tax_for_valuation = [d for d in self.get("taxes")
				if d.category in ["Valuation", "Valuation and Total"]]

		if tax_for_valuation:
			for d in tax_for_valuation:
				d.category = 'Total'

			msgprint(msg)

	def validate_asset_return(self):
		if self.doctype not in ['Purchase Receipt', 'Purchase Invoice'] or not self.is_return:
			return

		purchase_doc_field = 'purchase_receipt' if self.doctype == 'Purchase Receipt' else 'purchase_invoice'
		not_cancelled_asset = [d.name for d in frappe.db.get_all("Asset", {
			purchase_doc_field: self.return_against,
			"docstatus": 1
		})]
		if self.is_return and len(not_cancelled_asset):
			frappe.throw(_("{} has submitted assets linked to it. You need to cancel the assets to create purchase return.")
				.format(self.return_against), title=_("Not Allowed"))

	def get_asset_items(self):
		if self.doctype not in ['Purchase Order', 'Purchase Invoice', 'Purchase Receipt']:
			return []

		return [d.item_code for d in self.items if d.is_fixed_asset]

	def set_landed_cost_voucher_amount(self):
		for d in self.get("items"):
			lc_voucher_data = frappe.db.sql("""select sum(applicable_charges), cost_center
				from `tabLanded Cost Item`
				where docstatus = 1 and purchase_receipt_item = %s""", d.name)
			d.landed_cost_voucher_amount = lc_voucher_data[0][0] if lc_voucher_data else 0.0
			if not d.cost_center and lc_voucher_data and lc_voucher_data[0][1]:
				d.db_set('cost_center', lc_voucher_data[0][1])

	def validate_from_warehouse(self):
		for item in self.get('items'):
			if item.get('from_warehouse') and (item.get('from_warehouse') == item.get('warehouse')):
				frappe.throw(_("Row #{0}: Accepted Warehouse and Supplier Warehouse cannot be same").format(item.idx))

			if item.get('from_warehouse') and self.get('is_subcontracted') == 'Yes':
				frappe.throw(_("Row #{0}: Cannot select Supplier Warehouse while suppling raw materials to subcontractor").format(item.idx))

	def set_supplier_address(self):
		address_dict = {
			'supplier_address': 'address_display',
			'shipping_address': 'shipping_address_display'
		}

		for address_field, address_display_field in address_dict.items():
			if self.get(address_field):
				self.set(address_display_field, get_address_display(self.get(address_field)))

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		if self.meta.get_field("base_in_words"):
			if self.meta.get_field("base_rounded_total") and not self.is_rounded_total_disabled():
				amount = self.base_rounded_total
			else:
				amount = self.base_grand_total
			self.base_in_words = money_in_words(amount, self.company_currency)

		if self.meta.get_field("in_words"):
			if self.meta.get_field("rounded_total") and not self.is_rounded_total_disabled():
				amount = self.rounded_total
			else:
				amount = self.grand_total

			self.in_words = money_in_words(amount, self.currency)

	# update valuation rate
	def update_valuation_rate(self, reset_outgoing_rate=True):
		"""
			item_tax_amount is the total tax amount applied on that item
			stored for valuation

			TODO: rename item_tax_amount to valuation_tax_amount
		"""
		stock_and_asset_items = self.get_stock_items() + self.get_asset_items()

		stock_and_asset_items_qty, stock_and_asset_items_amount = 0, 0
		last_item_idx = 1
		for d in self.get("items"):
			if d.item_code and d.item_code in stock_and_asset_items:
				stock_and_asset_items_qty += flt(d.qty)
				stock_and_asset_items_amount += flt(d.base_net_amount)
				last_item_idx = d.idx

		total_valuation_amount = sum([flt(d.base_tax_amount_after_discount_amount) for d in self.get("taxes")
			if d.category in ["Valuation", "Valuation and Total"]])

		valuation_amount_adjustment = total_valuation_amount
		for i, item in enumerate(self.get("items")):
			if item.item_code and item.qty and item.item_code in stock_and_asset_items:
				item_proportion = flt(item.base_net_amount) / stock_and_asset_items_amount if stock_and_asset_items_amount \
					else flt(item.qty) / stock_and_asset_items_qty

				if i == (last_item_idx - 1):
					item.item_tax_amount = flt(valuation_amount_adjustment,
						self.precision("item_tax_amount", item))
				else:
					item.item_tax_amount = flt(item_proportion * total_valuation_amount,
						self.precision("item_tax_amount", item))
					valuation_amount_adjustment -= item.item_tax_amount

				self.round_floats_in(item)
				if flt(item.conversion_factor)==0.0:
					item.conversion_factor = get_conversion_factor(item.item_code, item.uom).get("conversion_factor") or 1.0

				qty_in_stock_uom = flt(item.qty * item.conversion_factor)
				item.rm_supp_cost = self.get_supplied_items_cost(item.name, reset_outgoing_rate)
				item.valuation_rate = ((item.base_net_amount + item.item_tax_amount + item.rm_supp_cost
					 + flt(item.landed_cost_voucher_amount)) / qty_in_stock_uom)
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
					outgoing_rate = get_incoming_rate({
						"item_code": d.item_code,
						"warehouse": d.get('from_warehouse'),
						"posting_date": self.get('posting_date') or self.get('transation_date'),
						"posting_time": self.get('posting_time'),
						"qty": -1 * flt(d.get('stock_qty')),
						"serial_no": d.get('serial_no'),
						"company": self.company,
						"voucher_type": self.doctype,
						"voucher_no": self.name,
						"allow_zero_valuation": d.get("allow_zero_valuation")
					}, raise_error_if_no_rate=False)

					rate = flt(outgoing_rate * d.conversion_factor, d.precision('rate'))
				else:
					rate = frappe.db.get_value(ref_doctype, d.get(frappe.scrub(ref_doctype)), 'rate')

				if self.is_internal_transfer():
					if rate != d.rate:
						d.rate = rate
						d.discount_percentage = 0
						d.discount_amount = 0
						frappe.msgprint(_("Row {0}: Item rate has been updated as per valuation rate since its an internal stock transfer")
							.format(d.idx), alert=1)

	def get_supplied_items_cost(self, item_row_id, reset_outgoing_rate=True):
		supplied_items_cost = 0.0
		for d in self.get("supplied_items"):
			if d.reference_name == item_row_id:
				if reset_outgoing_rate and frappe.db.get_value('Item', d.rm_item_code, 'is_stock_item'):
					rate = get_incoming_rate({
						"item_code": d.rm_item_code,
						"warehouse": self.supplier_warehouse,
						"posting_date": self.posting_date,
						"posting_time": self.posting_time,
						"qty": -1 * d.consumed_qty,
						"serial_no": d.serial_no
					})

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

			if self.doctype == "Purchase Order":
				for supplied_item in self.get("supplied_items"):
					if not supplied_item.reserve_warehouse:
						frappe.throw(_("Reserved Warehouse is mandatory for Item {0} in Raw Materials supplied").format(frappe.bold(supplied_item.rm_item_code)))

		else:
			for item in self.get("items"):
				if item.bom:
					item.bom = None

	def create_raw_materials_supplied(self, raw_material_table):
		if self.is_subcontracted=="Yes":
			parent_items = []
			backflush_raw_materials_based_on = frappe.db.get_single_value("Buying Settings",
				"backflush_raw_materials_of_subcontract_based_on")
			if (self.doctype == 'Purchase Receipt' and
				backflush_raw_materials_based_on != 'BOM'):
				self.update_raw_materials_supplied_based_on_stock_entries()
			else:
				for item in self.get("items"):
					if self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
						item.rm_supp_cost = 0.0
					if item.bom and item.item_code in self.sub_contracted_items:
						self.update_raw_materials_supplied_based_on_bom(item, raw_material_table)

						if [item.item_code, item.name] not in parent_items:
							parent_items.append([item.item_code, item.name])

				self.cleanup_raw_materials_supplied(parent_items, raw_material_table)

		elif self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			for item in self.get("items"):
				item.rm_supp_cost = 0.0

		if self.is_subcontracted == "No" and self.get("supplied_items"):
			self.set('supplied_items', [])

	def update_raw_materials_supplied_based_on_stock_entries(self):
		self.set('supplied_items', [])

		purchase_orders = set([d.purchase_order for d in self.items])

		# qty of raw materials backflushed (for each item per purchase order)
		backflushed_raw_materials_map = get_backflushed_subcontracted_raw_materials(purchase_orders)

		# qty of "finished good" item yet to be received
		qty_to_be_received_map = get_qty_to_be_received(purchase_orders)

		for item in self.get('items'):
			if not item.purchase_order:
				continue

			# reset raw_material cost
			item.rm_supp_cost = 0

			# qty of raw materials transferred to the supplier
			transferred_raw_materials = get_subcontracted_raw_materials_from_se(item.purchase_order, item.item_code)

			non_stock_items = get_non_stock_items(item.purchase_order, item.item_code)

			item_key = '{}{}'.format(item.item_code, item.purchase_order)

			fg_yet_to_be_received = qty_to_be_received_map.get(item_key)

			if not fg_yet_to_be_received:
				frappe.throw(_("Row #{0}: Item {1} is already fully received in Purchase Order {2}")
					.format(item.idx, frappe.bold(item.item_code),
						frappe.utils.get_link_to_form("Purchase Order", item.purchase_order)),
					title=_("Limit Crossed"))

			transferred_batch_qty_map = get_transferred_batch_qty_map(item.purchase_order, item.item_code)
			# backflushed_batch_qty_map = get_backflushed_batch_qty_map(item.purchase_order, item.item_code)

			for raw_material in transferred_raw_materials + non_stock_items:
				rm_item_key = (raw_material.rm_item_code, item.item_code, item.purchase_order)
				raw_material_data = backflushed_raw_materials_map.get(rm_item_key, {})

				consumed_qty = raw_material_data.get('qty', 0)
				consumed_serial_nos = raw_material_data.get('serial_no', '')
				consumed_batch_nos = raw_material_data.get('batch_nos', '')

				transferred_qty = raw_material.qty

				rm_qty_to_be_consumed = transferred_qty - consumed_qty

				# backflush all remaining transferred qty in the last Purchase Receipt
				if fg_yet_to_be_received == item.qty:
					qty = rm_qty_to_be_consumed
				else:
					qty = (rm_qty_to_be_consumed / fg_yet_to_be_received) * item.qty

					if frappe.get_cached_value('UOM', raw_material.stock_uom, 'must_be_whole_number'):
						qty = frappe.utils.ceil(qty)

				if qty > rm_qty_to_be_consumed:
					qty = rm_qty_to_be_consumed

				if not qty: continue

				if raw_material.serial_nos:
					set_serial_nos(raw_material, consumed_serial_nos, qty)

				if raw_material.batch_nos:
					backflushed_batch_qty_map = raw_material_data.get('consumed_batch', {})

					batches_qty = get_batches_with_qty(raw_material.rm_item_code, raw_material.main_item_code,
						qty, transferred_batch_qty_map, backflushed_batch_qty_map, item.purchase_order)
					for batch_data in batches_qty:
						qty = batch_data['qty']
						raw_material.batch_no = batch_data['batch']
						self.append_raw_material_to_be_backflushed(item, raw_material, qty)
				else:
					self.append_raw_material_to_be_backflushed(item, raw_material, qty)

	def append_raw_material_to_be_backflushed(self, fg_item_row, raw_material_data, qty):
		rm = self.append('supplied_items', {})
		rm.update(raw_material_data)

		if not rm.main_item_code:
			rm.main_item_code = fg_item_row.item_code

		rm.reference_name = fg_item_row.name
		rm.required_qty = qty
		rm.consumed_qty = qty

	def update_raw_materials_supplied_based_on_bom(self, item, raw_material_table):
		exploded_item = 1
		if hasattr(item, 'include_exploded_items'):
			exploded_item = item.get('include_exploded_items')

		bom_items = get_items_from_bom(item.item_code, item.bom, exploded_item)

		used_alternative_items = []
		if self.doctype in ["Purchase Receipt", "Purchase Invoice"] and item.purchase_order:
			used_alternative_items = get_used_alternative_items(purchase_order = item.purchase_order)

		raw_materials_cost = 0
		items = list(set([d.item_code for d in bom_items]))
		item_wh = frappe._dict(frappe.db.sql("""select i.item_code, id.default_warehouse
			from `tabItem` i, `tabItem Default` id
			where id.parent=i.name and id.company=%s and i.name in ({0})"""
			.format(", ".join(["%s"] * len(items))), [self.company] + items))

		for bom_item in bom_items:
			if self.doctype == "Purchase Order":
				reserve_warehouse = bom_item.source_warehouse or item_wh.get(bom_item.item_code)
				if frappe.db.get_value("Warehouse", reserve_warehouse, "company") != self.company:
					reserve_warehouse = None

			conversion_factor = item.conversion_factor
			if (self.doctype in ["Purchase Receipt", "Purchase Invoice"] and item.purchase_order and
				bom_item.item_code in used_alternative_items):
				alternative_item_data = used_alternative_items.get(bom_item.item_code)
				bom_item.item_code = alternative_item_data.item_code
				bom_item.item_name = alternative_item_data.item_name
				bom_item.stock_uom = alternative_item_data.stock_uom
				conversion_factor = alternative_item_data.conversion_factor
				bom_item.description = alternative_item_data.description

			# check if exists
			exists = 0
			for d in self.get(raw_material_table):
				if d.main_item_code == item.item_code and d.rm_item_code == bom_item.item_code \
					and d.reference_name == item.name:
						rm, exists = d, 1
						break

			if not exists:
				rm = self.append(raw_material_table, {})

			required_qty = flt(flt(bom_item.qty_consumed_per_unit) * (flt(item.qty) + getattr(item, 'rejected_qty', 0)) *
				flt(conversion_factor), rm.precision("required_qty"))
			rm.reference_name = item.name
			rm.bom_detail_no = bom_item.name
			rm.main_item_code = item.item_code
			rm.rm_item_code = bom_item.item_code
			rm.stock_uom = bom_item.stock_uom
			rm.required_qty = required_qty
			rm.rate = bom_item.rate
			rm.conversion_factor = conversion_factor

			if self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
				rm.consumed_qty = required_qty
				rm.description = bom_item.description
				if item.batch_no and frappe.db.get_value("Item", rm.rm_item_code, "has_batch_no") and not rm.batch_no:
					rm.batch_no = item.batch_no
			elif not rm.reserve_warehouse:
				rm.reserve_warehouse = reserve_warehouse

	def cleanup_raw_materials_supplied(self, parent_items, raw_material_table):
		"""Remove all those child items which are no longer present in main item table"""
		delete_list = []
		for d in self.get(raw_material_table):
			if [d.main_item_code, d.reference_name] not in parent_items:
				# mark for deletion from doclist
				delete_list.append(d)

		# delete from doclist
		if delete_list:
			rm_supplied_details = self.get(raw_material_table)
			self.set(raw_material_table, [])
			for d in rm_supplied_details:
				if d not in delete_list:
					self.append(raw_material_table, d)

	@property
	def sub_contracted_items(self):
		if not hasattr(self, "_sub_contracted_items"):
			self._sub_contracted_items = []
			item_codes = list(set(item.item_code for item in
				self.get("items")))
			if item_codes:
				items = frappe.get_all('Item', filters={
					'name': ['in', item_codes],
					'is_sub_contracted_item': 1
				})
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

				if self.doctype=="Purchase Receipt" and d.meta.get_field("received_stock_qty"):
					# Set Received Qty in Stock UOM
					d.received_stock_qty = flt(d.received_qty) * flt(d.conversion_factor, d.precision("conversion_factor"))

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
					frappe.throw(_("Row #{0}: Rejected Warehouse is mandatory against rejected Item {1}").format(d.idx, d.item_code))

	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in self.get("items"):
			self.validate_negative_quantity(d, ["received_qty","qty", "rejected_qty"])
			if not flt(d.received_qty) and flt(d.qty):
				d.received_qty = flt(d.qty) - flt(d.rejected_qty)

			elif not flt(d.qty) and flt(d.rejected_qty):
				d.qty = flt(d.received_qty) - flt(d.rejected_qty)

			elif not flt(d.rejected_qty):
				d.rejected_qty = flt(d.received_qty) -  flt(d.qty)

			val  = flt(d.qty) + flt(d.rejected_qty)
			# Check Received Qty = Accepted Qty + Rejected Qty
			if (flt(val, d.precision("received_qty")) != flt(d.received_qty, d.precision("received_qty"))):
				frappe.throw(_("Accepted + Rejected Qty must be equal to Received quantity for Item {0}").format(d.item_code))

	def validate_negative_quantity(self, item_row, field_list):
		if self.is_return:
			return

		item_row = item_row.as_dict()
		for fieldname in field_list:
			if flt(item_row[fieldname]) < 0:
				frappe.throw(_("Row #{0}: {1} can not be negative for item {2}").format(item_row['idx'],
					frappe.get_meta(item_row.doctype).get_label(fieldname), item_row['item_code']))

	def check_for_on_hold_or_closed_status(self, ref_doctype, ref_fieldname):
		for d in self.get("items"):
			if d.get(ref_fieldname):
				status = frappe.db.get_value(ref_doctype, d.get(ref_fieldname), "status")
				if status in ("Closed", "On Hold"):
					frappe.throw(_("{0} {1} is {2}").format(ref_doctype,d.get(ref_fieldname), status))

	def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
		self.update_ordered_and_reserved_qty()

		sl_entries = []
		stock_items = self.get_stock_items()

		for d in self.get('items'):
			if d.item_code in stock_items and d.warehouse:
				pr_qty = flt(d.qty) * flt(d.conversion_factor)

				if pr_qty:

					if d.from_warehouse and ((not cint(self.is_return) and self.docstatus==1)
						or (cint(self.is_return) and self.docstatus==2)):
						from_warehouse_sle = self.get_sl_entries(d, {
							"actual_qty": -1 * pr_qty,
							"warehouse": d.from_warehouse,
							"outgoing_rate": d.rate,
							"recalculate_rate": 1,
							"dependant_sle_voucher_detail_no": d.name
						})

						sl_entries.append(from_warehouse_sle)

					sle = self.get_sl_entries(d, {
						"actual_qty": flt(pr_qty),
						"serial_no": cstr(d.serial_no).strip()
					})
					if self.is_return:
						outgoing_rate = get_rate_for_return(self.doctype, self.name, d.item_code, self.return_against, item_row=d)

						sle.update({
							"outgoing_rate": outgoing_rate,
							"recalculate_rate": 1
						})
						if d.from_warehouse:
							sle.dependant_sle_voucher_detail_no = d.name
					else:
						val_rate_db_precision = 6 if cint(self.precision("valuation_rate", d)) <= 6 else 9
						incoming_rate = flt(d.valuation_rate, val_rate_db_precision)
						sle.update({
							"incoming_rate": incoming_rate,
							"recalculate_rate": 1 if (self.is_subcontracted and d.bom) or d.from_warehouse else 0
						})
					sl_entries.append(sle)

					if d.from_warehouse and ((not cint(self.is_return) and self.docstatus==2)
						or (cint(self.is_return) and self.docstatus==1)):
						from_warehouse_sle = self.get_sl_entries(d, {
							"actual_qty": -1 * pr_qty,
							"warehouse": d.from_warehouse,
							"recalculate_rate": 1
						})

						sl_entries.append(from_warehouse_sle)

				if flt(d.rejected_qty) != 0:
					sl_entries.append(self.get_sl_entries(d, {
						"warehouse": d.rejected_warehouse,
						"actual_qty": flt(d.rejected_qty) * flt(d.conversion_factor),
						"serial_no": cstr(d.rejected_serial_no).strip(),
						"incoming_rate": 0.0
					}))

		self.make_sl_entries_for_supplier_warehouse(sl_entries)
		self.make_sl_entries(sl_entries, allow_negative_stock=allow_negative_stock,
			via_landed_cost_voucher=via_landed_cost_voucher)

	def update_ordered_and_reserved_qty(self):
		po_map = {}
		for d in self.get("items"):
			if self.doctype=="Purchase Receipt" \
				and d.purchase_order:
					po_map.setdefault(d.purchase_order, []).append(d.purchase_order_item)

			elif self.doctype=="Purchase Invoice" and d.purchase_order and d.po_detail:
				po_map.setdefault(d.purchase_order, []).append(d.po_detail)

		for po, po_item_rows in po_map.items():
			if po and po_item_rows:
				po_obj = frappe.get_doc("Purchase Order", po)

				if po_obj.status in ["Closed", "Cancelled"]:
					frappe.throw(_("{0} {1} is cancelled or closed").format(_("Purchase Order"), po),
						frappe.InvalidStatusError)

				po_obj.update_ordered_qty(po_item_rows)
				if self.is_subcontracted:
					po_obj.update_reserved_qty_for_subcontract()

	def make_sl_entries_for_supplier_warehouse(self, sl_entries):
		if hasattr(self, 'supplied_items'):
			for d in self.get('supplied_items'):
				# negative quantity is passed, as raw material qty has to be decreased
				# when PR is submitted and it has to be increased when PR is cancelled
				sl_entries.append(self.get_sl_entries(d, {
					"item_code": d.rm_item_code,
					"warehouse": self.supplier_warehouse,
					"actual_qty": -1*flt(d.consumed_qty),
					"dependant_sle_voucher_detail_no": d.reference_name
				}))

	def on_submit(self):
		if self.get('is_return'):
			return

		if self.doctype in ['Purchase Receipt', 'Purchase Invoice']:
			field = 'purchase_invoice' if self.doctype == 'Purchase Invoice' else 'purchase_receipt'

			self.process_fixed_asset()
			self.update_fixed_asset(field)

		update_last_purchase_rate(self, is_submit = 1)

	def on_cancel(self):
		super(BuyingController, self).on_cancel()

		if self.get('is_return'):
			return

		update_last_purchase_rate(self, is_submit = 0)
		if self.doctype in ['Purchase Receipt', 'Purchase Invoice']:
			field = 'purchase_invoice' if self.doctype == 'Purchase Invoice' else 'purchase_receipt'

			self.delete_linked_asset()
			self.update_fixed_asset(field, delete_asset=True)

	def validate_budget(self):
		if self.docstatus == 1:
			for data in self.get('items'):
				args = data.as_dict()
				args.update({
					'doctype': self.doctype,
					'company': self.company,
					'posting_date': (self.schedule_date
						if self.doctype == 'Material Request' else self.transaction_date)
				})

				validate_expense_against_budget(args)

	def process_fixed_asset(self):
		if self.doctype == 'Purchase Invoice' and not self.update_stock:
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

				if item_data.get('auto_create_assets'):
					# If asset has to be auto created
					# Check for asset naming series
					if item_data.get('asset_naming_series'):
						created_assets = []

						for qty in range(cint(d.qty)):
							asset = self.make_asset(d)
							created_assets.append(asset)

						if len(created_assets) > 5:
							# dont show asset form links if more than 5 assets are created
							messages.append(_('{} Assets created for {}').format(len(created_assets), frappe.bold(d.item_code)))
						else:
							assets_link = list(map(lambda d: frappe.utils.get_link_to_form('Asset', d), created_assets))
							assets_link = frappe.bold(','.join(assets_link))

							is_plural = 's' if len(created_assets) != 1 else ''
							messages.append(
								_('Asset{} {assets_link} created for {}').format(is_plural, frappe.bold(d.item_code), assets_link=assets_link)
							)
					else:
						frappe.throw(_("Row {}: Asset Naming Series is mandatory for the auto creation for item {}")
							.format(d.idx, frappe.bold(d.item_code)))
				else:
					messages.append(_("Assets not created for {0}. You will have to create asset manually.")
						.format(frappe.bold(d.item_code)))

		for message in messages:
			frappe.msgprint(message, title="Success", indicator="green")

	def make_asset(self, row):
		if not row.asset_location:
			frappe.throw(_("Row {0}: Enter location for the asset item {1}").format(row.idx, row.item_code))

		item_data = frappe.db.get_value('Item',
			row.item_code, ['asset_naming_series', 'asset_category'], as_dict=1)

		purchase_amount = flt(row.base_rate + row.item_tax_amount)
		asset = frappe.get_doc({
			'doctype': 'Asset',
			'item_code': row.item_code,
			'asset_name': row.item_name,
			'naming_series': item_data.get('asset_naming_series') or 'AST',
			'asset_category': item_data.get('asset_category'),
			'location': row.asset_location,
			'company': self.company,
			'supplier': self.supplier,
			'purchase_date': self.posting_date,
			'calculate_depreciation': 1,
			'purchase_receipt_amount': purchase_amount,
			'gross_purchase_amount': purchase_amount,
			'purchase_receipt': self.name if self.doctype == 'Purchase Receipt' else None,
			'purchase_invoice': self.name if self.doctype == 'Purchase Invoice' else None
		})

		asset.flags.ignore_validate = True
		asset.flags.ignore_mandatory = True
		asset.set_missing_values()
		asset.insert()

		return asset.name

	def update_fixed_asset(self, field, delete_asset = False):
		for d in self.get("items"):
			if d.is_fixed_asset:
				is_auto_create_enabled = frappe.db.get_value('Item', d.item_code, 'auto_create_assets')
				assets = frappe.db.get_all('Asset', filters={ field : self.name, 'item_code' : d.item_code })

				for asset in assets:
					asset = frappe.get_doc('Asset', asset.name)
					if delete_asset and is_auto_create_enabled:
						# need to delete movements to delete assets otherwise throws link exists error
						movements = frappe.db.sql(
							"""SELECT asm.name
							FROM `tabAsset Movement` asm, `tabAsset Movement Item` asm_item
							WHERE asm_item.parent=asm.name and asm_item.asset=%s""", asset.name, as_dict=1)
						for movement in movements:
							frappe.delete_doc('Asset Movement', movement.name, force=1)
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
							frappe.throw(_('Cannot cancel this document as it is linked with submitted asset {0}. Please cancel it to continue.')
								.format(frappe.utils.get_link_to_form('Asset', asset.name)))

					asset.flags.ignore_validate_update_after_submit = True
					asset.flags.ignore_mandatory = True
					if asset.docstatus == 0:
						asset.flags.ignore_validate = True

					asset.save()

	def delete_linked_asset(self):
		if self.doctype == 'Purchase Invoice' and not self.get('update_stock'):
			return

		frappe.db.sql("delete from `tabAsset Movement` where reference_name=%s", self.name)

	def validate_schedule_date(self):
		if not self.get("items"):
			return

		earliest_schedule_date = min([d.schedule_date for d in self.get("items")])
		if earliest_schedule_date:
			self.schedule_date = earliest_schedule_date

		if self.schedule_date:
			for d in self.get('items'):
				if not d.schedule_date:
					d.schedule_date = self.schedule_date

				if (d.schedule_date and self.transaction_date and
					getdate(d.schedule_date) < getdate(self.transaction_date)):
					frappe.throw(_("Row #{0}: Reqd by Date cannot be before Transaction Date").format(d.idx))
		else:
			frappe.throw(_("Please enter Reqd by Date"))

	def validate_items(self):
		# validate items to see if they have is_purchase_item or is_subcontracted_item enabled
		if self.doctype=="Material Request": return

		if hasattr(self, "is_subcontracted") and self.is_subcontracted == 'Yes':
			validate_item_type(self, "is_sub_contracted_item", "subcontracted")
		else:
			validate_item_type(self, "is_purchase_item", "purchase")


def get_items_from_bom(item_code, bom, exploded_item=1):
	doctype = "BOM Item" if not exploded_item else "BOM Explosion Item"

	bom_items = frappe.db.sql("""select t2.item_code, t2.name,
			t2.rate, t2.stock_uom, t2.source_warehouse, t2.description,
			t2.stock_qty / ifnull(t1.quantity, 1) as qty_consumed_per_unit
		from
			`tabBOM` t1, `tab{0}` t2, tabItem t3
		where
			t2.parent = t1.name and t1.item = %s
			and t1.docstatus = 1 and t1.is_active = 1 and t1.name = %s
			and t2.sourced_by_supplier = 0
			and t2.item_code = t3.name""".format(doctype),
			(item_code, bom), as_dict=1)

	if not bom_items:
		msgprint(_("Specified BOM {0} does not exist for Item {1}").format(bom, item_code), raise_exception=1)

	return bom_items

def get_subcontracted_raw_materials_from_se(purchase_order, fg_item):
	common_query = """
		SELECT
			sed.item_code AS rm_item_code,
			SUM(sed.qty) AS qty,
			sed.description,
			sed.stock_uom,
			sed.subcontracted_item AS main_item_code,
			{serial_no_concat_syntax} AS serial_nos,
			{batch_no_concat_syntax} AS batch_nos
		FROM `tabStock Entry` se,`tabStock Entry Detail` sed
		WHERE
			se.name = sed.parent
			AND se.docstatus=1
			AND se.purpose='Send to Subcontractor'
			AND se.purchase_order = %s
			AND IFNULL(sed.t_warehouse, '') != ''
			AND IFNULL(sed.subcontracted_item, '') in ('', %s)
		GROUP BY sed.item_code, sed.subcontracted_item
	"""
	raw_materials = frappe.db.multisql({
		'mariadb': common_query.format(
			serial_no_concat_syntax="GROUP_CONCAT(sed.serial_no)",
			batch_no_concat_syntax="GROUP_CONCAT(sed.batch_no)"
		),
		'postgres': common_query.format(
			serial_no_concat_syntax="STRING_AGG(sed.serial_no, ',')",
			batch_no_concat_syntax="STRING_AGG(sed.batch_no, ',')"
		)
	}, (purchase_order, fg_item), as_dict=1)

	return raw_materials

def get_backflushed_subcontracted_raw_materials(purchase_orders):
	purchase_receipts = frappe.get_all("Purchase Receipt Item",
		fields = ["purchase_order", "item_code", "name", "parent"],
		filters={"docstatus": 1, "purchase_order": ("in", list(purchase_orders))})

	distinct_purchase_receipts = {}
	for pr in purchase_receipts:
		key = (pr.purchase_order, pr.item_code, pr.parent)
		distinct_purchase_receipts.setdefault(key, []).append(pr.name)

	backflushed_raw_materials_map = frappe._dict()
	for args, references in iteritems(distinct_purchase_receipts):
		purchase_receipt_supplied_items = get_supplied_items(args[1], args[2], references)

		for data in purchase_receipt_supplied_items:
			pr_key = (data.rm_item_code, data.main_item_code, args[0])
			if pr_key not in backflushed_raw_materials_map:
				backflushed_raw_materials_map.setdefault(pr_key, frappe._dict({
					"qty": 0.0,
					"serial_no": [],
					"batch_no": [],
					"consumed_batch": {}
				}))

			row = backflushed_raw_materials_map.get(pr_key)
			row.qty += data.consumed_qty

			for field in ["serial_no", "batch_no"]:
				if data.get(field):
					row[field].append(data.get(field))

			if data.get("batch_no"):
				if data.get("batch_no") in row.consumed_batch:
					row.consumed_batch[data.get("batch_no")] += data.consumed_qty
				else:
					row.consumed_batch[data.get("batch_no")] = data.consumed_qty

	return backflushed_raw_materials_map

def get_supplied_items(item_code, purchase_receipt, references):
	return frappe.get_all("Purchase Receipt Item Supplied",
		fields=["rm_item_code", "main_item_code", "consumed_qty", "serial_no", "batch_no"],
		filters={"main_item_code": item_code, "parent": purchase_receipt, "reference_name": ("in", references)})

def get_asset_item_details(asset_items):
	asset_items_data = {}
	for d in frappe.get_all('Item', fields = ["name", "auto_create_assets", "asset_naming_series"],
		filters = {'name': ('in', asset_items)}):
		asset_items_data.setdefault(d.name, d)

	return asset_items_data

def validate_item_type(doc, fieldname, message):
	# iterate through items and check if they are valid sales or purchase items
	items = [d.item_code for d in doc.items if d.item_code]

	# No validation check inase of creating transaction using 'Opening Invoice Creation Tool'
	if not items:
		return

	item_list = ", ".join(["%s" % frappe.db.escape(d) for d in items])

	invalid_items = [d[0] for d in frappe.db.sql("""
		select item_code from tabItem where name in ({0}) and {1}=0
		""".format(item_list, fieldname), as_list=True)]

	if invalid_items:
		items = ", ".join([d for d in invalid_items])

		if len(invalid_items) > 1:
			error_message = _("Following items {0} are not marked as {1} item. You can enable them as {1} item from its Item master").format(items, message)
		else:
			error_message = _("Following item {0} is not marked as {1} item. You can enable them as {1} item from its Item master").format(items, message)

		frappe.throw(error_message)

def get_qty_to_be_received(purchase_orders):
	return frappe._dict(frappe.db.sql("""
		SELECT CONCAT(poi.`item_code`, poi.`parent`) AS item_key,
		SUM(poi.`qty`) - SUM(poi.`received_qty`) AS qty_to_be_received
		FROM `tabPurchase Order Item` poi
		WHERE
			poi.`parent` in %s
		GROUP BY poi.`item_code`, poi.`parent`
		HAVING SUM(poi.`qty`) > SUM(poi.`received_qty`)
	""", (purchase_orders)))

def get_non_stock_items(purchase_order, fg_item_code):
	return frappe.db.sql("""
		SELECT
			pois.main_item_code,
			pois.rm_item_code,
			item.description,
			pois.required_qty AS qty,
			pois.rate,
			1 as non_stock_item,
			pois.stock_uom
		FROM `tabPurchase Order Item Supplied` pois, `tabItem` item
		WHERE
			pois.`rm_item_code` = item.`name`
			AND item.is_stock_item = 0
			AND pois.`parent` = %s
			AND pois.`main_item_code` = %s
	""", (purchase_order, fg_item_code), as_dict=1)


def set_serial_nos(raw_material, consumed_serial_nos, qty):
	serial_nos = set(get_serial_nos(raw_material.serial_nos)) - \
		set(get_serial_nos(consumed_serial_nos))
	if serial_nos and qty <= len(serial_nos):
		raw_material.serial_no = '\n'.join(list(serial_nos)[0:frappe.utils.cint(qty)])

def get_transferred_batch_qty_map(purchase_order, fg_item):
	# returns
	# {
	# 	(item_code, fg_code): {
	# 		batch1: 10, # qty
	# 		batch2: 16
	# 	},
	# }
	transferred_batch_qty_map = {}
	transferred_batches = frappe.db.sql("""
		SELECT
			sed.batch_no,
			SUM(sed.qty) AS qty,
			sed.item_code,
			sed.subcontracted_item
		FROM `tabStock Entry` se,`tabStock Entry Detail` sed
		WHERE
			se.name = sed.parent
			AND se.docstatus=1
			AND se.purpose='Send to Subcontractor'
			AND se.purchase_order = %s
			AND ifnull(sed.subcontracted_item, '') in ('', %s)
			AND sed.batch_no IS NOT NULL
		GROUP BY
			sed.batch_no,
			sed.item_code
	""", (purchase_order, fg_item), as_dict=1)

	for batch_data in transferred_batches:
		key = ((batch_data.item_code, fg_item)
			if batch_data.subcontracted_item else (batch_data.item_code, purchase_order))
		transferred_batch_qty_map.setdefault(key, {})
		transferred_batch_qty_map[key][batch_data.batch_no] = batch_data.qty

	return transferred_batch_qty_map

def get_backflushed_batch_qty_map(purchase_order, fg_item):
	# returns
	# {
	# 	(item_code, fg_code): {
	# 		batch1: 10, # qty
	# 		batch2: 16
	# 	},
	# }
	backflushed_batch_qty_map = {}
	backflushed_batches = frappe.db.sql("""
		SELECT
			pris.batch_no,
			SUM(pris.consumed_qty) AS qty,
			pris.rm_item_code AS item_code
		FROM `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pri, `tabPurchase Receipt Item Supplied` pris
		WHERE
			pr.name = pri.parent
			AND pri.parent = pris.parent
			AND pri.purchase_order = %s
			AND pri.item_code = pris.main_item_code
			AND pr.docstatus = 1
			AND pris.main_item_code = %s
			AND pris.batch_no IS NOT NULL
		GROUP BY
			pris.rm_item_code, pris.batch_no
	""", (purchase_order, fg_item), as_dict=1)

	for batch_data in backflushed_batches:
		backflushed_batch_qty_map.setdefault((batch_data.item_code, fg_item), {})
		backflushed_batch_qty_map[(batch_data.item_code, fg_item)][batch_data.batch_no] = batch_data.qty

	return backflushed_batch_qty_map

def get_batches_with_qty(item_code, fg_item, required_qty, transferred_batch_qty_map, backflushed_batches, po):
	# Returns available batches to be backflushed based on requirements
	transferred_batches = transferred_batch_qty_map.get((item_code, fg_item), {})
	if not transferred_batches:
		transferred_batches = transferred_batch_qty_map.get((item_code, po), {})

	available_batches = []

	for (batch, transferred_qty) in transferred_batches.items():
		backflushed_qty = backflushed_batches.get(batch, 0)
		available_qty = transferred_qty - backflushed_qty

		if available_qty >= required_qty:
			available_batches.append({'batch': batch, 'qty': required_qty})
			break
		else:
			available_batches.append({'batch': batch, 'qty': available_qty})
			required_qty -= available_qty

	return available_batches
