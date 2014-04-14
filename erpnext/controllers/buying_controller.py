# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt, _round
from erpnext.setup.utils import get_company_currency
from erpnext.accounts.party import get_party_details

from erpnext.controllers.stock_controller import StockController

class BuyingController(StockController):
	def onload_post_render(self):
		# contact, address, item details
		self.set_missing_values()

	def validate(self):
		super(BuyingController, self).validate()
		if getattr(self, "supplier", None) and not self.supplier_name:
			self.supplier_name = frappe.db.get_value("Supplier",
				self.supplier, "supplier_name")
		self.is_item_table_empty()
		self.validate_stock_or_nonstock_items()
		self.validate_warehouse()

	def set_missing_values(self, for_validate=False):
		super(BuyingController, self).set_missing_values(for_validate)

		self.set_supplier_from_item_default()
		self.set_price_list_currency("Buying")

		# set contact and address details for supplier, if they are not mentioned
		if getattr(self, "supplier", None):
			self.update_if_missing(get_party_details(self.supplier, party_type="Supplier"))

		self.set_missing_item_details()
		if self.get("__islocal"):
			self.set_taxes("other_charges", "taxes_and_charges")

	def set_supplier_from_item_default(self):
		if self.meta.get_field("supplier") and not self.supplier:
			for d in self.get(self.fname):
				supplier = frappe.db.get_value("Item", d.item_code, "default_supplier")
				if supplier:
					self.supplier = supplier
					break

	def validate_warehouse(self):
		from erpnext.stock.utils import validate_warehouse_company

		warehouses = list(set([d.warehouse for d in
			self.get(self.fname) if getattr(d, "warehouse", None)]))

		for w in warehouses:
			validate_warehouse_company(w, self.company)

	def validate_stock_or_nonstock_items(self):
		if not self.get_stock_items():
			tax_for_valuation = [d.account_head for d in
				self.get("other_charges")
				if d.category in ["Valuation", "Valuation and Total"]]
			if tax_for_valuation:
				frappe.throw(_("Tax Category can not be 'Valuation' or 'Valuation and Total' as all items are non-stock items"))

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		company_currency = get_company_currency(self.company)
		if self.meta.get_field("in_words"):
			self.in_words = money_in_words(self.grand_total, company_currency)
		if self.meta.get_field("in_words_import"):
			self.in_words_import = money_in_words(self.grand_total_import,
		 		self.currency)

	def calculate_taxes_and_totals(self):
		self.other_fname = "other_charges"
		super(BuyingController, self).calculate_taxes_and_totals()
		self.calculate_total_advance("Purchase Invoice", "advance_allocation_details")

	def calculate_item_values(self):
		for item in self.item_doclist:
			self.round_floats_in(item)

			if item.discount_percentage == 100.0:
				item.rate = 0.0
			elif not item.rate:
				item.rate = flt(item.price_list_rate * (1.0 - (item.discount_percentage / 100.0)),
					self.precision("rate", item))

			item.amount = flt(item.rate * item.qty,
				self.precision("amount", item))
			item.item_tax_amount = 0.0;

			self._set_in_company_currency(item, "amount", "base_amount")
			self._set_in_company_currency(item, "price_list_rate", "base_price_list_rate")
			self._set_in_company_currency(item, "rate", "base_rate")


	def calculate_net_total(self):
		self.net_total = self.net_total_import = 0.0

		for item in self.item_doclist:
			self.net_total += item.base_amount
			self.net_total_import += item.amount

		self.round_floats_in(self, ["net_total", "net_total_import"])

	def calculate_totals(self):
		self.grand_total = flt(self.tax_doclist[-1].total if self.tax_doclist
			else self.net_total, self.precision("grand_total"))
		self.grand_total_import = flt(self.grand_total / self.conversion_rate,
			self.precision("grand_total_import"))

		self.total_tax = flt(self.grand_total - self.net_total,
			self.precision("total_tax"))

		if self.meta.get_field("rounded_total"):
			self.rounded_total = _round(self.grand_total)

		if self.meta.get_field("rounded_total_import"):
			self.rounded_total_import = _round(self.grand_total_import)

		if self.meta.get_field("other_charges_added"):
			self.other_charges_added = flt(sum([flt(d.tax_amount) for d in self.tax_doclist
				if d.add_deduct_tax=="Add" and d.category in ["Valuation and Total", "Total"]]),
				self.precision("other_charges_added"))

		if self.meta.get_field("other_charges_deducted"):
			self.other_charges_deducted = flt(sum([flt(d.tax_amount) for d in self.tax_doclist
				if d.add_deduct_tax=="Deduct" and d.category in ["Valuation and Total", "Total"]]),
				self.precision("other_charges_deducted"))

		if self.meta.get_field("other_charges_added_import"):
			self.other_charges_added_import = flt(self.other_charges_added /
				self.conversion_rate, self.precision("other_charges_added_import"))

		if self.meta.get_field("other_charges_deducted_import"):
			self.other_charges_deducted_import = flt(self.other_charges_deducted /
				self.conversion_rate, self.precision("other_charges_deducted_import"))

	def calculate_outstanding_amount(self):
		if self.doctype == "Purchase Invoice" and self.docstatus == 0:
			self.total_advance = flt(self.total_advance,
				self.precision("total_advance"))
			self.total_amount_to_pay = flt(self.grand_total - flt(self.write_off_amount,
				self.precision("write_off_amount")), self.precision("total_amount_to_pay"))
			self.outstanding_amount = flt(self.total_amount_to_pay - self.total_advance,
				self.precision("outstanding_amount"))

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
				stock_items_amount += flt(d.base_amount)
				last_stock_item_idx = d.idx

		total_valuation_amount = sum([flt(d.tax_amount) for d in
			self.get("other_charges")
			if d.category in ["Valuation", "Valuation and Total"]])


		valuation_amount_adjustment = total_valuation_amount
		for i, item in enumerate(self.get(parentfield)):
			if item.item_code and item.qty and item.item_code in stock_items:
				item_proportion = flt(item.base_amount) / stock_items_amount if stock_items_amount \
					else flt(item.qty) / stock_items_qty

				if i == (last_stock_item_idx - 1):
					item.item_tax_amount = flt(valuation_amount_adjustment,
						self.precision("item_tax_amount", item))
				else:
					item.item_tax_amount = flt(item_proportion * total_valuation_amount,
						self.precision("item_tax_amount", item))
					valuation_amount_adjustment -= item.item_tax_amount

				self.round_floats_in(item)

				item.conversion_factor = item.conversion_factor or flt(frappe.db.get_value(
					"UOM Conversion Detail", {"parent": item.item_code, "uom": item.uom},
					"conversion_factor")) or 1
				qty_in_stock_uom = flt(item.qty * item.conversion_factor)
				item.valuation_rate = ((item.base_amount + item.item_tax_amount + item.rm_supp_cost)
					/ qty_in_stock_uom)
			else:
				item.valuation_rate = 0.0

	def validate_for_subcontracting(self):
		if not self.is_subcontracted and self.sub_contracted_items:
			frappe.throw(_("Please enter 'Is Subcontracted' as Yes or No"))

		if self.doctype == "Purchase Receipt" and self.is_subcontracted=="Yes" \
			and not self.supplier_warehouse:
				frappe.throw(_("Supplier Warehouse mandatory for sub-contracted Purchase Receipt"))

	def update_raw_materials_supplied(self, raw_material_table):
		self.set(raw_material_table, [])
		if self.is_subcontracted=="Yes":
			for item in self.get(self.fname):
				if item.item_code in self.sub_contracted_items:
					self.add_bom_items(item, raw_material_table)

	def add_bom_items(self, d, raw_material_table):
		bom_items = self.get_items_from_default_bom(d.item_code)
		raw_materials_cost = 0
		for item in bom_items:
			required_qty = flt(item.qty_consumed_per_unit) * flt(d.qty) * flt(d.conversion_factor)
			rm_doclist = {
				"doctype": self.doctype + " Item Supplied",
				"reference_name": d.name,
				"bom_detail_no": item.name,
				"main_item_code": d.item_code,
				"rm_item_code": item.item_code,
				"stock_uom": item.stock_uom,
				"required_qty": required_qty,
				"conversion_factor": d.conversion_factor,
				"rate": item.rate,
				"amount": required_qty * flt(item.rate)
			}
			if self.doctype == "Purchase Receipt":
				rm_doclist.update({
					"consumed_qty": required_qty,
					"description": item.description,
				})

			self.append(raw_material_table, rm_doclist)

			raw_materials_cost += required_qty * flt(item.rate)

		if self.doctype == "Purchase Receipt":
			d.rm_supp_cost = raw_materials_cost

	def get_items_from_default_bom(self, item_code):
		bom_items = frappe.db.sql("""select t2.item_code, t2.qty_consumed_per_unit,
			t2.rate, t2.stock_uom, t2.name, t2.description
			from `tabBOM` t1, `tabBOM Item` t2
			where t2.parent = t1.name and t1.item = %s and t1.is_default = 1
			and t1.docstatus = 1 and t1.is_active = 1""", item_code, as_dict=1)
		if not bom_items:
			msgprint(_("No default BOM exists for Item {0}").format(item_code), raise_exception=1)

		return bom_items

	@property
	def sub_contracted_items(self):
		if not hasattr(self, "_sub_contracted_items"):
			self._sub_contracted_items = []
			item_codes = list(set(item.item_code for item in
				self.get(self.fname)))
			if item_codes:
				self._sub_contracted_items = [r[0] for r in frappe.db.sql("""select name
					from `tabItem` where name in (%s) and is_sub_contracted_item='Yes'""" % \
					(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return self._sub_contracted_items

	@property
	def purchase_items(self):
		if not hasattr(self, "_purchase_items"):
			self._purchase_items = []
			item_codes = list(set(item.item_code for item in
				self.get(self.fname)))
			if item_codes:
				self._purchase_items = [r[0] for r in frappe.db.sql("""select name
					from `tabItem` where name in (%s) and is_purchase_item='Yes'""" % \
					(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return self._purchase_items


	def is_item_table_empty(self):
		if not len(self.get(self.fname)):
			frappe.throw(_("Item table can not be blank"))
