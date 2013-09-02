# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
from webnotes.utils import flt, _round

from buying.utils import get_item_details
from setup.utils import get_company_currency

from controllers.stock_controller import StockController

class WrongWarehouseCompany(Exception): pass

class BuyingController(StockController):
	def onload_post_render(self):
		# contact, address, item details
		self.set_missing_values()
	
	def validate(self):
		super(BuyingController, self).validate()
		if self.doc.supplier and not self.doc.supplier_name:
			self.doc.supplier_name = webnotes.conn.get_value("Supplier", 
				self.doc.supplier, "supplier_name")
		self.validate_stock_or_nonstock_items()
		self.validate_warehouse_belongs_to_company()
		
	def set_missing_values(self, for_validate=False):
		super(BuyingController, self).set_missing_values(for_validate)

		self.set_supplier_from_item_default()
		self.set_price_list_currency("Buying")
		
		# set contact and address details for supplier, if they are not mentioned
		if self.doc.supplier and not (self.doc.contact_person and self.doc.supplier_address):
			for fieldname, val in self.get_supplier_defaults().items():
				if not self.doc.fields.get(fieldname) and self.meta.get_field(fieldname):
					self.doc.fields[fieldname] = val

		self.set_missing_item_details(get_item_details)
		if self.doc.fields.get("__islocal"):
			self.set_taxes("purchase_tax_details", "purchase_other_charges")

	def set_supplier_from_item_default(self):
		if self.meta.get_field("supplier") and not self.doc.supplier:
			for d in self.doclist.get({"doctype": self.tname}):
				supplier = webnotes.conn.get_value("Item", d.item_code, "default_supplier")
				if supplier:
					self.doc.supplier = supplier
					break

	def get_purchase_tax_details(self):
		self.doclist = self.doc.clear_table(self.doclist, "purchase_tax_details")
		self.set_taxes("purchase_tax_details", "purchase_other_charges")
		
	def validate_warehouse_belongs_to_company(self):
		for warehouse, company in webnotes.conn.get_values("Warehouse", 
			self.doclist.get_distinct_values("warehouse"), "company").items():
			if company and company != self.doc.company:
				webnotes.msgprint(_("Company mismatch for Warehouse") + (": %s" % (warehouse,)),
					raise_exception=WrongWarehouseCompany)

	def validate_stock_or_nonstock_items(self):
		if not self.stock_items:
			tax_for_valuation = [d.account_head for d in 
				self.doclist.get({"parentfield": "purchase_tax_details"}) 
				if d.category in ["Valuation", "Valuation and Total"]]
			if tax_for_valuation:
				webnotes.msgprint(_("""Tax Category can not be 'Valuation' or 'Valuation and Total' 
					as all items are non-stock items"""), raise_exception=1)
			
	def set_total_in_words(self):
		from webnotes.utils import money_in_words
		company_currency = get_company_currency(self.doc.company)
		if self.meta.get_field("in_words"):
			self.doc.in_words = money_in_words(self.doc.grand_total, company_currency)
		if self.meta.get_field("in_words_import"):
			self.doc.in_words_import = money_in_words(self.doc.grand_total_import,
		 		self.doc.currency)
		
	def calculate_taxes_and_totals(self):
		self.other_fname = "purchase_tax_details"
		super(BuyingController, self).calculate_taxes_and_totals()
		self.calculate_total_advance("Purchase Invoice", "advance_allocation_details")
		
	def calculate_item_values(self):
		# hack! - cleaned up in _cleanup()
		if self.doc.doctype != "Purchase Invoice":
			df = self.meta.get_field("purchase_rate", parentfield=self.fname)
			df.fieldname = "rate"
			
		for item in self.item_doclist:
			# hack! - cleaned up in _cleanup()
			if self.doc.doctype != "Purchase Invoice":
				item.rate = item.purchase_rate
				
			self.round_floats_in(item)

			if item.discount_rate == 100.0:
				item.import_rate = 0.0
			elif not item.import_rate:
				item.import_rate = flt(item.import_ref_rate * (1.0 - (item.discount_rate / 100.0)),
					self.precision("import_rate", item))
						
			item.import_amount = flt(item.import_rate * item.qty,
				self.precision("import_amount", item))
			item.item_tax_amount = 0.0;
				
			self._set_in_company_currency(item, "import_ref_rate", "purchase_ref_rate")
			self._set_in_company_currency(item, "import_rate", "rate")
			self._set_in_company_currency(item, "import_amount", "amount")
			
	def calculate_net_total(self):
		self.doc.net_total = self.doc.net_total_import = 0.0

		for item in self.item_doclist:
			self.doc.net_total += item.amount
			self.doc.net_total_import += item.import_amount
			
		self.round_floats_in(self.doc, ["net_total", "net_total_import"])
		
	def calculate_totals(self):
		self.doc.grand_total = flt(self.tax_doclist and \
			self.tax_doclist[-1].total or self.doc.net_total, self.precision("grand_total"))
		self.doc.grand_total_import = flt(self.doc.grand_total / self.doc.conversion_rate,
			self.precision("grand_total_import"))

		self.doc.total_tax = flt(self.doc.grand_total - self.doc.net_total,
			self.precision("total_tax"))

		if self.meta.get_field("rounded_total"):
			self.doc.rounded_total = _round(self.doc.grand_total)
		
		if self.meta.get_field("rounded_total_import"):
			self.doc.rounded_total_import = _round(self.doc.grand_total_import)
			
	def calculate_outstanding_amount(self):
		if self.doc.doctype == "Purchase Invoice" and self.doc.docstatus < 2:
			self.doc.total_advance = flt(self.doc.total_advance,
				self.precision("total_advance"))
			self.doc.total_amount_to_pay = flt(self.doc.grand_total - flt(self.doc.write_off_amount,
				self.precision("write_off_amount")), self.precision("total_amount_to_pay"))
			self.doc.outstanding_amount = flt(self.doc.total_amount_to_pay - self.doc.total_advance,
				self.precision("outstanding_amount"))
			
	def _cleanup(self):
		super(BuyingController, self)._cleanup()
			
		# except in purchase invoice, rate field is purchase_rate		
		# reset fieldname of rate
		if self.doc.doctype != "Purchase Invoice":
			df = self.meta.get_field("rate", parentfield=self.fname)
			df.fieldname = "purchase_rate"
			
			for item in self.item_doclist:
				item.purchase_rate = item.rate
				del item.fields["rate"]
		
		if not self.meta.get_field("item_tax_amount", parentfield=self.fname):
			for item in self.item_doclist:
				del item.fields["item_tax_amount"]
				
	def set_item_tax_amount(self, item, tax, current_tax_amount):
		"""
			item_tax_amount is the total tax amount applied on that item
			stored for valuation 
			
			TODO: rename item_tax_amount to valuation_tax_amount
		"""
		if tax.category in ["Valuation", "Valuation and Total"] and \
			self.meta.get_field("item_tax_amount", parentfield=self.fname):
				item.item_tax_amount += flt(current_tax_amount, self.precision("item_tax_amount", item))
				
	# update valuation rate
	def update_valuation_rate(self, parentfield):
		for item in self.doclist.get({"parentfield": parentfield}):
			item.conversion_factor = item.conversion_factor or flt(webnotes.conn.get_value(
				"UOM Conversion Detail", {"parent": item.item_code, "uom": item.uom}, 
				"conversion_factor")) or 1
			
			if item.item_code and item.qty:
				self.round_floats_in(item)
				
				purchase_rate = item.rate if self.doc.doctype == "Purchase Invoice" else item.purchase_rate
				
				# if no item code, which is sometimes the case in purchase invoice, 
				# then it is not possible to track valuation against it
				item.valuation_rate = flt((purchase_rate + 
					(item.item_tax_amount + item.rm_supp_cost) / item.qty) / item.conversion_factor, 
					self.precision("valuation_rate", item))
			else:
				item.valuation_rate = 0.0
				
	def validate_for_subcontracting(self):
		if not self.doc.is_subcontracted and self.sub_contracted_items:
			webnotes.msgprint(_("""Please enter whether %s is made for subcontracting or purchasing,
			 	in 'Is Subcontracted' field""" % self.doc.doctype), raise_exception=1)
			
		if self.doc.doctype == "Purchase Receipt" and self.doc.is_subcontracted=="Yes" \
			and not self.doc.supplier_warehouse:
				webnotes.msgprint(_("Supplier Warehouse mandatory subcontracted purchase receipt"), 
					raise_exception=1)
										
	def update_raw_materials_supplied(self, raw_material_table):
		self.doclist = self.doc.clear_table(self.doclist, raw_material_table)
		if self.doc.is_subcontracted=="Yes":
			for item in self.doclist.get({"parentfield": self.fname}):
				if item.item_code in self.sub_contracted_items:
					self.add_bom_items(item, raw_material_table)

	def add_bom_items(self, d, raw_material_table):
		bom_items = self.get_items_from_default_bom(d.item_code)
		raw_materials_cost = 0
		for item in bom_items:
			required_qty = flt(item.qty_consumed_per_unit) * flt(d.qty) * flt(d.conversion_factor)
			rm_doclist = {
				"parentfield": raw_material_table,
				"doctype": self.doc.doctype + " Item Supplied",
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
			if self.doc.doctype == "Purchase Receipt":
				rm_doclist.update({
					"consumed_qty": required_qty,
					"description": item.description,
				})
				
			self.doclist.append(rm_doclist)
			
			raw_materials_cost += required_qty * flt(item.rate)
			
		if self.doc.doctype == "Purchase Receipt":
			d.rm_supp_cost = raw_materials_cost

	def get_items_from_default_bom(self, item_code):
		# print webnotes.conn.sql("""select name from `tabBOM` where item = '_Test FG Item'""")
		bom_items = webnotes.conn.sql("""select t2.item_code, t2.qty_consumed_per_unit, 
			t2.rate, t2.stock_uom, t2.name, t2.description 
			from `tabBOM` t1, `tabBOM Item` t2 
			where t2.parent = t1.name and t1.item = %s and t1.is_default = 1 
			and t1.docstatus = 1 and t1.is_active = 1""", item_code, as_dict=1)
		if not bom_items:
			msgprint(_("No default BOM exists for item: ") + item_code, raise_exception=1)
		
		return bom_items

	@property
	def sub_contracted_items(self):
		if not hasattr(self, "_sub_contracted_items"):
			self._sub_contracted_items = []
			item_codes = list(set(item.item_code for item in 
				self.doclist.get({"parentfield": self.fname})))
			if item_codes:
				self._sub_contracted_items = [r[0] for r in webnotes.conn.sql("""select name
					from `tabItem` where name in (%s) and is_sub_contracted_item='Yes'""" % \
					(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return self._sub_contracted_items
		
	@property
	def purchase_items(self):
		if not hasattr(self, "_purchase_items"):
			self._purchase_items = []
			item_codes = list(set(item.item_code for item in 
				self.doclist.get({"parentfield": self.fname})))
			if item_codes:
				self._purchase_items = [r[0] for r in webnotes.conn.sql("""select name
					from `tabItem` where name in (%s) and is_purchase_item='Yes'""" % \
					(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return self._purchase_items
