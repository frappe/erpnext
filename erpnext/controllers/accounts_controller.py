# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, throw
from frappe.utils import today, flt, cint
from erpnext.setup.utils import get_company_currency, get_exchange_rate
from erpnext.accounts.utils import get_fiscal_year, validate_fiscal_year
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.controllers.recurring_document import convert_to_recurring, validate_recurring_document

class AccountsController(TransactionBase):
	def validate(self):
		if self.get("_action") and self._action != "update_after_submit":
			self.set_missing_values(for_validate=True)
		self.validate_date_with_fiscal_year()
		if self.meta.get_field("currency"):
			self.calculate_taxes_and_totals()
			self.validate_value("base_grand_total", ">=", 0)
			self.set_total_in_words()

		self.validate_due_date()

		if self.meta.get_field("is_recurring"):
			validate_recurring_document(self)

		if self.meta.get_field("taxes_and_charges"):
			self.validate_enabled_taxes_and_charges()

	def on_submit(self):
		if self.meta.get_field("is_recurring"):
			convert_to_recurring(self, self.get("posting_date") or self.get("transaction_date"))

	def on_update_after_submit(self):
		if self.meta.get_field("is_recurring"):
			validate_recurring_document(self)
			convert_to_recurring(self, self.get("posting_date") or self.get("transaction_date"))

	def before_recurring(self):
		self.fiscal_year = None
		for fieldname in ("due_date", "aging_date"):
			if self.meta.get_field(fieldname):
				self.set(fieldname, None)

	def set_missing_values(self, for_validate=False):
		for fieldname in ["posting_date", "transaction_date"]:
			if not self.get(fieldname) and self.meta.get_field(fieldname):
				self.set(fieldname, today())
				if not self.fiscal_year:
					self.fiscal_year = get_fiscal_year(self.get(fieldname))[0]
				break

	def calculate_taxes_and_totals(self):
		from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
		calculate_taxes_and_totals(self)

		if self.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
			self.calculate_commission()
			self.calculate_contribution()

	def validate_date_with_fiscal_year(self):
		if self.meta.get_field("fiscal_year") :
			date_field = ""
			if self.meta.get_field("posting_date"):
				date_field = "posting_date"
			elif self.meta.get_field("transaction_date"):
				date_field = "transaction_date"

			if date_field and self.get(date_field):
				validate_fiscal_year(self.get(date_field), self.fiscal_year,
					self.meta.get_label(date_field), self)

	def validate_due_date(self):
		from erpnext.accounts.party import validate_due_date
		if self.doctype == "Sales Invoice":
			validate_due_date(self.posting_date, self.due_date, "Customer", self.customer, self.company)
		elif self.doctype == "Purchase Invoice":
			validate_due_date(self.posting_date, self.due_date, "Supplier", self.supplier, self.company)

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

		if hasattr(self, "items"):
			parent_dict = {}
			for fieldname in self.meta.get_valid_columns():
				parent_dict[fieldname] = self.get(fieldname)

			for item in self.get("items"):
				if item.get("item_code"):
					args = parent_dict.copy()
					args.update(item.as_dict())
					if not args.get("transaction_date"):
						args["transaction_date"] = args.get("posting_date")
					ret = get_item_details(args)

					for fieldname, value in ret.items():
						if item.meta.get_field(fieldname) and \
							item.get(fieldname) is None and value is not None:
								item.set(fieldname, value)

						if fieldname == "cost_center" and item.meta.get_field("cost_center") \
							and not item.get("cost_center") and value is not None:
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
		self.set("taxes", [])
		self.set_taxes("taxes", "taxes_and_charges")

	def validate_enabled_taxes_and_charges(self):
		taxes_and_charges_doctype = self.meta.get_options("taxes_and_charges")
		if frappe.db.get_value(taxes_and_charges_doctype, self.taxes_and_charges, "disabled"):
			frappe.throw(_("{0} '{1}' is disabled").format(taxes_and_charges_doctype, self.taxes_and_charges))

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
			'party_type': None,
			'party': None
		})
		gl_dict.update(args)
		return gl_dict

	def clear_unallocated_advances(self, childtype, parentfield):
		self.set(parentfield, self.get(parentfield, {"allocated_amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tab%s` where parentfield=%s and parent = %s
			and ifnull(allocated_amount, 0) = 0""" % (childtype, '%s', '%s'), (parentfield, self.name))

	def get_advances(self, account_head, party_type, party, child_doctype, parentfield, dr_or_cr, against_order_field):
		so_list = list(set([d.get(against_order_field) for d in self.get("items") if d.get(against_order_field)]))
		cond = ""
		if so_list:
			cond = "or (ifnull(t2.%s, '')  in (%s))" % ("against_" + against_order_field, ', '.join(['%s']*len(so_list)))

		res = frappe.db.sql("""
			select
				t1.name as jv_no, t1.remark, t2.{0} as amount, t2.name as jv_detail_no, `against_{1}` as against_order
			from
				`tabJournal Entry` t1, `tabJournal Entry Account` t2
			where
				t1.name = t2.parent and t2.account = %s
				and t2.party_type=%s and t2.party=%s
				and t2.is_advance = 'Yes' and t1.docstatus = 1
				and ((
						ifnull(t2.against_voucher, '')  = ''
						and ifnull(t2.against_invoice, '')  = ''
						and ifnull(t2.against_jv, '')  = ''
						and ifnull(t2.against_sales_order, '')  = ''
						and ifnull(t2.against_purchase_order, '')  = ''
				) {2})
			order by t1.posting_date""".format(dr_or_cr, against_order_field, cond),
			[account_head, party_type, party] + so_list, as_dict=1)

		self.set(parentfield, [])
		for d in res:
			self.append(parentfield, {
				"doctype": child_doctype,
				"journal_entry": d.jv_no,
				"jv_detail_no": d.jv_detail_no,
				"remarks": d.remark,
				"advance_amount": flt(d.amount),
				"allocated_amount": flt(d.amount) if d.against_order else 0
			})

	def validate_advance_jv(self, advance_table_fieldname, against_order_field):
		order_list = list(set([d.get(against_order_field) for d in self.get("items") if d.get(against_order_field)]))
		if order_list:
			account = self.get("debit_to" if self.doctype=="Sales Invoice" else "credit_to")

			jv_against_order = frappe.db.sql("""select parent, %s as against_order
				from `tabJournal Entry Account`
				where docstatus=1 and account=%s and ifnull(is_advance, 'No') = 'Yes'
				and ifnull(against_sales_order, '') in (%s)
				group by parent, against_sales_order""" %
				("against_" + against_order_field, '%s', ', '.join(['%s']*len(order_list))),
				tuple([account] + order_list), as_dict=1)

			if jv_against_order:
				order_jv_map = {}
				for d in jv_against_order:
					order_jv_map.setdefault(d.against_order, []).append(d.parent)

				advance_jv_against_si = [d.journal_entry for d in self.get(advance_table_fieldname)]

				for order, jv_list in order_jv_map.items():
					for jv in jv_list:
						if not advance_jv_against_si or jv not in advance_jv_against_si:
							frappe.msgprint(_("Journal Entry {0} is linked against Order {1}, check if it should be pulled as advance in this invoice.")
								.format(jv, order))


	def validate_multiple_billing(self, ref_dt, item_ref_dn, based_on, parentfield):
		from erpnext.controllers.status_updater import get_tolerance_for
		item_tolerance = {}
		global_tolerance = None

		for item in self.get("items"):
			if item.get(item_ref_dn):
				ref_amt = flt(frappe.db.get_value(ref_dt + " Item",
					item.get(item_ref_dn), based_on), self.precision(based_on, item))
				if not ref_amt:
					frappe.msgprint(_("Warning: System will not check overbilling since amount for Item {0} in {1} is zero").format(item.item_code, ref_dt))
				else:
					already_billed = frappe.db.sql("""select sum(%s) from `tab%s`
						where %s=%s and docstatus=1 and parent != %s""" %
						(based_on, self.doctype + " Item", item_ref_dn, '%s', '%s'),
						(item.get(item_ref_dn), self.name))[0][0]

					total_billed_amt = flt(flt(already_billed) + flt(item.get(based_on)),
						self.precision(based_on, item))

					tolerance, item_tolerance, global_tolerance = get_tolerance_for(item.item_code,
						item_tolerance, global_tolerance)

					max_allowed_amt = flt(ref_amt * (100 + tolerance) / 100)

					if total_billed_amt - max_allowed_amt > 0.01:
						frappe.throw(_("Cannot overbill for Item {0} in row {1} more than {2}. To allow overbilling, please set in Stock Settings").format(item.item_code, item.idx, max_allowed_amt))

	def get_company_default(self, fieldname):
		from erpnext.accounts.utils import get_company_default
		return get_company_default(self.company, fieldname)

	def get_stock_items(self):
		stock_items = []
		item_codes = list(set(item.item_code for item in self.get("items")))
		if item_codes:
			stock_items = [r[0] for r in frappe.db.sql("""select name
				from `tabItem` where name in (%s) and is_stock_item='Yes'""" % \
				(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return stock_items

	def set_total_advance_paid(self):
		if self.doctype == "Sales Order":
			dr_or_cr = "credit"
			against_field = "against_sales_order"
		else:
			dr_or_cr = "debit"
			against_field = "against_purchase_order"

		advance_paid = frappe.db.sql("""
			select
				sum(ifnull({dr_or_cr}, 0))
			from
				`tabJournal Entry Account`
			where
				{against_field} = %s and docstatus = 1 and is_advance = "Yes" """.format(dr_or_cr=dr_or_cr, \
					against_field=against_field), self.name)

		if advance_paid:
			advance_paid = flt(advance_paid[0][0], self.precision("advance_paid"))
		if flt(self.base_grand_total) >= advance_paid:
			frappe.db.set_value(self.doctype, self.name, "advance_paid", advance_paid)
		else:
			frappe.throw(_("Total advance ({0}) against Order {1} cannot be greater \
				than the Grand Total ({2})")
			.format(advance_paid, self.name, self.base_grand_total))

	@property
	def company_abbr(self):
		if not hasattr(self, "_abbr"):
			self._abbr = frappe.db.get_value("Company", self.company, "abbr")

		return self._abbr

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

def validate_conversion_rate(currency, conversion_rate, conversion_rate_label, company):
	"""common validation for currency and price list currency"""

	company_currency = frappe.db.get_value("Company", company, "default_currency")

	if not conversion_rate:
		throw(_("{0} is mandatory. Maybe Currency Exchange record is not created for {1} to {2}.").format(
			conversion_rate_label, currency, company_currency))

def validate_taxes_and_charges(tax):
	if tax.charge_type in ['Actual', 'On Net Total'] and tax.row_id:
		frappe.throw(_("Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'"))
	elif tax.charge_type in ['On Previous Row Amount', 'On Previous Row Total']:
		if cint(tax.idx) == 1:
			frappe.throw(_("Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"))
		elif not tax.row_id:
			frappe.throw(_("Please specify a valid Row ID for row {0} in table {1}".format(tax.idx, _(tax.doctype))))
		elif tax.row_id and cint(tax.row_id) >= cint(tax.idx):
			frappe.throw(_("Cannot refer row number greater than or equal to current row number for this Charge type"))

	if tax.charge_type == "Actual":
		tax.rate = None
		if not tax.tax_amount:
			frappe.throw(_("Amount is mandatory for charge type 'Actual'"))

def validate_inclusive_tax(tax, doc):
	def _on_previous_row_error(row_range):
		throw(_("To include tax in row {0} in Item rate, taxes in rows {1} must also be included").format(tax.idx,
			row_range))

	if cint(getattr(tax, "included_in_print_rate", None)):
		if tax.charge_type == "Actual":
			# inclusive tax cannot be of type Actual
			throw(_("Charge of type 'Actual' in row {0} cannot be included in Item Rate").format(tax.idx))
		elif tax.charge_type == "On Previous Row Amount" and \
				not cint(doc.get("taxes")[cint(tax.row_id) - 1].included_in_print_rate):
			# referred row should also be inclusive
			_on_previous_row_error(tax.row_id)
		elif tax.charge_type == "On Previous Row Total" and \
				not all([cint(t.included_in_print_rate) for t in doc.get("taxes")[:cint(tax.row_id) - 1]]):
			# all rows about the reffered tax should be inclusive
			_on_previous_row_error("1 - %d" % (tax.row_id,))
		elif tax.get("category") == "Valuation":
			frappe.throw(_("Valuation type charges can not marked as Inclusive"))
