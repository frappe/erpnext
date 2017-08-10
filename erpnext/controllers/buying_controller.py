# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt,cint, cstr

from erpnext.accounts.party import get_party_details
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.buying.utils import validate_for_items
from erpnext.stock.stock_ledger import get_valuation_rate

from erpnext.controllers.stock_controller import StockController

class BuyingController(StockController):
	def __setup__(self):
		if hasattr(self, "taxes"):
			self.print_templates = {
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

		self.set_qty_as_per_stock_uom()
		self.validate_stock_or_nonstock_items()
		self.validate_warehouse()

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
			self.update_if_missing(get_party_details(self.supplier, party_type="Supplier", ignore_permissions=self.flags.ignore_permissions))

		self.set_missing_item_details(for_validate)

	def set_supplier_from_item_default(self):
		if self.meta.get_field("supplier") and not self.supplier:
			for d in self.get("items"):
				supplier = frappe.db.get_value("Item", d.item_code, "default_supplier")
				if supplier:
					self.supplier = supplier
					break

	def validate_stock_or_nonstock_items(self):
		if self.meta.get_field("taxes") and not self.get_stock_items():
			tax_for_valuation = [d for d in self.get("taxes")
				if d.category in ["Valuation", "Valuation and Total"]]

			if tax_for_valuation:
				for d in tax_for_valuation:
					d.category = 'Total'
				msgprint(_('Tax Category has been changed to "Total" because all the Items are non-stock items'))

	def set_landed_cost_voucher_amount(self):
		for d in self.get("items"):
			lc_voucher_data = frappe.db.sql("""select sum(applicable_charges), cost_center
				from `tabLanded Cost Item`
				where docstatus = 1 and purchase_receipt_item = %s""", d.name)
			d.landed_cost_voucher_amount = lc_voucher_data[0][0] if lc_voucher_data else 0.0
			if not d.cost_center and lc_voucher_data and lc_voucher_data[0][1]:
				d.db_set('cost_center', lc_voucher_data[0][1])

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		if self.meta.get_field("base_in_words"):
			self.base_in_words = money_in_words(self.base_grand_total, self.company_currency)
		if self.meta.get_field("in_words"):
			self.in_words = money_in_words(self.grand_total, self.currency)

	# update valuation rate
	def update_valuation_rate(self, parentfield):
		"""
			item_tax_amount is the total tax amount applied on that item
			stored for valuation

			TODO: rename item_tax_amount to valuation_tax_amount
		"""
		stock_items = self.get_stock_items()

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

		else:
			for item in self.get("items"):
				if item.bom:
					item.bom = None

	def create_raw_materials_supplied(self, raw_material_table):
		if self.is_subcontracted=="Yes":
			parent_items = []
			for item in self.get("items"):
				if self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
					item.rm_supp_cost = 0.0
				if item.item_code in self.sub_contracted_items:
					self.update_raw_materials_supplied(item, raw_material_table)

					if [item.item_code, item.name] not in parent_items:
						parent_items.append([item.item_code, item.name])

			self.cleanup_raw_materials_supplied(parent_items, raw_material_table)

		elif self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			for item in self.get("items"):
				item.rm_supp_cost = 0.0

		if self.is_subcontracted == "No" and self.get("supplied_items"):
			self.set('supplied_items', [])

	def update_raw_materials_supplied(self, item, raw_material_table):
		bom_items = self.get_items_from_bom(item.item_code, item.bom)
		raw_materials_cost = 0

		for bom_item in bom_items:
			# check if exists
			exists = 0
			for d in self.get(raw_material_table):
				if d.main_item_code == item.item_code and d.rm_item_code == bom_item.item_code \
					and d.reference_name == item.name:
						rm, exists = d, 1
						break

			if not exists:
				rm = self.append(raw_material_table, {})

			required_qty = flt(bom_item.qty_consumed_per_unit) * flt(item.qty) * flt(item.conversion_factor)
			rm.reference_name = item.name
			rm.bom_detail_no = bom_item.name
			rm.main_item_code = item.item_code
			rm.rm_item_code = bom_item.item_code
			rm.stock_uom = bom_item.stock_uom
			rm.required_qty = required_qty

			rm.conversion_factor = item.conversion_factor

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

	def get_items_from_bom(self, item_code, bom):
		bom_items = frappe.db.sql("""select t2.item_code,
			t2.stock_qty / ifnull(t1.quantity, 1) as qty_consumed_per_unit,
			t2.rate, t2.stock_uom, t2.name, t2.description
			from `tabBOM` t1, `tabBOM Item` t2, tabItem t3
			where t2.parent = t1.name and t1.item = %s
			and t1.docstatus = 1 and t1.is_active = 1 and t1.name = %s
			and t2.item_code = t3.name and t3.is_stock_item = 1""", (item_code, bom), as_dict=1)

		if not bom_items:
			msgprint(_("Specified BOM {0} does not exist for Item {1}").format(bom, item_code), raise_exception=1)

		return bom_items

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
		self.update_ordered_qty()

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

	def update_ordered_qty(self):
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

