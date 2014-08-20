# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, throw
from frappe.utils import flt, cint, today
from erpnext.setup.utils import get_company_currency, get_exchange_rate
from erpnext.accounts.utils import get_fiscal_year, validate_fiscal_year
from erpnext.utilities.transaction_base import TransactionBase
import json

class AccountsController(TransactionBase):
	def validate(self):
		if self.get("_action") and self._action != "update_after_submit":
			self.set_missing_values(for_validate=True)
		self.validate_date_with_fiscal_year()
		if self.meta.get_field("currency"):
			self.calculate_taxes_and_totals()
			self.validate_value("grand_total", ">=", 0)
			self.set_total_in_words()

		self.validate_for_freezed_account()

	def set_missing_values(self, for_validate=False):
		for fieldname in ["posting_date", "transaction_date"]:
			if not self.get(fieldname) and self.meta.get_field(fieldname):
				self.set(fieldname, today())
				if not self.fiscal_year:
					self.fiscal_year = get_fiscal_year(self.get(fieldname))[0]
				break

	def validate_date_with_fiscal_year(self):
		if self.meta.get_field("fiscal_year") :
			date_field = ""
			if self.meta.get_field("posting_date"):
				date_field = "posting_date"
			elif self.meta.get_field("transaction_date"):
				date_field = "transaction_date"

			if date_field and self.get(date_field):
				validate_fiscal_year(self.get(date_field), self.fiscal_year,
					label=self.meta.get_label(date_field))

	def validate_for_freezed_account(self):
		for fieldname in ["customer", "supplier"]:
			if self.meta.get_field(fieldname) and self.get(fieldname):
				accounts = frappe.db.get_values("Account",
					{"master_type": fieldname.title(), "master_name": self.get(fieldname),
					"company": self.company}, "name")
				if accounts:
					from erpnext.accounts.doctype.gl_entry.gl_entry import validate_frozen_account
					for account in accounts:
						validate_frozen_account(account[0])

	def set_price_list_currency(self, buying_or_selling):
		if self.meta.get_field("currency"):
			company_currency = get_company_currency(self.company)

			# price list part
			fieldname = "selling_price_list" if buying_or_selling.lower() == "selling" \
				else "buying_price_list"
			if self.meta.get_field(fieldname) and self.get(fieldname):
				self.price_list_currency = frappe.db.get_value("Price List",
					self.get(fieldname), "currency")

				if self.price_list_currency == company_currency:
					self.plc_conversion_rate = 1.0

				elif not self.plc_conversion_rate:
					self.plc_conversion_rate = get_exchange_rate(
						self.price_list_currency, company_currency)

			# currency
			if not self.currency:
				self.currency = self.price_list_currency
				self.conversion_rate = self.plc_conversion_rate
			elif self.currency == company_currency:
				self.conversion_rate = 1.0
			elif not self.conversion_rate:
				self.conversion_rate = get_exchange_rate(self.currency,
					company_currency)

	def set_missing_item_details(self):
		"""set missing item values"""
		from erpnext.stock.get_item_details import get_item_details
		if hasattr(self, "fname"):
			parent_dict = {}
			for fieldname in self.meta.get_valid_columns():
				parent_dict[fieldname] = self.get(fieldname)

			for item in self.get(self.fname):
				if item.get("item_code"):
					args = parent_dict.copy()
					args.update(item.as_dict())
					ret = get_item_details(args)

					for fieldname, value in ret.items():
						if item.meta.get_field(fieldname) and \
							item.get(fieldname) is None and value is not None:
								item.set(fieldname, value)

					if ret.get("pricing_rule"):
						for field in ["base_price_list_rate", "price_list_rate",
							"discount_percentage", "base_rate", "rate"]:
								item.set(field, ret.get(field))

	def set_taxes(self, tax_parentfield, tax_master_field):
		if not self.meta.get_field(tax_parentfield):
			return

		tax_master_doctype = self.meta.get_field(tax_master_field).options

		if not self.get(tax_parentfield):
			if not self.get(tax_master_field):
				# get the default tax master
				self.set(tax_master_field, frappe.db.get_value(tax_master_doctype, {"is_default": 1}))

			self.append_taxes_from_master(tax_parentfield, tax_master_field, tax_master_doctype)

	def append_taxes_from_master(self, tax_parentfield, tax_master_field, tax_master_doctype=None):
		if self.get(tax_master_field):
			if not tax_master_doctype:
				tax_master_doctype = self.meta.get_field(tax_master_field).options

			self.extend(tax_parentfield,
				get_taxes_and_charges(tax_master_doctype, self.get(tax_master_field), tax_parentfield))

	def set_other_charges(self):
		self.set("other_charges", [])
		self.set_taxes("other_charges", "taxes_and_charges")

	def calculate_taxes_and_totals(self):
		self.discount_amount_applied = False
		self._calculate_taxes_and_totals()

		if self.meta.get_field("discount_amount"):
			self.apply_discount_amount()

	def _calculate_taxes_and_totals(self):
		# validate conversion rate
		company_currency = get_company_currency(self.company)
		if not self.currency or self.currency == company_currency:
			self.currency = company_currency
			self.conversion_rate = 1.0
		else:
			from erpnext.setup.doctype.currency.currency import validate_conversion_rate
			validate_conversion_rate(self.currency, self.conversion_rate,
				self.meta.get_label("conversion_rate"), self.company)

		self.conversion_rate = flt(self.conversion_rate)
		self.item_doclist = self.get(self.fname)
		self.tax_doclist = self.get(self.other_fname)

		self.calculate_item_values()
		self.initialize_taxes()

		if hasattr(self, "determine_exclusive_rate"):
			self.determine_exclusive_rate()

		self.calculate_net_total()
		self.calculate_taxes()
		self.calculate_totals()
		self._cleanup()

	def initialize_taxes(self):
		for tax in self.tax_doclist:
			tax.item_wise_tax_detail = {}
			tax_fields = ["total", "tax_amount_after_discount_amount",
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if not self.discount_amount_applied:
				tax_fields.append("tax_amount")

			for fieldname in tax_fields:
				tax.set(fieldname, 0.0)

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
			throw(_("Please specify a valid Row ID for {0} in row {1}").format(_(tax.doctype), tax.idx))

	def validate_inclusive_tax(self, tax):
		def _on_previous_row_error(row_range):
			throw(_("To include tax in row {0} in Item rate, taxes in rows {1} must also be included").format(tax.idx,
				row_range))

		if cint(getattr(tax, "included_in_print_rate", None)):
			if tax.charge_type == "Actual":
				# inclusive tax cannot be of type Actual
				throw(_("Charge of type 'Actual' in row {0} cannot be included in Item Rate").format(tax.idx))
			elif tax.charge_type == "On Previous Row Amount" and \
					not cint(self.tax_doclist[cint(tax.row_id) - 1].included_in_print_rate):
				# referred row should also be inclusive
				_on_previous_row_error(tax.row_id)
			elif tax.charge_type == "On Previous Row Total" and \
					not all([cint(t.included_in_print_rate) for t in self.tax_doclist[:cint(tax.row_id) - 1]]):
				# all rows about the reffered tax should be inclusive
				_on_previous_row_error("1 - %d" % (tax.row_id,))

	def calculate_taxes(self):
		# maintain actual tax rate based on idx
		actual_tax_dict = dict([[tax.idx, flt(tax.rate, self.precision("tax_amount", tax))] for tax in self.tax_doclist
			if tax.charge_type == "Actual"])

		for n, item in enumerate(self.item_doclist):
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)

			for i, tax in enumerate(self.tax_doclist):
				# tax_amount represents the amount of tax for the current step
				current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)

				# Adjust divisional loss to the last item
				if tax.charge_type == "Actual":
					actual_tax_dict[tax.idx] -= current_tax_amount
					if n == len(self.item_doclist) - 1:
						current_tax_amount += actual_tax_dict[tax.idx]

				# store tax_amount for current item as it will be used for
				# charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount

				# accumulate tax amount into tax.tax_amount
				if not self.discount_amount_applied:
					tax.tax_amount += current_tax_amount

				tax.tax_amount_after_discount_amount += current_tax_amount

				if getattr(tax, "category", None):
					# if just for valuation, do not add the tax amount in total
					# hence, setting it as 0 for further steps
					current_tax_amount = 0.0 if (tax.category == "Valuation") \
						else current_tax_amount

					current_tax_amount *= -1.0 if (tax.add_deduct_tax == "Deduct") else 1.0

				# Calculate tax.total viz. grand total till that step
				# note: grand_total_for_current_item contains the contribution of
				# item's amount, previously applied tax and the current tax on that item
				if i==0:
					tax.grand_total_for_current_item = flt(item.base_amount + current_tax_amount,
						self.precision("total", tax))
				else:
					tax.grand_total_for_current_item = \
						flt(self.tax_doclist[i-1].grand_total_for_current_item +
							current_tax_amount, self.precision("total", tax))

				# in tax.total, accumulate grand total of each item
				tax.total += tax.grand_total_for_current_item

				# set precision in the last item iteration
				if n == len(self.item_doclist) - 1:
					self.round_off_totals(tax)

					# adjust Discount Amount loss in last tax iteration
					if i == (len(self.tax_doclist) - 1) and self.discount_amount_applied:
						self.adjust_discount_amount_loss(tax)

	def round_off_totals(self, tax):
		tax.total = flt(tax.total, self.precision("total", tax))
		tax.tax_amount = flt(tax.tax_amount, self.precision("tax_amount", tax))
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount,
			self.precision("tax_amount", tax))

	def adjust_discount_amount_loss(self, tax):
		discount_amount_loss = self.grand_total - flt(self.discount_amount) - tax.total
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount +
			discount_amount_loss, self.precision("tax_amount", tax))
		tax.total = flt(tax.total + discount_amount_loss, self.precision("total", tax))

	def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)
		current_tax_amount = 0.0

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.rate, self.precision("tax_amount", tax))
			current_tax_amount = (self.net_total
				and ((item.base_amount / self.net_total) * actual)
				or 0)
		elif tax.charge_type == "On Net Total":
			current_tax_amount = (tax_rate / 100.0) * item.base_amount
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * \
				self.tax_doclist[cint(tax.row_id) - 1].tax_amount_for_current_item
		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * \
				self.tax_doclist[cint(tax.row_id) - 1].grand_total_for_current_item

		current_tax_amount = flt(current_tax_amount, self.precision("tax_amount", tax))

		# store tax breakup for each item
		key = item.item_code or item.item_name
		if tax.item_wise_tax_detail.get(key):
			item_wise_tax_amount = tax.item_wise_tax_detail[key][1] + current_tax_amount
			tax.item_wise_tax_detail[key] = [tax_rate,item_wise_tax_amount]
		else:
			tax.item_wise_tax_detail[key] = [tax_rate,current_tax_amount]

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
			tax.item_wise_tax_detail = json.dumps(tax.item_wise_tax_detail, separators=(',', ':'))

	def _set_in_company_currency(self, item, print_field, base_field):
		"""set values in base currency"""
		value_in_company_currency = flt(self.conversion_rate *
			flt(item.get(print_field), self.precision(print_field, item)),
			self.precision(base_field, item))
		item.set(base_field, value_in_company_currency)

	def calculate_total_advance(self, parenttype, advance_parentfield):
		if self.doctype == parenttype and self.docstatus < 2:
			sum_of_allocated_amount = sum([flt(adv.allocated_amount, self.precision("allocated_amount", adv))
				for adv in self.get(advance_parentfield)])

			self.total_advance = flt(sum_of_allocated_amount, self.precision("total_advance"))

			self.calculate_outstanding_amount()

	def get_gl_dict(self, args):
		"""this method populates the common properties of a gl entry record"""
		gl_dict = frappe._dict({
			'company': self.company,
			'posting_date': self.posting_date,
			'voucher_type': self.doctype,
			'voucher_no': self.name,
			'aging_date': self.get("aging_date") or self.posting_date,
			'remarks': self.get("remarks"),
			'fiscal_year': self.fiscal_year,
			'debit': 0,
			'credit': 0,
			'is_opening': self.get("is_opening") or "No",
		})
		gl_dict.update(args)
		return gl_dict

	def clear_unallocated_advances(self, childtype, parentfield):
		self.set(parentfield, self.get(parentfield, {"allocated_amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tab%s` where parentfield=%s and parent = %s
			and ifnull(allocated_amount, 0) = 0""" % (childtype, '%s', '%s'), (parentfield, self.name))

	def get_advances(self, account_head, child_doctype, parentfield, dr_or_cr):
		res = frappe.db.sql("""
			select
				t1.name as jv_no, t1.remark, t2.%s as amount, t2.name as jv_detail_no
			from
				`tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
			where
				t1.name = t2.parent and t2.account = %s and t2.is_advance = 'Yes' and t1.docstatus = 1
				and ifnull(t2.against_voucher, '')  = ''
				and ifnull(t2.against_invoice, '')  = ''
				and ifnull(t2.against_jv, '')  = ''
			order by t1.posting_date""" %
			(dr_or_cr, '%s'), account_head, as_dict=1)

		self.set(parentfield, [])
		for d in res:
			self.append(parentfield, {
				"doctype": child_doctype,
				"journal_voucher": d.jv_no,
				"jv_detail_no": d.jv_detail_no,
				"remarks": d.remark,
				"advance_amount": flt(d.amount),
				"allocate_amount": 0
			})

	def validate_multiple_billing(self, ref_dt, item_ref_dn, based_on, parentfield):
		from erpnext.controllers.status_updater import get_tolerance_for
		item_tolerance = {}
		global_tolerance = None

		for item in self.get("entries"):
			if item.get(item_ref_dn):
				ref_amt = flt(frappe.db.get_value(ref_dt + " Item",
					item.get(item_ref_dn), based_on), self.precision(based_on, item))
				if not ref_amt:
					frappe.msgprint(_("Warning: System will not check overbilling since amount for Item {0} in {1} is zero").format(item.item_code, ref_dt))
				else:
					already_billed = frappe.db.sql("""select sum(%s) from `tab%s`
						where %s=%s and docstatus=1 and parent != %s""" %
						(based_on, self.tname, item_ref_dn, '%s', '%s'),
						(item.get(item_ref_dn), self.name))[0][0]

					total_billed_amt = flt(flt(already_billed) + flt(item.get(based_on)),
						self.precision(based_on, item))

					tolerance, item_tolerance, global_tolerance = get_tolerance_for(item.item_code,
						item_tolerance, global_tolerance)

					max_allowed_amt = flt(ref_amt * (100 + tolerance) / 100)

					if total_billed_amt - max_allowed_amt > 0.01:
						reduce_by = total_billed_amt - max_allowed_amt
						frappe.throw(_("Cannot overbill for Item {0} in row {0} more than {1}. To allow overbilling, please set in Stock Settings").format(item.item_code, item.idx, max_allowed_amt))

	def get_company_default(self, fieldname):
		from erpnext.accounts.utils import get_company_default
		return get_company_default(self.company, fieldname)

	def get_stock_items(self):
		stock_items = []
		item_codes = list(set(item.item_code for item in self.get(self.fname)))
		if item_codes:
			stock_items = [r[0] for r in frappe.db.sql("""select name
				from `tabItem` where name in (%s) and is_stock_item='Yes'""" % \
				(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return stock_items

	@property
	def company_abbr(self):
		if not hasattr(self, "_abbr"):
			self._abbr = frappe.db.get_value("Company", self.company, "abbr")

		return self._abbr

	def check_credit_limit(self, account):
		total_outstanding = frappe.db.sql("""
			select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
			from `tabGL Entry` where account = %s""", account)

		total_outstanding = total_outstanding[0][0] if total_outstanding else 0
		if total_outstanding:
			frappe.get_doc('Account', account).check_credit_limit(total_outstanding)


@frappe.whitelist()
def get_tax_rate(account_head):
	return frappe.db.get_value("Account", account_head, "tax_rate")

@frappe.whitelist()
def get_taxes_and_charges(master_doctype, master_name, tax_parentfield):
	from frappe.model import default_fields
	tax_master = frappe.get_doc(master_doctype, master_name)

	taxes_and_charges = []
	for i, tax in enumerate(tax_master.get(tax_parentfield)):
		tax = tax.as_dict()

		for fieldname in default_fields:
			if fieldname in tax:
				del tax[fieldname]

		taxes_and_charges.append(tax)

	return taxes_and_charges
