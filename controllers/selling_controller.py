# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, flt, comma_or, _round, add_days, cstr
from setup.utils import get_company_currency
from selling.utils import get_item_details
from webnotes import msgprint, _

from controllers.stock_controller import StockController

class SellingController(StockController):
	def onload_post_render(self):
		# contact, address, item details and pos details (if applicable)
		self.set_missing_values()
		
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

	def set_buying_amount(self, stock_ledger_entries = None):
		from stock.utils import get_buying_amount
		if not stock_ledger_entries:
			stock_ledger_entries = self.get_stock_ledger_entries()

		item_sales_bom = {}
		for d in self.doclist.get({"parentfield": "packing_details"}):
			new_d = webnotes._dict(d.fields.copy())
			new_d.total_qty = -1 * d.qty
			item_sales_bom.setdefault(d.parent_item, []).append(new_d)
		
		if stock_ledger_entries:
			for item in self.doclist.get({"parentfield": self.fname}):
				if item.item_code in self.stock_items or \
						(item_sales_bom and item_sales_bom.get(item.item_code)):
					buying_amount = get_buying_amount(item.item_code, self.doc.doctype, self.doc.name, item.name, 
						stock_ledger_entries.get((item.item_code, item.warehouse), []), 
						item_sales_bom)
					
					item.buying_amount = buying_amount >= 0.01 and buying_amount or 0
					webnotes.conn.set_value(item.doctype, item.name, "buying_amount", 
						item.buying_amount)
						
	def check_expense_account(self, item):
		if item.buying_amount and not item.expense_account:
			msgprint(_("""Expense account is mandatory for item: """) + item.item_code, 
				raise_exception=1)
				
		if item.buying_amount and not item.cost_center:
			msgprint(_("""Cost Center is mandatory for item: """) + item.item_code, 
				raise_exception=1)
				
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
				_("must be one of") + ": " + comma_or(valid_types),
				raise_exception=True)
				
	def update_serial_nos(self, cancel=False):
		from stock.doctype.stock_ledger_entry.stock_ledger_entry import update_serial_nos_after_submit, get_serial_nos
		update_serial_nos_after_submit(self, self.doc.doctype, self.fname)
		update_serial_nos_after_submit(self, self.doc.doctype, "packing_details")

		for table_fieldname in (self.fname, "packing_details"):
			for d in self.doclist.get({"parentfield": table_fieldname}):
				for serial_no in get_serial_nos(d.serial_no):
					sr = webnotes.bean("Serial No", serial_no)
					if cancel:
						sr.doc.status = "Available"
						for fieldname in ("warranty_expiry_date", "delivery_document_type", 
							"delivery_document_no", "delivery_date", "delivery_time", "customer", 
							"customer_name"):
							sr.doc.fields[fieldname] = None
					else:
						sr.doc.delivery_document_type = self.doc.doctype
						sr.doc.delivery_document_no = self.doc.name
						sr.doc.delivery_date = self.doc.posting_date
						sr.doc.delivery_time = self.doc.posting_time
						sr.doc.customer = self.doc.customer
						sr.doc.customer_name	= self.doc.customer_name
						if sr.doc.warranty_period:
							sr.doc.warranty_expiry_date = add_days(cstr(self.doc.posting_date), 
								cint(sr.doc.warranty_period))
						sr.doc.status =	'Delivered'

					sr.save()
