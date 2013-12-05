# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, flt, comma_or, _round, cstr
from setup.utils import get_company_currency
from selling.utils import get_item_details
from webnotes import msgprint, _

from controllers.stock_controller import StockController

class SellingController(StockController):
	def onload_post_render(self):
		# contact, address, item details and pos details (if applicable)
		self.set_missing_values()
		
	def validate(self):
		super(SellingController, self).validate()
		self.validate_max_discount()
		check_active_sales_items(self)
	
	def get_sender(self, comm):
		return webnotes.conn.get_value('Sales Email Settings', None, 'email_id')
	
	def set_missing_values(self, for_validate=False):
		super(SellingController, self).set_missing_values(for_validate)
		
		# set contact and address details for customer, if they are not mentioned
		self.set_missing_lead_customer_details()
		self.set_price_list_and_item_details()
		if self.doc.fields.get("__islocal"):
			self.set_taxes("other_charges", "charge")
					
	def set_missing_lead_customer_details(self):
		if self.doc.customer:
			if not (self.doc.contact_person and self.doc.customer_address and self.doc.customer_name):
				for fieldname, val in self.get_customer_defaults().items():
					if not self.doc.fields.get(fieldname) and self.meta.get_field(fieldname):
						self.doc.fields[fieldname] = val
		
		elif self.doc.lead:
			if not (self.doc.customer_address and self.doc.customer_name and \
				self.doc.contact_display):
				for fieldname, val in self.get_lead_defaults().items():
					if not self.doc.fields.get(fieldname) and self.meta.get_field(fieldname):
						self.doc.fields[fieldname] = val
						
	def set_price_list_and_item_details(self):
		self.set_price_list_currency("Selling")
		self.set_missing_item_details(get_item_details)
										
	def get_other_charges(self):
		self.doclist = self.doc.clear_table(self.doclist, "other_charges")
		self.set_taxes("other_charges", "charge")
		
	def apply_shipping_rule(self):
		if self.doc.shipping_rule:
			shipping_rule = webnotes.bean("Shipping Rule", self.doc.shipping_rule)
			value = self.doc.net_total
			
			# TODO
			# shipping rule calculation based on item's net weight
			
			shipping_amount = 0.0
			for condition in shipping_rule.doclist.get({"parentfield": "shipping_rule_conditions"}):
				if not condition.to_value or (flt(condition.from_value) <= value <= flt(condition.to_value)):
					shipping_amount = condition.shipping_amount
					break
			
			self.doclist.append({
				"doctype": "Sales Taxes and Charges",
				"parentfield": "other_charges",
				"charge_type": "Actual",
				"account_head": shipping_rule.doc.account,
				"cost_center": shipping_rule.doc.cost_center,
				"description": shipping_rule.doc.label,
				"rate": shipping_amount
			})
		
	def set_total_in_words(self):
		from webnotes.utils import money_in_words
		company_currency = get_company_currency(self.doc.company)
		
		disable_rounded_total = cint(webnotes.conn.get_value("Global Defaults", None, 
			"disable_rounded_total"))
			
		if self.meta.get_field("in_words"):
			self.doc.in_words = money_in_words(disable_rounded_total and 
				self.doc.grand_total or self.doc.rounded_total, company_currency)
		if self.meta.get_field("in_words_export"):
			self.doc.in_words_export = money_in_words(disable_rounded_total and 
				self.doc.grand_total_export or self.doc.rounded_total_export, self.doc.currency)
				
	def calculate_taxes_and_totals(self):
		self.other_fname = "other_charges"
		
		super(SellingController, self).calculate_taxes_and_totals()
		
		self.calculate_total_advance("Sales Invoice", "advance_adjustment_details")
		self.calculate_commission()
		self.calculate_contribution()
				
	def determine_exclusive_rate(self):
		if not any((cint(tax.included_in_print_rate) for tax in self.tax_doclist)):
			# no inclusive tax
			return
		
		for item in self.item_doclist:
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
			cumulated_tax_fraction = 0
			for i, tax in enumerate(self.tax_doclist):
				tax.tax_fraction_for_current_item = self.get_current_tax_fraction(tax, item_tax_map)
				
				if i==0:
					tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item
				else:
					tax.grand_total_fraction_for_current_item = \
						self.tax_doclist[i-1].grand_total_fraction_for_current_item \
						+ tax.tax_fraction_for_current_item
						
				cumulated_tax_fraction += tax.tax_fraction_for_current_item
			
			if cumulated_tax_fraction:
				item.amount = flt((item.export_amount * self.doc.conversion_rate) /
					(1 + cumulated_tax_fraction), self.precision("amount", item))
					
				item.basic_rate = flt(item.amount / item.qty, self.precision("basic_rate", item))
				
				if item.adj_rate == 100:
					item.base_ref_rate = item.basic_rate
					item.basic_rate = 0.0
				else:
					item.base_ref_rate = flt(item.basic_rate / (1 - (item.adj_rate / 100.0)),
						self.precision("base_ref_rate", item))
			
	def get_current_tax_fraction(self, tax, item_tax_map):
		"""
			Get tax fraction for calculating tax exclusive amount
			from tax inclusive amount
		"""
		current_tax_fraction = 0
		
		if cint(tax.included_in_print_rate):
			tax_rate = self._get_tax_rate(tax, item_tax_map)
			
			if tax.charge_type == "On Net Total":
				current_tax_fraction = tax_rate / 100.0
			
			elif tax.charge_type == "On Previous Row Amount":
				current_tax_fraction = (tax_rate / 100.0) * \
					self.tax_doclist[cint(tax.row_id) - 1].tax_fraction_for_current_item
			
			elif tax.charge_type == "On Previous Row Total":
				current_tax_fraction = (tax_rate / 100.0) * \
					self.tax_doclist[cint(tax.row_id) - 1].grand_total_fraction_for_current_item
						
		return current_tax_fraction
		
	def calculate_item_values(self):
		for item in self.item_doclist:
			self.round_floats_in(item)
			
			if item.adj_rate == 100:
				item.export_rate = 0
			elif not item.export_rate:
				item.export_rate = flt(item.ref_rate * (1.0 - (item.adj_rate / 100.0)),
					self.precision("export_rate", item))
						
			item.export_amount = flt(item.export_rate * item.qty,
				self.precision("export_amount", item))

			self._set_in_company_currency(item, "ref_rate", "base_ref_rate")
			self._set_in_company_currency(item, "export_rate", "basic_rate")
			self._set_in_company_currency(item, "export_amount", "amount")
			
	def calculate_net_total(self):
		self.doc.net_total = self.doc.net_total_export = 0.0

		for item in self.item_doclist:
			self.doc.net_total += item.amount
			self.doc.net_total_export += item.export_amount
		
		self.round_floats_in(self.doc, ["net_total", "net_total_export"])
				
	def calculate_totals(self):
		self.doc.grand_total = flt(self.tax_doclist and \
			self.tax_doclist[-1].total or self.doc.net_total, self.precision("grand_total"))
		self.doc.grand_total_export = flt(self.doc.grand_total / self.doc.conversion_rate, 
			self.precision("grand_total_export"))
			
		self.doc.other_charges_total = flt(self.doc.grand_total - self.doc.net_total,
			self.precision("other_charges_total"))
		self.doc.other_charges_total_export = flt(self.doc.grand_total_export - self.doc.net_total_export,
			self.precision("other_charges_total_export"))
		
		self.doc.rounded_total = _round(self.doc.grand_total)
		self.doc.rounded_total_export = _round(self.doc.grand_total_export)
		
	def calculate_outstanding_amount(self):
		# NOTE: 
		# write_off_amount is only for POS Invoice
		# total_advance is only for non POS Invoice
		if self.doc.doctype == "Sales Invoice" and self.doc.docstatus < 2:
			self.round_floats_in(self.doc, ["grand_total", "total_advance", "write_off_amount",
				"paid_amount"])
			total_amount_to_pay = self.doc.grand_total - self.doc.write_off_amount
			self.doc.outstanding_amount = flt(total_amount_to_pay - self.doc.total_advance - self.doc.paid_amount,
				self.precision("outstanding_amount"))
		
	def calculate_commission(self):
		if self.meta.get_field("commission_rate"):
			self.round_floats_in(self.doc, ["net_total", "commission_rate"])
			if self.doc.commission_rate > 100.0:
				msgprint(_(self.meta.get_label("commission_rate")) + " " + 
					_("cannot be greater than 100"), raise_exception=True)
		
			self.doc.total_commission = flt(self.doc.net_total * self.doc.commission_rate / 100.0,
				self.precision("total_commission"))

	def calculate_contribution(self):
		total = 0.0
		sales_team = self.doclist.get({"parentfield": "sales_team"})
		for sales_person in sales_team:
			self.round_floats_in(sales_person)

			sales_person.allocated_amount = flt(
				self.doc.net_total * sales_person.allocated_percentage / 100.0,
				self.precision("allocated_amount", sales_person))
			
			total += sales_person.allocated_percentage
		
		if sales_team and total != 100.0:
			msgprint(_("Total") + " " + 
				_(self.meta.get_label("allocated_percentage", parentfield="sales_team")) + 
				" " + _("should be 100%"), raise_exception=True)
			
	def validate_order_type(self):
		valid_types = ["Sales", "Maintenance", "Shopping Cart"]
		if not self.doc.order_type:
			self.doc.order_type = "Sales"
		elif self.doc.order_type not in valid_types:
			msgprint(_(self.meta.get_label("order_type")) + " " + 
				_("must be one of") + ": " + comma_or(valid_types), raise_exception=True)
				
	def check_credit(self, grand_total):
		customer_account = webnotes.conn.get_value("Account", {"company": self.doc.company, 
			"master_name": self.doc.customer}, "name")
		if customer_account:
			total_outstanding = webnotes.conn.sql("""select 
				sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) 
				from `tabGL Entry` where account = %s""", customer_account)
			total_outstanding = total_outstanding[0][0] if total_outstanding else 0
			
			outstanding_including_current = flt(total_outstanding) + flt(grand_total)
			webnotes.bean('Account', customer_account).run_method("check_credit_limit", 
				outstanding_including_current)
				
	def validate_max_discount(self):
		for d in self.doclist.get({"parentfield": self.fname}):
			discount = flt(webnotes.conn.get_value("Item", d.item_code, "max_discount"))
			
			if discount and flt(d.adj_rate) > discount:
				webnotes.throw(_("You cannot give more than ") + cstr(discount) + "% " + 
					_("discount on Item Code") + ": " + cstr(d.item_code))
					
	def get_item_list(self):
		il = []
		for d in self.doclist.get({"parentfield": self.fname}):
			reserved_warehouse = ""
			reserved_qty_for_main_item = 0
			
			if self.doc.doctype == "Sales Order":
				if (webnotes.conn.get_value("Item", d.item_code, "is_stock_item") == 'Yes' or 
					self.has_sales_bom(d.item_code)) and not d.reserved_warehouse:
						webnotes.throw(_("Please enter Reserved Warehouse for item ") + 
							d.item_code + _(" as it is stock Item or packing item"))
				reserved_warehouse = d.reserved_warehouse
				if flt(d.qty) > flt(d.delivered_qty):
					reserved_qty_for_main_item = flt(d.qty) - flt(d.delivered_qty)
				
			if self.doc.doctype == "Delivery Note" and d.against_sales_order:
				# if SO qty is 10 and there is tolerance of 20%, then it will allow DN of 12.
				# But in this case reserved qty should only be reduced by 10 and not 12
				
				already_delivered_qty = self.get_already_delivered_qty(self.doc.name, 
					d.against_sales_order, d.prevdoc_detail_docname)
				so_qty, reserved_warehouse = self.get_so_qty_and_warehouse(d.prevdoc_detail_docname)
				
				if already_delivered_qty + d.qty > so_qty:
					reserved_qty_for_main_item = -(so_qty - already_delivered_qty)
				else:
					reserved_qty_for_main_item = -flt(d.qty)

			if self.has_sales_bom(d.item_code):
				for p in self.doclist.get({"parentfield": "packing_details"}):
					if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
						# the packing details table's qty is already multiplied with parent's qty
						il.append(webnotes._dict({
							'warehouse': p.warehouse,
							'reserved_warehouse': reserved_warehouse,
							'item_code': p.item_code,
							'qty': flt(p.qty),
							'reserved_qty': (flt(p.qty)/flt(d.qty)) * reserved_qty_for_main_item,
							'uom': p.uom,
							'batch_no': cstr(p.batch_no).strip(),
							'serial_no': cstr(p.serial_no).strip(),
							'name': d.name
						}))
			else:
				il.append(webnotes._dict({
					'warehouse': d.warehouse,
					'reserved_warehouse': reserved_warehouse,
					'item_code': d.item_code,
					'qty': d.qty,
					'reserved_qty': reserved_qty_for_main_item,
					'uom': d.stock_uom,
					'batch_no': cstr(d.batch_no).strip(),
					'serial_no': cstr(d.serial_no).strip(),
					'name': d.name
				}))
		return il
		
	def has_sales_bom(self, item_code):
		return webnotes.conn.sql("""select name from `tabSales BOM` 
			where new_item_code=%s and docstatus != 2""", item_code)
			
	def get_already_delivered_qty(self, dn, so, so_detail):
		qty = webnotes.conn.sql("""select sum(qty) from `tabDelivery Note Item` 
			where prevdoc_detail_docname = %s and docstatus = 1 
			and against_sales_order = %s 
			and parent != %s""", (so_detail, so, dn))
		return qty and flt(qty[0][0]) or 0.0

	def get_so_qty_and_warehouse(self, so_detail):
		so_item = webnotes.conn.sql("""select qty, reserved_warehouse from `tabSales Order Item`
			where name = %s and docstatus = 1""", so_detail, as_dict=1)
		so_qty = so_item and flt(so_item[0]["qty"]) or 0.0
		so_warehouse = so_item and so_item[0]["reserved_warehouse"] or ""
		return so_qty, so_warehouse
		
	def check_stop_sales_order(self, ref_fieldname):
		for d in self.doclist.get({"parentfield": self.fname}):
			if d.fields.get(ref_fieldname):
				status = webnotes.conn.get_value("Sales Order", d.fields[ref_fieldname], "status")
				if status == "Stopped":
					webnotes.throw(self.doc.doctype + 
						_(" can not be created/modified against stopped Sales Order ") + 
						d.fields[ref_fieldname])
		
def check_active_sales_items(obj):
	for d in obj.doclist.get({"parentfield": obj.fname}):
		if d.item_code:
			item = webnotes.conn.sql("""select docstatus, is_sales_item, 
				is_service_item, default_income_account from tabItem where name = %s""", 
				d.item_code, as_dict=True)[0]
			if item.is_sales_item == 'No' and item.is_service_item == 'No':
				webnotes.throw(_("Item is neither Sales nor Service Item") + ": " + d.item_code)
			if d.income_account and not item.default_income_account:
				webnotes.conn.set_value("Item", d.item_code, "default_income_account", 
					d.income_account)
