# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, flt, comma_or
from setup.utils import get_company_currency
from webnotes import msgprint, _
import json

from controllers.stock_controller import StockController

class SellingController(StockController):
	def onload_post_render(self):
		self.set_price_list_currency()

		# contact, address, item details and pos details (if applicable)
		self.set_missing_values()
		
		if self.meta.get_field("other_charges"):
			self.set_taxes()
			
	def validate(self):
		super(SellingController, self).validate()
		# self.calculate_taxes_and_totals()
		self.set_total_in_words()
		self.set_missing_values(for_validate=True)
		
	def set_price_list_currency(self):
		if self.doc.price_list_name and not self.doc.price_list_currency:
			# TODO - change this, since price list now has only one currency allowed
			from setup.utils import get_price_list_currency
			self.doc.fields.update(get_price_list_currency(
				{"price_list_name": self.doc.price_list_name, "use_for": "selling"}))
		
	def set_missing_values(self, for_validate=False):
		# set contact and address details for customer, if they are not mentioned
		if self.doc.customer and not (self.doc.contact_person and self.doc.customer_address):
			for fieldname, val in self.get_default_address_and_contact("customer").items():
				if not self.doc.fields.get(fieldname) and self.meta.get_field(fieldname):
					self.doc.fields[fieldname] = val
					
		# set missing item values
		from selling.utils import get_item_details
		for item in self.doclist.get({"parentfield": "entries"}):
			if item.fields.get("item_code"):
				ret = get_item_details(item.fields)
				for fieldname, value in ret.items():
					if self.meta.get_field(fieldname, parentfield="entries") and \
						not item.fields.get(fieldname):
							item.fields[fieldname] = value
							
	def set_taxes(self):
		if not self.doclist.get({"parentfield": "other_charges"}):
			if not self.doc.charge:
				# get the default tax master
				self.doc.charge = webnotes.conn.get_value("Sales Taxes and Charges Master",
					{"is_default": 1})
			
			if self.doc.charge:
				from webnotes.model import default_fields
				tax_master = webnotes.bean("Sales Taxes and Charges Master", self.doc.charge)
				for i, tax in enumerate(tax_master.doclist.get({"parentfield": "other_charges"})):
					for fieldname in default_fields:
						tax.fields[fieldname] = None
					
					tax.fields.update({
						"doctype": "Sales Taxes and Charges",
						"parentfield": "other_charges",
						"idx": i+1
					})
					
					self.doclist.append(tax)
					
	def get_other_charges(self):
		self.doclist = self.doc.clear_table(self.doclist, "other_charges")
		self.set_taxes()
		
	def set_customer_defaults(self):
		self.get_default_customer_address()
		
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
					buying_amount = get_buying_amount(item.item_code, item.warehouse, -1*item.qty, 
						self.doc.doctype, self.doc.name, item.name, stock_ledger_entries, 
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
		self.doc.conversion_rate = flt(self.doc.conversion_rate)
		self.item_doclist = self.doclist.get({"parentfield": self.fname})
		self.tax_doclist = self.doclist.get({"parentfield": "other_charges"})
		
		self.calculate_item_values()
		self.initialize_taxes()
		self.determine_exclusive_rate()
		self.calculate_net_total()
		self.calculate_taxes()
		self.calculate_totals()
		self.calculate_commission()
		self.calculate_contribution()
		# self.calculate_outstanding_amount()
		self._cleanup()
		
		# TODO
		# print format: show net_total_export instead of net_total
		
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
				item.basic_rate = flt((item.export_rate * self.doc.conversion_rate) / 
					(1 + cumulated_tax_fraction), self.precision("basic_rate", item))
				
				item.amount = flt(item.basic_rate * item.qty, self.precision("amount", item))
				
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
		def _set_base(item, print_field, base_field):
			"""set values in base currency"""
			item.fields[base_field] = flt((flt(item.fields[print_field],
				self.precision(print_field, item)) * self.doc.conversion_rate),
				self.precision(base_field, item))

		for item in self.item_doclist:
			self.round_floats_in(item)
			
			if item.adj_rate == 100:
				item.ref_rate = item.ref_rate or item.export_rate
				item.export_rate = 0
			else:
				if item.ref_rate:
					item.export_rate = flt(item.ref_rate * (1.0 - (item.adj_rate / 100.0)),
						self.precision("export_rate", item))
				else:
					# assume that print rate and discount are specified
					item.ref_rate = flt(item.export_rate / (1.0 - (item.adj_rate / 100.0)),
						self.precision("ref_rate", item))
						
			item.export_amount = flt(item.export_rate * item.qty,
				self.precision("export_amount", item))
				
			_set_base(item, "ref_rate", "base_ref_rate")
			_set_base(item, "export_rate", "basic_rate")
			_set_base(item, "export_amount", "amount")
	
	def initialize_taxes(self):
		for tax in self.tax_doclist:
			tax.tax_amount = tax.total = 0.0
			tax.item_wise_tax_detail = {}

			# temporary fields
			tax.tax_amount_for_current_item = tax.grand_total_for_current_item = 0.0
			
			self.validate_on_previous_row(tax)
			self.validate_inclusive_tax(tax)
			self.round_floats_in(tax)
			
	def calculate_net_total(self):
		self.doc.net_total = self.doc.net_total_export = 0.0

		for item in self.item_doclist:
			self.doc.net_total += item.amount
			self.doc.net_total_export += item.export_amount
		
		self.round_floats_in(self.doc, ["net_total", "net_total_export"])
		
	def calculate_taxes(self):
		for item in self.item_doclist:
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)

			for i, tax in enumerate(self.tax_doclist):
				# tax_amount represents the amount of tax for the current step
				current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)

				# case when net total is 0 but there is an actual type charge
				# in this case add the actual amount to tax.tax_amount
				# and tax.grand_total_for_current_item for the first such iteration
				if tax.charge_type=="Actual" and \
						not (current_tax_amount or self.doc.net_total or tax.tax_amount):
					zero_net_total_adjustment = flt(tax.rate, self.precision("tax_amount", tax))
					current_tax_amount += zero_net_total_adjustment

				# store tax_amount for current item as it will be used for
				# charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount

				# accumulate tax amount into tax.tax_amount
				tax.tax_amount += current_tax_amount
				
				# Calculate tax.total viz. grand total till that step
				# note: grand_total_for_current_item contains the contribution of 
				# item's amount, previously applied tax and the current tax on that item
				if i==0:
					tax.grand_total_for_current_item = flt(item.amount +
						current_tax_amount, self.precision("total", tax))
						
				else:
					tax.grand_total_for_current_item = \
						flt(self.tax_doclist[i-1].grand_total_for_current_item +
							current_tax_amount, self.precision("total", tax))
							
				# in tax.total, accumulate grand total of each item
				tax.total += tax.grand_total_for_current_item

				# store tax breakup for each item
				tax.item_wise_tax_detail[item.item_code] = current_tax_amount
				
	def calculate_totals(self):
		self.doc.grand_total = flt(self.tax_doclist and \
			self.tax_doclist[-1].total or self.doc.net_total, self.precision("grand_total"))
		self.doc.grand_total_export = flt(self.doc.grand_total / self.doc.conversion_rate, 
			self.precision("grand_total_export"))
			
		self.doc.other_charges_total = flt(self.doc.grand_total - self.doc.net_total,
			self.precision("other_charges_total"))
		self.doc.other_charges_total_export = flt(self.doc.grand_total_export - self.doc.net_total_export,
			self.precision("other_charges_total_export"))
		
		self.doc.rounded_total = round(self.doc.grand_total)
		self.doc.rounded_total_export = round(self.doc.grand_total_export)
	
	def calculate_commission(self):
		if self.doc.commission_rate > 100:
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
	
	def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)
		current_tax_amount = 0.0

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.rate, self.precision("tax_amount", tax))
			current_tax_amount = (self.doc.net_total
				and ((item.amount / self.doc.net_total) * actual)
				or 0)
		elif tax.charge_type == "On Net Total":
			current_tax_amount = (tax_rate / 100.0) * item.amount
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * \
				self.tax_doclist[cint(tax.row_id) - 1].tax_amount_for_current_item
		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * \
				self.tax_doclist[cint(tax.row_id) - 1].grand_total_for_current_item

		return flt(current_tax_amount, self.precision("tax_amount", tax))
	
	def validate_on_previous_row(self, tax):
		"""
			validate if a valid row id is mentioned in case of
			On Previous Row Amount and On Previous Row Total
		"""
		if tax.charge_type in ["On Previous Row Amount", "On Previous Row Total"] and \
				(not tax.row_id or cint(tax.row_id) >= tax.idx):
			msgprint((_("Row") + " # %(idx)s [%(taxes_doctype)s]: " + \
				_("Please specify a valid") + " %(row_id_label)s") % {
					"idx": tax.idx,
					"taxes_doctype": tax.doctype,
					"row_id_label": self.meta.get_label("row_id",
						parentfield="other_charges")
				}, raise_exception=True)
				
	def validate_inclusive_tax(self, tax):
		def _on_previous_row_error(row_range):
			msgprint((_("Row") + " # %(idx)s [%(doctype)s]: " +
				_("to be included in Item's rate, it is required that: ") +
				" [" + _("Row") + " # %(row_range)s] " + _("also be included in Item's rate")) % {
					"idx": tax.idx,
					"doctype": tax.doctype,
					"inclusive_label": self.meta.get_label("included_in_print_rate",
						parentfield="other_charges"),
					"charge_type_label": self.meta.get_label("charge_type",
						parentfield="other_charges"),
					"charge_type": tax.charge_type,
					"row_range": row_range
				}, raise_exception=True)
		
		if cint(tax.included_in_print_rate):
			if tax.charge_type == "Actual":
				# inclusive tax cannot be of type Actual
				msgprint((_("Row") 
					+ " # %(idx)s [%(doctype)s]: %(charge_type_label)s = \"%(charge_type)s\" " 
					+ "cannot be included in Item's rate") % {
						"idx": tax.idx,
						"doctype": tax.doctype,
						"charge_type_label": self.meta.get_label("charge_type",
							parentfield="other_charges"),
						"charge_type": tax.charge_type,
					}, raise_exception=True)
			elif tax.charge_type == "On Previous Row Amount" and \
					not cint(self.tax_doclist[tax.row_id - 1].included_in_print_rate):
				# referred row should also be inclusive
				_on_previous_row_error(tax.row_id)
			elif tax.charge_type == "On Previous Row Total" and \
					not all([cint(t.included_in_print_rate) for t in self.tax_doclist[:tax.row_id - 1]]):
				# all rows about the reffered tax should be inclusive
				_on_previous_row_error("1 - %d" % (tax.row_id,))
				
	def _load_item_tax_rate(self, item_tax_rate):
		return json.loads(item_tax_rate) if item_tax_rate else {}
		
	def _get_tax_rate(self, tax, item_tax_map):
		if item_tax_map.has_key(tax.account_head):
			return flt(item_tax_map.get(tax.account_head), self.precision("rate", tax))
		else:
			return tax.rate
				
	def _cleanup(self):
		for tax in self.tax_doclist:
			for fieldname in ("grand_total_for_current_item",
				"tax_amount_for_current_item",
				"tax_fraction_for_current_item", 
				"grand_total_fraction_for_current_item"):
				if fieldname in tax.fields:
					del tax.fields[fieldname]
			
			tax.item_wise_tax_detail = json.dumps(tax.item_wise_tax_detail)
			
	def validate_order_type(self):
		valid_types = ["Sales", "Maintenance"]
		if self.doc.order_type not in valid_types:
			msgprint(_(self.meta.get_label("order_type")) + " " + 
				_("must be one of") + ": " + comma_or(valid_types),
				raise_exception=True)
