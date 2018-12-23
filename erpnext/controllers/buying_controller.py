# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt,cint, cstr, getdate

from erpnext.accounting.party import get_party_details
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.buying.utils import validate_for_items, update_last_purchase_rate
from erpnext.stock.stock_ledger import get_valuation_rate
from erpnext.stock.doctype.stock_entry.stock_entry import get_used_alternative_items
from erpnext.stock.doctype.serial_no.serial_no import get_auto_serial_nos, auto_make_serial_nos, get_serial_nos
from frappe.contacts.doctype.address.address import get_address_display

from erpnext.accounting.doctype.budget.budget import validate_expense_against_budget
from erpnext.controllers.stock_controller import StockController

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
		self.set_supplier_address()

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
			self.update_valuation_rate("items")

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
			tax_for_valuation = [d for d in self.get("taxes")
				if d.category in ["Valuation", "Valuation and Total"]]

			if tax_for_valuation:
				for d in tax_for_valuation:
					d.category = 'Total'
				msgprint(_('Tax Category has been changed to "Total" because all the Items are non-stock items'))

	def get_asset_items(self):
		if self.doctype not in ['Purchase Invoice', 'Purchase Receipt']:
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
	def update_valuation_rate(self, parentfield):
		"""
			item_tax_amount is the total tax amount applied on that item
			stored for valuation

			TODO: rename item_tax_amount to valuation_tax_amount
		"""
		stock_items = self.get_stock_items() + self.get_asset_items()

		stock_items_qty, stock_items_amount = 0, 0
		last_stock_item_idx = 1
		for d in self.get(parentfield):
			if d.item_code and d.item_code in stock_items:
				stock_items_qty += flt(d.qty)
				stock_items_amount += flt(d.base_net_amount)
				last_stock_item_idx = d.idx

		total_valuation_amount = sum([flt(d.base_tax_amount_after_discount_amount) for d in self.get("taxes")
			if d.category in ["Valuation", "Valuation and Total"]])

		valuation_amount_adjustment = total_valuation_amount
		for i, item in enumerate(self.get(parentfield)):
			if item.item_code and item.qty and item.item_code in stock_items:
				item_proportion = flt(item.base_net_amount) / stock_items_amount if stock_items_amount \
					else flt(item.qty) / stock_items_qty
				if i == (last_stock_item_idx - 1):
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
				rm_supp_cost = flt(item.rm_supp_cost) if self.doctype in ["Purchase Receipt", "Purchase Invoice"] else 0.0

				landed_cost_voucher_amount = flt(item.landed_cost_voucher_amount) \
					if self.doctype in ["Purchase Receipt", "Purchase Invoice"] else 0.0

				item.valuation_rate = ((item.base_net_amount + item.item_tax_amount + rm_supp_cost
					 + landed_cost_voucher_amount) / qty_in_stock_uom)
			else:
				item.valuation_rate = 0.0

	def validate_for_subcontracting(self):
		if not self.is_subcontracted and self.sub_contracted_items:
			frappe.throw(_("Please enter 'Is Subcontracted' as Yes or No"))

		if self.is_subcontracted == "Yes":
			if self.doctype in ["Purchase Receipt", "Purchase Invoice"] and not self.supplier_warehouse:
				frappe.throw(_("Supplier Warehouse mandatory for sub-contracted Purchase Receipt"))

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
				self.update_raw_materials_supplied_based_on_stock_entries(raw_material_table)
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

	def update_raw_materials_supplied_based_on_stock_entries(self, raw_material_table):
		self.set(raw_material_table, [])
		purchase_orders = [d.purchase_order for d in self.items]
		if purchase_orders:
			items = get_subcontracted_raw_materials_from_se(purchase_orders)
			backflushed_raw_materials = get_backflushed_subcontracted_raw_materials_from_se(purchase_orders, self.name)

			for d in items:
				qty = d.qty - backflushed_raw_materials.get(d.item_code, 0)
				rm = self.append(raw_material_table, {})
				rm.rm_item_code = d.item_code
				rm.item_name = d.item_name
				rm.main_item_code = d.main_item_code
				rm.description = d.description
				rm.stock_uom = d.stock_uom
				rm.required_qty = qty
				rm.consumed_qty = qty
				rm.serial_no = d.serial_no
				rm.batch_no = d.batch_no

				# get raw materials rate
				from erpnext.stock.utils import get_incoming_rate
				rm.rate = get_incoming_rate({
					"item_code": d.item_code,
					"warehouse": self.supplier_warehouse,
					"posting_date": self.posting_date,
					"posting_time": self.posting_time,
					"qty": -1 * qty,
					"serial_no": rm.serial_no
				})
				if not rm.rate:
					rm.rate = get_valuation_rate(d.item_code, self.supplier_warehouse,
						self.doctype, self.name, currency=self.company_currency, company = self.company)

				rm.amount = qty * flt(rm.rate)

	def update_raw_materials_supplied_based_on_bom(self, item, raw_material_table):
		exploded_item = 1
		if hasattr(item, 'include_exploded_items'):
			exploded_item = item.get('include_exploded_items')

		bom_items = get_items_from_bom(item.item_code, item.bom, exploded_item)

		used_alternative_items = []
		if self.doctype == 'Purchase Receipt' and item.purchase_order:
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
			if (self.doctype == 'Purchase Receipt' and item.purchase_order and
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
			if self.doctype == "Purchase Order" and not rm.reserve_warehouse:
				rm.reserve_warehouse = reserve_warehouse

			rm.conversion_factor = conversion_factor

			if self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
				rm.consumed_qty = required_qty
				rm.description = bom_item.description
				if item.batch_no and not rm.batch_no:
					rm.batch_no = item.batch_no

			# get raw materials rate
			if self.doctype == "Purchase Receipt":
				from erpnext.stock.utils import get_incoming_rate
				rm.rate = get_incoming_rate({
					"item_code": bom_item.item_code,
					"warehouse": self.supplier_warehouse,
					"posting_date": self.posting_date,
					"posting_time": self.posting_time,
					"qty": -1 * required_qty,
					"serial_no": rm.serial_no
				})
				if not rm.rate:
					rm.rate = get_valuation_rate(bom_item.item_code, self.supplier_warehouse,
						self.doctype, self.name, currency=self.company_currency, company = self.company)
			else:
				rm.rate = bom_item.rate

			rm.amount = required_qty * flt(rm.rate)
			raw_materials_cost += flt(rm.amount)

		if self.doctype in ("Purchase Receipt", "Purchase Invoice"):
			item.rm_supp_cost = raw_materials_cost

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
				self._sub_contracted_items = [r[0] for r in frappe.db.sql("""select name
					from `tabItem` where name in (%s) and is_sub_contracted_item=1""" % \
					(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return self._sub_contracted_items

	def set_qty_as_per_stock_uom(self):
		for d in self.get("items"):
			if d.meta.get_field("stock_qty"):
				if not d.conversion_factor:
					frappe.throw(_("Row {0}: Conversion Factor is mandatory").format(d.idx))
				d.stock_qty = flt(d.qty) * flt(d.conversion_factor)

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

			# Check Received Qty = Accepted Qty + Rejected Qty
			if ((flt(d.qty) + flt(d.rejected_qty)) != flt(d.received_qty)):
				frappe.throw(_("Accepted + Rejected Qty must be equal to Received quantity for Item {0}").format(d.item_code))

	def validate_negative_quantity(self, item_row, field_list):
		if self.is_return:
			return

		item_row = item_row.as_dict()
		for fieldname in field_list:
			if flt(item_row[fieldname]) < 0:
				frappe.throw(_("Row #{0}: {1} can not be negative for item {2}".format(item_row['idx'],
					frappe.get_meta(item_row.doctype).get_label(fieldname), item_row['item_code'])))

	def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
		self.update_ordered_and_reserved_qty()

		sl_entries = []
		stock_items = self.get_stock_items()

		for d in self.get('items'):
			if d.item_code in stock_items and d.warehouse:
				pr_qty = flt(d.qty) * flt(d.conversion_factor)

				if pr_qty:
					sle = self.get_sl_entries(d, {
						"actual_qty": flt(pr_qty),
						"serial_no": cstr(d.serial_no).strip()
					})
					if self.is_return:
						original_incoming_rate = frappe.db.get_value("Stock Ledger Entry",
							{"voucher_type": "Purchase Receipt", "voucher_no": self.return_against,
							"item_code": d.item_code}, "incoming_rate")

						sle.update({
							"outgoing_rate": original_incoming_rate
						})
					else:
						val_rate_db_precision = 6 if cint(self.precision("valuation_rate", d)) <= 6 else 9
						incoming_rate = flt(d.valuation_rate, val_rate_db_precision)
						sle.update({
							"incoming_rate": incoming_rate
						})
					sl_entries.append(sle)

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
			self.make_serial_nos_for_asset(asset_items)

	def make_serial_nos_for_asset(self, asset_items):
		items_data = get_asset_item_details(asset_items)

		for d in self.items:
			if d.is_fixed_asset:
				item_data = items_data.get(d.item_code)
				if not d.asset:
					asset = self.make_asset(d)
					d.db_set('asset', asset)

				if item_data.get('has_serial_no'):
					# If item has serial no
					if item_data.get('serial_no_series') and not d.serial_no:
						serial_nos = get_auto_serial_nos(item_data.get('serial_no_series'), d.qty)
					elif d.serial_no:
						serial_nos = d.serial_no
					elif not d.serial_no:
						frappe.throw(_("Serial no is mandatory for the item {0}").format(d.item_code))

					auto_make_serial_nos({
						'serial_no': serial_nos,
						'item_code': d.item_code,
						'via_stock_ledger': False,
						'company': self.company,
						'actual_qty': d.qty,
						'purchase_document_type': self.doctype,
						'purchase_document_no': self.name,
						'asset': d.asset,
						'location': d.asset_location
					})
					d.db_set('serial_no', serial_nos)

				if d.asset:
					self.make_asset_movement(d)

	def make_asset(self, row):
		if not row.asset_location:
			frappe.throw(_("Row {0}: Enter location for the asset item {1}").format(row.idx, row.item_code))

		item_data = frappe.db.get_value('Item',
			row.item_code, ['asset_naming_series', 'asset_category'], as_dict=1)

		purchase_amount = flt(row.base_net_amount + row.item_tax_amount)
		asset = frappe.get_doc({
			'doctype': 'Asset',
			'item_code': row.item_code,
			'asset_name': row.item_name,
			'naming_series': item_data.get('asset_naming_series') or 'AST',
			'asset_category': item_data.get('asset_category'),
			'location': row.asset_location,
			'company': self.company,
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

		frappe.msgprint(_("Asset {0} created").format(asset.name))
		return asset.name

	def make_asset_movement(self, row):
		asset_movement = frappe.get_doc({
			'doctype': 'Asset Movement',
			'asset': row.asset,
			'target_location': row.asset_location,
			'purpose': 'Receipt',
			'serial_no': row.serial_no,
			'quantity': len(get_serial_nos(row.serial_no)),
			'company': self.company,
			'transaction_date': self.posting_date,
			'reference_doctype': self.doctype,
			'reference_name': self.name
		}).insert()

		return asset_movement.name

	def update_fixed_asset(self, field, delete_asset = False):
		for d in self.get("items"):
			if d.is_fixed_asset and d.asset:
				asset = frappe.get_doc("Asset", d.asset)

				if delete_asset and asset.docstatus == 0:
					frappe.delete_doc("Asset", asset.name)
					d.db_set('asset', None)
					continue

				if self.docstatus in [0, 1] and not asset.get(field):
					asset.set(field, self.name)
					asset.purchase_date = self.posting_date
					asset.supplier = self.supplier
				elif self.docstatus == 2:
					asset.set(field, None)
					asset.supplier = None

				asset.flags.ignore_validate_update_after_submit = True
				asset.flags.ignore_mandatory = True
				if asset.docstatus == 0:
					asset.flags.ignore_validate = True

				asset.save()

	def delete_linked_asset(self):
		if self.doctype == 'Purchase Invoice' and not self.get('update_stock'):
			return

		frappe.db.sql("delete from `tabAsset Movement` where reference_name=%s", self.name)
		frappe.db.sql("delete from `tabSerial No` where purchase_document_no=%s", self.name)

	def validate_schedule_date(self):
		if not self.schedule_date:
			self.schedule_date = min([d.schedule_date for d in self.get("items")])

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
			and t2.item_code = t3.name and t3.is_stock_item = 1""".format(doctype),
			(item_code, bom), as_dict=1)

	if not bom_items:
		msgprint(_("Specified BOM {0} does not exist for Item {1}").format(bom, item_code), raise_exception=1)

	return bom_items

def get_subcontracted_raw_materials_from_se(purchase_orders):
	return frappe.db.sql("""
		select
			sed.item_name, sed.item_code, sum(sed.qty) as qty, sed.description,
			sed.stock_uom, sed.subcontracted_item as main_item_code, sed.serial_no, sed.batch_no
		from `tabStock Entry` se,`tabStock Entry Detail` sed
		where
			se.name = sed.parent and se.docstatus=1 and se.purpose='Subcontract'
			and se.purchase_order in (%s) and ifnull(sed.t_warehouse, '') != ''
		group by sed.item_code, sed.t_warehouse
	""" % (','.join(['%s'] * len(purchase_orders))), tuple(purchase_orders), as_dict=1)

def get_backflushed_subcontracted_raw_materials_from_se(purchase_orders, purchase_receipt):
	return frappe._dict(frappe.db.sql("""
		select
			prsi.rm_item_code as item_code, sum(prsi.consumed_qty) as qty
		from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pri, `tabPurchase Receipt Item Supplied` prsi
		where
			pr.name = pri.parent and pr.name = prsi.parent and pri.purchase_order in (%s)
			and pri.item_code = prsi.main_item_code and pr.name != '%s' and pr.docstatus = 1
		group by prsi.rm_item_code
	""" % (','.join(['%s'] * len(purchase_orders)), purchase_receipt), tuple(purchase_orders)))

def get_asset_item_details(asset_items):
	asset_items_data = {}
	for d in frappe.get_all('Item', fields = ["name", "has_serial_no", "serial_no_series"],
		filters = {'name': ('in', asset_items)}):
		asset_items_data.setdefault(d.name, d)

	return asset_items_data

def validate_item_type(doc, fieldname, message):
	# iterate through items and check if they are valid sales or purchase items
	items = [d.item_code for d in doc.items if d.item_code]

	# No validation check inase of creating transaction using 'Opening Invoice Creation Tool'
	if not items:
		return

	item_list = ", ".join(["'%s'" % frappe.db.escape(d) for d in items])

	invalid_items = [d[0] for d in frappe.db.sql("""
		select item_code from tabItem where name in ({0}) and {1}=0
		""".format(item_list, fieldname), as_list=True)]

	if invalid_items:
		items = ", ".join([d for d in invalid_items])

		if len(invalid_items) > 1:
			error_message = _("Following items {0} are not marked as {1} item. You can enable them as {1} item from its Item master".format(items, message))
		else:
			error_message = _("Following item {0} is not marked as {1} item. You can enable them as {1} item from its Item master".format(items, message))

		frappe.throw(error_message)
