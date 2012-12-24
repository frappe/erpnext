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
import webnotes.model
from webnotes import _, msgprint
from webnotes.utils import cint, flt
from webnotes.model.utils import round_floats_in_doc
import json

from controllers.transaction_controller import TransactionController

class TaxController(TransactionController):
	def append_taxes(self):
		"""append taxes as per tax master link field"""
		# clear tax table
		self.doclist = self.doclist.get({"parentfield": ["!=",
			self.fmap.taxes_and_charges]})
		
		tax_master_doctype = self.meta.get_options(self.fmap.taxes_and_charges_master)
		master_tax_list = webnotes.get_doclist(tax_master_doctype,
			self.doc.fields.get(self.fmap.taxes_and_charges_master)).get(
			{"parentfield": self.fmap.taxes_and_charges})
			
		for base_tax in master_tax_list:
			tax = _dict([[field, base_tax.fields.get(field)]
				for field in base_tax.fields
				if field not in webnotes.model.default_fields])
			tax.update({
				"doctype": self.meta.get_options(self.fmap.taxes_and_charges),
				"parentfield": self.fmap.taxes_and_charges,
				"rate": flt(tax.rate, self.precision.tax.rate),
			})
			self.doclist.append(tax)
	
	def calculate_taxes_and_totals(self):
		"""
			Calculates:
				* amount for each item
				* valuation_tax_amount for each item, 
				* tax amount and tax total for each tax
				* net total
				* total taxes
				* grand total
		"""
		self.doc.fields[self.fmap.exchange_rate] = \
			flt(self.doc.fields.get(self.fmap.exchange_rate),
			self.precision.main[self.fmap.exchange_rate])
		
		self.calculate_item_values()
		
		self.initialize_taxes()
		if self.meta.get_field("included_in_print_rate",
				parentfield=self.fmap.taxes_and_charges):
			self.determine_exclusive_rate()
		
		self.calculate_net_total()
		self.calculate_taxes()
		self.calculate_totals()
		self.set_amount_in_words()
		self.cleanup()
		
	def calculate_item_values(self):
		def _set_base(item, print_field, base_field):
			"""set values in base currency"""
			item.fields[base_field] = flt((flt(item.fields[print_field],
				self.precision.item[print_field]) * \
				self.doc.fields.get(self.fmap.exchange_rate)),
				self.precision.item[base_field])
		
		for item in self.item_doclist:
			round_floats_in_doc(item, self.precision.item)
			
			if item.fields.get(self.fmap.discount) == 100:
				if not item.fields.get(self.fmap.print_ref_rate):
					item.fields[self.fmap.print_ref_rate] = \
						item.fields.get(self.fmap.print_rate)
				item.fields[self.fmap.print_rate] = 0
			else:
				if item.fields.get(self.fmap.print_ref_rate):
					item.fields[self.fmap.print_rate] = \
						flt(item.fields.get(self.fmap.print_ref_rate) *
						(1.0 - (item.fields.get(self.fmap.discount) / 100.0)),
						self.precision.item[self.fmap.print_rate])
				else:
					# assume that print rate and discount are specified
					item.fields[self.fmap.print_ref_rate] = \
						flt(item.fields.get(self.fmap.print_rate) / 
						(1.0 - (item.fields.get(self.fmap.discount) / 100.0)),
						self.precision.item[self.fmap.print_ref_rate])
						
			item.fields[self.fmap.print_amount] = \
				flt(item.fields.get(self.fmap.print_rate) * \
				item.fields.get("qty"),
				self.precision.item[self.fmap.print_amount])
				
			_set_base(item, self.fmap.print_ref_rate, self.fmap.ref_rate)
			_set_base(item, self.fmap.print_rate, self.fmap.rate)
			_set_base(item, self.fmap.print_amount, "amount")
			
	def initialize_taxes(self):
		for tax in self.tax_doclist:
			# initialize totals to 0
			tax.tax_amount = tax.total = tax.total_print = 0
			tax.grand_total_for_current_item = tax.tax_amount_for_current_item = 0
			
			# for actual type, user can mention actual tax amount in tax.tax_amount_print
			if tax.charge_type != "Actual" or tax.rate:
				tax.tax_amount_print = 0
			
			self.validate_on_previous_row(tax)
			self.validate_included_tax(tax)
			
			# round relevant values
			round_floats_in_doc(tax, self.precision.tax)
			
	def calculate_net_total(self):
		self.doc.net_total = 0
		self.doc.fields[self.fmap.net_total_print] = 0
		
		for item in self.item_doclist:
			self.doc.net_total += item.amount
			self.doc.fields[self.fmap.net_total_print] += \
				item.fields.get(self.fmap.print_amount)
				
		self.doc.net_total = flt(self.doc.net_total, self.precision.main.net_total)
		self.doc.fields[self.fmap.net_total_print] = \
			flt(self.doc.fields.get(self.fmap.net_total_print),
			self.precision.main.get(self.fmap.net_total_print))
			
	def calculate_taxes(self):
		for item in self.item_doclist:
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
			item.fields[self.fmap.valuation_tax_amount] = 0
			
			for i, tax in enumerate(self.tax_doclist):
				# tax_amount represents the amount of tax for the current step
				current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)
				
				if hasattr(self, "set_valuation_tax_amount"):
					self.set_valuation_tax_amount(item, tax, current_tax_amount)
				
				# case when net total is 0 but there is an actual type charge
				# in this case add the actual amount to tax.tax_amount
				# and tax.grand_total_for_current_item for the first such iteration
				if not (current_tax_amount or self.doc.net_total or tax.tax_amount) and \
						tax.charge_type=="Actual":
					zero_net_total_adjustment = flt((tax.tax_amount_print * 
						self.doc.fields.get(self.fmap.exchange_rate)) or tax.rate, 
						self.precision.tax.tax_amount)
					current_tax_amount += zero_net_total_adjustment
				
				# store tax_amount for current item as it will be used for
				# charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount
				
				# accumulate tax amount into tax.tax_amount
				tax.tax_amount += tax.tax_amount_for_current_item
				
				# accumulate tax_amount_print only if tax is not included
				# and if tax amount of actual type is entered in 'rate' field
				if not cint(tax.included_in_print_rate) and (tax.charge_type != "Actual"
						or tax.rate):
					tax.tax_amount_print += flt((tax.tax_amount_for_current_item /
						self.doc.fields.get(self.fmap.exchange_rate)),
						self.precision.tax.tax_amount_print)
				
				if tax.category == "Valuation":
					# if just for valuation, do not add the tax amount in total
					# hence, setting it as 0 for further steps
					current_tax_amount = 0
				
				# Calculate tax.total viz. grand total till that step
				# note: grand_total_for_current_item contains the contribution of 
				# item's amount, previously applied tax and the current tax on that item
				if i==0:
					tax.grand_total_for_current_item = flt(item.amount +
						current_tax_amount, self.precision.tax.total)
					
					# if inclusive pricing, current_tax_amount should not be considered
					if cint(tax.included_in_print_rate):
						current_tax_amount = 0
						
					tax.grand_total_print_for_current_item = \
						flt(item.fields.get(self.fmap.print_amount) +
						(current_tax_amount / self.doc.fields.get(
							self.fmap.exchange_rate)),
						self.precision.tax.total_print)
				else:
					tax.grand_total_for_current_item = \
						flt(self.tax_doclist[i-1].grand_total_for_current_item +
							current_tax_amount, self.precision.tax.total)
					
					# if inclusive pricing, current_tax_amount should not be considered
					if cint(tax.included_in_print_rate):
						current_tax_amount = 0
					
					tax.grand_total_print_for_current_item = \
						flt(self.tax_doclist[i-1].grand_total_print_for_current_item +
							(current_tax_amount / self.doc.fields.get(
								self.fmap.exchange_rate)),
							self.precision.tax.total_print)

				# in tax.total, accumulate grand total of each item
				tax.total += tax.grand_total_for_current_item
				tax.total_print += tax.grand_total_print_for_current_item
				
				# TODO store tax_breakup for each item
				
	def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.rate or (tax.tax_amount_print * \
				self.doc.fields.get(self.fmap.exchange_rate)),
				self.precision.tax.tax_amount)
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

		return flt(current_tax_amount, self.precision.tax.tax_amount)
		
	def calculate_totals(self):
		if self.tax_doclist:
			self.doc.grand_total = flt(self.tax_doclist[-1].total,
				self.precision.main.grand_total)
			self.doc.fields[self.fmap.grand_total_print] = \
				flt(self.tax_doclist[-1].total_print,
				self.precision.main[self.fmap.grand_total_print])
		else:
			self.doc.grand_total = flt(self.doc.net_total,
				self.precision.main.grand_total)
			self.doc.fields[self.fmap.grand_total_print] = \
				flt(self.doc.fields.get(self.fmap.net_total_print),
				self.precision.main[self.fmap.grand_total_print])
		
		self.doc.fields[self.fmap.taxes_and_charges_total] = \
			flt(self.doc.grand_total - self.doc.net_total,
			self.precision.main[self.fmap.taxes_and_charges_total])
			
		self.doc.taxes_and_charges_total_print = \
			flt(self.doc.fields.get(self.fmap.grand_total_print) - \
			self.doc.fields.get(self.fmap.net_total_print),
			self.precision.main.taxes_and_charges_total_print)
		
		self.doc.rounded_total = round(self.doc.grand_total)
		self.doc.fields[self.fmap.rounded_total_print] = \
			round(self.doc.fields.get(self.fmap.grand_total_print))
			
	def set_amount_in_words(self):
		from webnotes.utils import money_in_words
		base_currency = webnotes.conn.get_value("Company", self.doc.currency,
			"default_currency")
		
		self.doc.fields[self.fmap.grand_total_in_words] = \
			money_in_words(self.doc.grand_total, base_currency)
		self.doc.fields[self.fmap.rounded_total_in_words] = \
			money_in_words(self.doc.rounded_total, base_currency)
		
		self.doc.fields[self.fmap.grand_total_in_words_print] = \
			money_in_words(self.doc.fields.get(self.fmap.grand_total_print),
			self.doc.currency)
		self.doc.fields[self.fmap.rounded_total_in_words_print] = \
			money_in_words(self.doc.fields.get(self.fmap.rounded_total_print),
			self.doc.currency)
			
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
						parentfield=self.fmap.taxes_and_charges)
				}, raise_exception=True)
	
	def validate_included_tax(self, tax):
		"""
			validate conditions related to "Is this Tax Included in Rate?"
		"""
		def _on_previous_row_error(tax, row_range):
			msgprint((_("Row") + " # %(idx)s [%(taxes_doctype)s]: " + \
				_("If") + " '%(inclusive_label)s' " + _("is checked for") + \
				" '%(charge_type_label)s' = '%(charge_type)s', " + _("then") + " " + \
				_("Row") + " # %(row_range)s " + _("should also have") + \
				" '%(inclusive_label)s' = " + _("checked")) % {
					"idx": tax.idx,
					"taxes_doctype": tax.doctype,
					"inclusive_label": self.meta.get_label("included_in_print_rate",
						parentfield=self.fmap.taxes_and_charges),
					"charge_type_label": self.meta.get_label("charge_type",
						parentfield=self.fmap.taxes_and_charges),
					"charge_type": tax.charge_type,
					"row_range": row_range,
				}, raise_exception=True)
		
		if cint(tax.included_in_print_rate):
			if tax.charge_type == "Actual":
				# now inclusive rate for type 'Actual'
				msgprint((_("Row") + " # %(idx)s [%(taxes_doctype)s]: " + \
					"'%(charge_type_label)s' = '%(charge_type)s' " + \
					_("cannot be included in item's rate")) % {
						"idx": tax.idx,
						"taxes_doctype": self.meta.get_options(
							self.fmap.taxes_and_charges),
						"charge_type_label": self.meta.get_label("charge_type",
							parentfield=self.fmap.taxes_and_charges),
						"charge_type": tax.charge_type,
					}, raise_exception=True)
					
			elif tax.charge_type == "On Previous Row Amount" and \
					not cint(self.tax_doclist[cint(tax.row_id) - 1]\
						.included_in_print_rate):
				# for an inclusive tax of type "On Previous Row Amount",
				# dependent row should also be inclusive
				_on_previous_row_error(tax, tax.row_id)
				
			elif tax.charge_type == "On Previous Row Total" and \
					not all([cint(t.included_in_print_rate) \
						for t in self.tax_doclist[:tax.idx - 1]]):
				# for an inclusive tax of type "On Previous Row Total", 
				# all rows above it should also be inclusive
				_on_previous_row_error(tax, "1 - %d" % (tax.idx - 1))
		
	def determine_exclusive_rate(self):
		if not any((cint(tax.included_in_print_rate) for tax in self.tax_doclist)):
			# if no tax is marked as included in print rate, no need to proceed further
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
				item.fields[self.fmap.rate] = \
					flt((item.fields.get(self.fmap.print_rate) * \
					self.doc.fields.get(self.fmap.exchange_rate)) / 
					(1 + cumulated_tax_fraction), self.precision.item[self.fmap.rate])
				
				item.amount = flt(item.fields.get(self.fmap.rate) * item.qty,
					self.precision.item.amount)
				
				item.fields[self.fmap.ref_rate] = \
					flt(item.fields.get(self.fmap.rate) / (1 - \
					(item.fields.get(self.fmap.discount) / 100.0)),
					self.precision.item[self.fmap.ref_rate])
		
				# print item.print_rate, 1+cumulated_tax_fraction, item.rate, item.amount
				# print "-"*10

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
					self.tax_doclist[cint(tax.row_id) - 1]\
						.tax_fraction_for_current_item
			
			elif tax.charge_type == "On Previous Row Total":
				current_tax_fraction = (tax_rate / 100.0) * \
					self.tax_doclist[cint(tax.row_id) - 1]\
						.grand_total_fraction_for_current_item
						
			# print tax.account_head, tax_rate, current_tax_fraction

		return current_tax_fraction
	
	def _load_item_tax_rate(self, item_tax_rate):
		if not item_tax_rate:
			return {}

		return json.loads(item_tax_rate)
		
	def _get_tax_rate(self, tax, item_tax_map):
		if item_tax_map.has_key(tax.account_head):
			return flt(item_tax_map.get(tax.account_head), self.precision.tax.rate)
		else:
			return tax.rate
			
	def cleanup(self):
		def _del(f, doc):
			if f in doc.fields:
				del doc.fields[f]
			elif self.fmap.get(f) and self.fmap.get(f) in doc.fields:
				del doc.fields[self.fmap.get(f)]
		
		for f in ["taxes_and_charges_total_print", "rounded_total_in_words_print",
				"rounded_total_print", "rounded_total_in_words", "rounded_total"]:
			_del(f, self.doc)
		
		for f in ["grand_total_print_for_current_item", "tax_amount_print",
				"grand_total_for_current_item", "tax_amount_for_current_item",
				"total_print"]:
			for doc in self.doclist.get({"parentfield": self.fmap.taxes_and_charges}):
				_del(f, doc)
			
		for f in ["item_tax_amount"]:
			for doc in self.doclist.get({"parentfield": self.item_table_field}):
				_del(f, doc)
				
