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
from webnotes import _, msgprint
from webnotes.utils import flt, cint, today
from setup.utils import get_company_currency, get_price_list_currency
from accounts.utils import get_fiscal_year, validate_fiscal_year
from utilities.transaction_base import TransactionBase, validate_conversion_rate
import json

class AccountsController(TransactionBase):
	def validate(self):
		self.set_missing_values(for_validate=True)
		
		self.validate_date_with_fiscal_year()
		
		if self.meta.get_field("currency"):
			self.calculate_taxes_and_totals()
			self.validate_value("grand_total", ">=", 0)
			self.set_total_in_words()
			
	def set_missing_values(self, for_validate=False):
		for fieldname in ["posting_date", "transaction_date"]:
			if not self.doc.fields.get(fieldname) and self.meta.get_field(fieldname):
				self.doc.fields[fieldname] = today()
				if not self.doc.fiscal_year:
					self.doc.fiscal_year = get_fiscal_year(self.doc.fields[fieldname])[0]
					
	def validate_date_with_fiscal_year(self):
		if self.meta.get_field("fiscal_year") :
			date_field = ""
			if self.meta.get_field("posting_date"):
				date_field = "posting_date"
			elif self.meta.get_field("transaction_date"):
				date_field = "transaction_date"
				
			if date_field and self.doc.fields[date_field]:
				validate_fiscal_year(self.doc.fields[date_field], self.doc.fiscal_year, 
					label=self.meta.get_label(date_field))
			
	def set_price_list_currency(self, buying_or_selling):
		# TODO - change this, since price list now has only one currency allowed
		if self.meta.get_field("price_list_name") and self.doc.price_list_name and \
			not self.doc.price_list_currency:
				self.doc.fields.update(get_price_list_currency(self.doc.price_list_name))
				
				if self.doc.price_list_currency:
					if not self.doc.plc_conversion_rate:
						company_currency = get_company_currency(self.doc.company)
						if self.doc.price_list_currency == company_currency:
							self.doc.plc_conversion_rate = 1.0
						else:
							exchange = self.doc.price_list_currency + "-" + company_currency
							self.doc.plc_conversion_rate = flt(webnotes.conn.get_value("Currency Exchange",
								exchange, "exchange_rate"))
						
					if not self.doc.currency:
						self.doc.currency = self.doc.price_list_currency
						self.doc.conversion_rate = self.doc.plc_conversion_rate
						
	def set_missing_item_details(self, get_item_details):
		"""set missing item values"""
		for item in self.doclist.get({"parentfield": self.fname}):
			if item.fields.get("item_code"):
				args = item.fields.copy().update(self.doc.fields)
				ret = get_item_details(args)
				for fieldname, value in ret.items():
					if self.meta.get_field(fieldname, parentfield=self.fname) and \
						item.fields.get(fieldname) is None and value is not None:
							item.fields[fieldname] = value
							
	def set_taxes(self, tax_parentfield, tax_master_field):
		if not self.meta.get_field(tax_parentfield):
			return
			
		tax_master_doctype = self.meta.get_field(tax_master_field).options
			
		if not self.doclist.get({"parentfield": tax_parentfield}):
			if not self.doc.fields.get(tax_master_field):
				# get the default tax master
				self.doc.fields[tax_master_field] = \
					webnotes.conn.get_value(tax_master_doctype, {"is_default": 1})
					
			self.append_taxes_from_master(tax_parentfield, tax_master_field, tax_master_doctype)
				
	def append_taxes_from_master(self, tax_parentfield, tax_master_field, tax_master_doctype=None):
		if self.doc.fields.get(tax_master_field):
			if not tax_master_doctype:
				tax_master_doctype = self.meta.get_field(tax_master_field).options
			
			tax_doctype = self.meta.get_field(tax_parentfield).options
			
			from webnotes.model import default_fields
			tax_master = webnotes.bean(tax_master_doctype, self.doc.fields.get(tax_master_field))
			
			for i, tax in enumerate(tax_master.doclist.get({"parentfield": tax_parentfield})):
				for fieldname in default_fields:
					tax.fields[fieldname] = None
				
				tax.fields.update({
					"doctype": tax_doctype,
					"parentfield": tax_parentfield,
					"idx": i+1
				})
				
				self.doclist.append(tax)
					
	def calculate_taxes_and_totals(self):
		# validate conversion rate
		if not self.doc.currency:
			self.doc.currency = get_company_currency(self.doc.company)
			self.doc.conversion_rate = 1.0
		else:
			validate_conversion_rate(self.doc.currency, self.doc.conversion_rate,
				self.meta.get_label("conversion_rate"), self.doc.company)
		
		self.doc.conversion_rate = flt(self.doc.conversion_rate)
		self.item_doclist = self.doclist.get({"parentfield": self.fname})
		self.tax_doclist = self.doclist.get({"parentfield": self.other_fname})
		
		self.calculate_item_values()
		self.initialize_taxes()
		
		if hasattr(self, "determine_exclusive_rate"):
			self.determine_exclusive_rate()
		
		self.calculate_net_total()
		self.calculate_taxes()
		self.calculate_totals()
		self._cleanup()
		
		# TODO
		# print format: show net_total_export instead of net_total
		
	def initialize_taxes(self):
		for tax in self.tax_doclist:
			tax.item_wise_tax_detail = {}
			for fieldname in ["tax_amount", "total", 
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]:
					tax.fields[fieldname] = 0.0
			
			self.validate_on_previous_row(tax)
			self.validate_inclusive_tax(tax)
			self.round_floats_in(tax)
			
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
						parentfield=self.other_fname)
				}, raise_exception=True)
				
	def validate_inclusive_tax(self, tax):
		def _on_previous_row_error(row_range):
			msgprint((_("Row") + " # %(idx)s [%(doctype)s]: " +
				_("to be included in Item's rate, it is required that: ") +
				" [" + _("Row") + " # %(row_range)s] " + _("also be included in Item's rate")) % {
					"idx": tax.idx,
					"doctype": tax.doctype,
					"inclusive_label": self.meta.get_label("included_in_print_rate",
						parentfield=self.other_fname),
					"charge_type_label": self.meta.get_label("charge_type",
						parentfield=self.other_fname),
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
							parentfield=self.other_fname),
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
				
	def calculate_taxes(self):
		for item in self.item_doclist:
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)

			for i, tax in enumerate(self.tax_doclist):
				# tax_amount represents the amount of tax for the current step
				current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)
				
				if hasattr(self, "set_item_tax_amount"):
					self.set_item_tax_amount(item, tax, current_tax_amount)

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
				
				if tax.category:
					# if just for valuation, do not add the tax amount in total
					# hence, setting it as 0 for further steps
					current_tax_amount = 0.0 if (tax.category == "Valuation") else current_tax_amount
					
					current_tax_amount *= -1.0 if (tax.add_deduct_tax == "Deduct") else 1.0
				
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
		
		current_tax_amount = flt(current_tax_amount, self.precision("tax_amount", tax))
		
		# store tax breakup for each item
		tax.item_wise_tax_detail[item.item_code or item.item_name] = [tax_rate, current_tax_amount]

		return current_tax_amount
		
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
			
	def _set_in_company_currency(self, item, print_field, base_field):
		"""set values in base currency"""
		item.fields[base_field] = flt((flt(item.fields[print_field],
			self.precision(print_field, item)) * self.doc.conversion_rate),
			self.precision(base_field, item))
			
	def calculate_total_advance(self, parenttype, advance_parentfield):
		if self.doc.doctype == parenttype and self.doc.docstatus < 2:
			sum_of_allocated_amount = sum([flt(adv.allocated_amount, self.precision("allocated_amount", adv)) 
				for adv in self.doclist.get({"parentfield": advance_parentfield})])

			self.doc.total_advance = flt(sum_of_allocated_amount, self.precision("total_advance"))
			
			self.calculate_outstanding_amount()

	def get_gl_dict(self, args, cancel=None):
		"""this method populates the common properties of a gl entry record"""
		if cancel is None:
			cancel = (self.doc.docstatus == 2)
			
		gl_dict = {
			'company': self.doc.company, 
			'posting_date': self.doc.posting_date,
			'voucher_type': self.doc.doctype,
			'voucher_no': self.doc.name,
			'aging_date': self.doc.fields.get("aging_date") or self.doc.posting_date,
			'remarks': self.doc.remarks,
			'is_cancelled': cancel and "Yes" or "No",
			'fiscal_year': self.doc.fiscal_year,
			'debit': 0,
			'credit': 0,
			'is_opening': self.doc.fields.get("is_opening") or "No",
		}
		gl_dict.update(args)
		return gl_dict
				
	def clear_unallocated_advances(self, childtype, parentfield):
		self.doclist.remove_items({"parentfield": parentfield, "allocated_amount": ["in", [0, None, ""]]})
			
		webnotes.conn.sql("""delete from `tab%s` where parentfield=%s and parent = %s 
			and ifnull(allocated_amount, 0) = 0""" % (childtype, '%s', '%s'), (parentfield, self.doc.name))
		
	def get_advances(self, account_head, child_doctype, parentfield, dr_or_cr):
		res = webnotes.conn.sql("""select t1.name as jv_no, t1.remark, 
			t2.%s as amount, t2.name as jv_detail_no
			from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 
			where t1.name = t2.parent and t2.account = %s and t2.is_advance = 'Yes' 
			and (t2.against_voucher is null or t2.against_voucher = '')
			and (t2.against_invoice is null or t2.against_invoice = '') 
			and (t2.against_jv is null or t2.against_jv = '') 
			and t1.docstatus = 1 order by t1.posting_date""" % 
			(dr_or_cr, '%s'), account_head, as_dict=1)
			
		self.doclist = self.doc.clear_table(self.doclist, parentfield)
		for d in res:
			self.doclist.append({
				"doctype": child_doctype,
				"parentfield": parentfield,
				"journal_voucher": d.jv_no,
				"jv_detail_no": d.jv_detail_no,
				"remarks": d.remark,
				"advance_amount": flt(d.amount),
				"allocate_amount": 0
			})
			
	def validate_multiple_billing(self, ref_dt, item_ref_dn, based_on):
		for item in self.doclist.get({"parentfield": "entries"}):
			if item.fields.get(item_ref_dn):
				already_billed = webnotes.conn.sql("""select sum(%s) from `tab%s` 
					where %s=%s and docstatus=1""" % (based_on, self.tname, item_ref_dn, '%s'), 
					item.fields[item_ref_dn])[0][0]
				if already_billed:
					max_allowed_amt = webnotes.conn.get_value(ref_dt + " Item", 
						item.fields[item_ref_dn], based_on)
					
					if flt(already_billed) + flt(item.fields[based_on]) > max_allowed_amt:
						webnotes.msgprint(_("Row ")+ item.idx + ": " + item.item_code + 
							_(" will be over-billed against mentioned ") + ref_dt +  
							_(". Max allowed " + based_on + ": " + max_allowed_amt), 
							raise_exception=1)
		
	def get_company_default(self, fieldname):
		from accounts.utils import get_company_default
		return get_company_default(self.doc.company, fieldname)
			
		
	@property
	def stock_items(self):
		if not hasattr(self, "_stock_items"):
			self._stock_items = []
			item_codes = list(set(item.item_code for item in 
				self.doclist.get({"parentfield": self.fname})))
			if item_codes:
				self._stock_items = [r[0] for r in webnotes.conn.sql("""select name
					from `tabItem` where name in (%s) and is_stock_item='Yes'""" % \
					(", ".join((["%s"]*len(item_codes))),), item_codes)]
				
		return self._stock_items
		
	@property
	def company_abbr(self):
		if not hasattr(self, "_abbr"):
			self._abbr = webnotes.conn.get_value("Company", self.doc.company, "abbr")
			
		return self._abbr
