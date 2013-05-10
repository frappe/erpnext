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
from webnotes.utils import cint, flt
from setup.utils import get_company_currency
from webnotes import msgprint, _
import json

from controllers.stock_controller import StockController

class SellingController(StockController):
	def validate(self):
		super(SellingController, self).validate()
		self.set_total_in_words()
		
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
		
		self.determin_exclusive_rate()
		
		# TODO
		# code: save net_total_export on client side
		# print format: show net_total_export instead of net_total
		
		self.calculate_net_total()
		self.calculate_taxes()
		self.calculate_totals()
		# self.calculate_outstanding_amount()
		# 
		self._cleanup()
		
	def determin_exclusive_rate(self):
		if not any((cint(tax.included_in_print_rate) for tax in self.tax_doclist)):
			# no inclusive tax
			return
		
		for item in self.item_doclist:
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
			cumulated_tax_fraction = 0
			for i, tax in enumerate(self.tax_doclist):
				if cint(tax.included_in_print_rate):
					tax.tax_fraction_for_current_item = \
						self.get_current_tax_fraction(tax, item_tax_map)
				else:
					tax.tax_fraction_for_current_item = 0
					
				if i==0:
					tax.grand_total_fraction_for_current_item = 1 + \
						tax.tax_fraction_for_current_item
				else:
					tax.grand_total_fraction_for_current_item = \
						self.tax_doclist[i-1].grand_total_fraction_for_current_item \
						+ tax.tax_fraction_for_current_item
						
				cumulated_tax_fraction += tax.tax_fraction_for_current_item
			
			if cumulated_tax_fraction:
				item.basic_rate = flt((item.export_rate * self.doc.conversion_rate) / 
					(1 + cumulated_tax_fraction), self.precision_of("basic_rate", item.parentfield))
				
				item.amount = flt(item.basic_rate * item.qty, self.precision_of("amount", item.parentfield))
				
				item.base_ref_rate = flt(item.basic_rate / (1 - (item.adj_rate / 100.0)),
					self.precision_of("base_ref_rate", item.parentfield))
			
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
				self.precision_of(print_field, item.parentfield)) * self.doc.conversion_rate),
				self.precision_of(base_field, item.parentfield))

		for item in self.item_doclist:
			self.round_floats_in_doc(item, item.parentfield)
			
			if item.adj_rate == 100:
				item.ref_rate = item.ref_rate or item.export_rate
				item.export_rate = 0
			else:
				if item.ref_rate:
					item.export_rate = flt(item.ref_rate * (1.0 - (item.adj_rate / 100.0)),
						self.precision_of("export_rate", item.parentfield))
				else:
					# assume that print rate and discount are specified
					item.ref_rate = flt(item.export_rate / (1.0 - (item.adj_rate / 100.0)),
						self.precision_of("ref_rate", item.parentfield))
						
			item.export_amount = flt(item.export_rate * item.qty,
				self.precision_of("export_amount", item.parentfield))
				
			_set_base(item, "ref_rate", "base_ref_rate")
			_set_base(item, "export_rate", "basic_rate")
			_set_base(item, "export_amount", "amount")
	
	def initialize_taxes(self):
		for tax in self.tax_doclist:
			tax.tax_amount = tax.total = 0.0
			# temporary fields
			tax.tax_amount_for_current_item = tax.grand_total_for_current_item = 0.0
			tax.item_wise_tax_detail = {}
			self.validate_on_previous_row(tax)
			self.validate_inclusive_tax(tax)
			self.round_floats_in_doc(tax, tax.parentfield)
			
	def calculate_net_total(self):
		self.doc.net_total = 0
		self.doc.net_total_export = 0

		for item in self.item_doclist:
			self.doc.net_total += item.amount
			self.doc.net_total_export += item.export_amount
			
		self.doc.net_total = flt(self.doc.net_total, self.precision_of("net_total"))
		self.doc.net_total_export = flt(self.doc.net_total_export,
			self.precision_of("net_total_export"))
		
	def calculate_taxes(self):
		for item in self.item_doclist:
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)

			for i, tax in enumerate(self.tax_doclist):
				# tax_amount represents the amount of tax for the current step
				current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)

				# case when net total is 0 but there is an actual type charge
				# in this case add the actual amount to tax.tax_amount
				# and tax.grand_total_for_current_item for the first such iteration
				if not (current_tax_amount or self.doc.net_total or tax.tax_amount) and \
						tax.charge_type=="Actual":
					zero_net_total_adjustment = flt(tax.rate, self.precision_of("tax_amount", tax.parentfield))
					current_tax_amount += zero_net_total_adjustment

				# store tax_amount for current item as it will be used for
				# charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount

				# accumulate tax amount into tax.tax_amount
				tax.tax_amount += tax.tax_amount_for_current_item
				
				# Calculate tax.total viz. grand total till that step
				# note: grand_total_for_current_item contains the contribution of 
				# item's amount, previously applied tax and the current tax on that item
				if i==0:
					tax.grand_total_for_current_item = flt(item.amount +
						current_tax_amount, self.precision_of("total", tax.parentfield))
						
				else:
					tax.grand_total_for_current_item = \
						flt(self.tax_doclist[i-1].grand_total_for_current_item +
							current_tax_amount, self.precision_of("total", tax.parentfield))
							
				# in tax.total, accumulate grand total of each item
				tax.total += tax.grand_total_for_current_item

				# store tax_breakup for each item
				# DOUBT: should valuation type amount also be stored?
				tax.item_wise_tax_detail[item.item_code] = current_tax_amount
				
	def calculate_totals(self):
		self.doc.grand_total = flt(self.tax_doclist and \
			self.tax_doclist[-1].total or self.doc.net_total, self.precision_of("grand_total"))
		self.doc.grand_total_export = flt(self.doc.grand_total / self.doc.conversion_rate, 
			self.precision_of("grand_total_export"))
		
		self.doc.rounded_total = round(self.doc.grand_total)
		self.doc.rounded_total_export = round(self.doc.grand_total_export)
	
	def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.rate, self.precision_of("tax_amount", tax.parentfield))
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

		return flt(current_tax_amount, self.precision_of("tax_amount", tax.parentfield))
	
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
					"taxes_doctype": tax.parenttype,
					"row_id_label": self.meta.get_label("row_id",
						parentfield="other_charges")
				}, raise_exception=True)
				
	def validate_inclusive_tax(self, tax):
		def _on_previous_row_error(tax, row_range):
			msgprint((_("Row") 
				+ " # %(idx)s [%(taxes_doctype)s] [%(charge_type_label)s = \"%(charge_type)s\"]: " 
				+ _("If:") + ' "%(inclusive_label)s" = ' + _("checked") + ", "
				+ _("then it is required that:") + " [" + _("Row") + " # %(row_range)s] "
				+ '"%(inclusive_label)s" = ' + _("checked")) % {
					"idx": tax.idx,
					"taxes_doctype": tax.doctype,
					"inclusive_label": self.meta.get_label("included_in_print_rate",
						parentfield="other_charges"),
					"charge_type_label": self.meta.get_label("charge_type",
						parentfield="other_charges"),
					"charge_type": tax.charge_type,
					"row_range": row_range
				}, raise_exception=True)
		
		if cint(tax.included_in_print_rate):
			if tax.charge_type == "Actual":
				# inclusive cannot be of type Actual
				msgprint((_("Row") 
					+ " # %(idx)s [%(taxes_doctype)s]: %(charge_type_label)s = \"%(charge_type)s\" " 
					+ "cannot be included in Item's rate") % {
						"idx": tax.idx,
						"taxes_doctype": tax.doctype,
						"charge_type_label": self.meta.get_label("charge_type",
							parentfield="other_charges"),
						"charge_type": tax.charge_type,
					}, raise_exception=True)
			elif tax.charge_type == "On Previous Row Amount" and \
					not cint(self.tax_doclist[tax.row_id - 1].included_in_print_rate):
				# referred row should also be inclusive
				_on_previous_row_error(tax, tax.row_id)
			elif tax.charge_type == "On Previous Row Total" and \
					not all([cint(t.included_in_print_rate) for t in self.tax_doclist[:tax.idx - 1]]):
				# all rows about this tax should be inclusive
				_on_previous_row_error(tax, "1 - %d" % (tax.idx - 1,))
				
	def _load_item_tax_rate(self, item_tax_rate):
		if not item_tax_rate:
			return {}
		return json.loads(item_tax_rate)
		
	def _get_tax_rate(self, tax, item_tax_map):
		if item_tax_map.has_key(tax.account_head):
			return flt(item_tax_map.get(tax.account_head), self.precision_of("rate", tax.parentfield))
		else:
			return tax.rate
				
	def _cleanup(self):
		for tax in self.tax_doclist:
			del tax.fields["grand_total_for_current_item"]
			del tax.fields["tax_amount_for_current_item"]
			
			for fieldname in ("tax_fraction_for_current_item", 
				"grand_total_fraction_for_current_item"):
				if fieldname in tax.fields:
					del tax.fields[fieldname]
			
			tax.item_wise_tax_detail = json.dumps(tax.item_wise_tax_detail)
