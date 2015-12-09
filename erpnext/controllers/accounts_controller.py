# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, throw
from frappe.utils import today, flt, cint
from erpnext.setup.utils import get_company_currency, get_exchange_rate
from erpnext.accounts.utils import get_fiscal_year, validate_fiscal_year, get_account_currency
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.controllers.recurring_document import convert_to_recurring, validate_recurring_document
from erpnext.controllers.sales_and_purchase_return import validate_return
from erpnext.accounts.party import get_party_account_currency
from erpnext.exceptions import CustomerFrozen, InvalidCurrency

force_item_fields = ("item_group", "barcode", "brand", "stock_uom")

class AccountsController(TransactionBase):
	def __init__(self, arg1, arg2=None):
		super(AccountsController, self).__init__(arg1, arg2)

	@property
	def company_currency(self):
		if not hasattr(self, "__company_currency"):
			self.__company_currency = get_company_currency(self.company)

		return self.__company_currency

	def validate(self):
		if self.get("_action") and self._action != "update_after_submit":
			self.set_missing_values(for_validate=True)
		self.validate_date_with_fiscal_year()

		if self.meta.get_field("currency"):
			self.calculate_taxes_and_totals()
			if not self.meta.get_field("is_return") or not self.is_return:
				self.validate_value("base_grand_total", ">=", 0)

			validate_return(self)
			self.set_total_in_words()

		if self.doctype in ("Sales Invoice", "Purchase Invoice") and not self.is_return:
			self.validate_due_date()

		if self.meta.get_field("is_recurring"):
			validate_recurring_document(self)

		if self.meta.get_field("taxes_and_charges"):
			self.validate_enabled_taxes_and_charges()

		self.validate_party()
		self.validate_currency()

	def on_submit(self):
		if self.meta.get_field("is_recurring"):
			convert_to_recurring(self, self.get("posting_date") or self.get("transaction_date"))

	def on_update_after_submit(self):
		if self.meta.get_field("is_recurring"):
			validate_recurring_document(self)
			convert_to_recurring(self, self.get("posting_date") or self.get("transaction_date"))

	def before_recurring(self):
		if self.meta.get_field("fiscal_year"):
			self.fiscal_year = None
		if self.meta.get_field("due_date"):
			self.due_date = None

	def set_missing_values(self, for_validate=False):
		for fieldname in ["posting_date", "transaction_date"]:
			if not self.get(fieldname) and self.meta.get_field(fieldname):
				self.set(fieldname, today())
				if self.meta.get_field("fiscal_year") and not self.fiscal_year:
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
			if not self.due_date:
				frappe.throw(_("Due Date is mandatory"))

			validate_due_date(self.posting_date, self.due_date, "Customer", self.customer, self.company)
		elif self.doctype == "Purchase Invoice":
			validate_due_date(self.posting_date, self.due_date, "Supplier", self.supplier, self.company)

	def set_price_list_currency(self, buying_or_selling):
		if self.meta.get_field("currency"):
			# price list part
			fieldname = "selling_price_list" if buying_or_selling.lower() == "selling" \
				else "buying_price_list"
			if self.meta.get_field(fieldname) and self.get(fieldname):
				self.price_list_currency = frappe.db.get_value("Price List",
					self.get(fieldname), "currency")

				if self.price_list_currency == self.company_currency:
					self.plc_conversion_rate = 1.0

				elif not self.plc_conversion_rate:
					self.plc_conversion_rate = get_exchange_rate(
						self.price_list_currency, self.company_currency)

			# currency
			if not self.currency:
				self.currency = self.price_list_currency
				self.conversion_rate = self.plc_conversion_rate
			elif self.currency == self.company_currency:
				self.conversion_rate = 1.0
			elif not self.conversion_rate:
				self.conversion_rate = get_exchange_rate(self.currency,
					self.company_currency)

	def set_missing_item_details(self):
		"""set missing item values"""
		from erpnext.stock.get_item_details import get_item_details
		
		if self.doctype == "Purchase Invoice":
			auto_accounting_for_stock = cint(frappe.defaults.get_global_default("auto_accounting_for_stock"))

			if auto_accounting_for_stock:
				stock_not_billed_account = self.get_company_default("stock_received_but_not_billed")
				
			stock_items = self.get_stock_items()

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

					if self.get("is_subcontracted"):
						args["is_subcontracted"] = self.is_subcontracted

					ret = get_item_details(args)

					for fieldname, value in ret.items():
						if item.meta.get_field(fieldname) and value is not None:
							if (item.get(fieldname) is None or fieldname in force_item_fields):
								item.set(fieldname, value)

							elif fieldname == "cost_center" and not item.get("cost_center"):
								item.set(fieldname, value)

							elif fieldname == "conversion_factor" and not item.get("conversion_factor"):
								item.set(fieldname, value)

					if ret.get("pricing_rule"):
						item.set("discount_percentage", ret.get("discount_percentage"))
						if ret.get("pricing_rule_for") == "Price":
							item.set("pricing_list_rate", ret.get("pricing_list_rate"))

						if item.price_list_rate:
							item.rate = flt(item.price_list_rate *
								(1.0 - (flt(item.discount_percentage) / 100.0)), item.precision("rate"))
								
					if self.doctype == "Purchase Invoice":
						if auto_accounting_for_stock and item.item_code in stock_items \
							and self.is_opening == 'No' \
							and (not item.po_detail or not frappe.db.get_value("Purchase Order Item", 
								item.po_detail, "delivered_by_supplier")):
				
								item.expense_account = stock_not_billed_account
								item.cost_center = None

	def set_taxes(self):
		if not self.meta.get_field("taxes"):
			return

		tax_master_doctype = self.meta.get_field("taxes_and_charges").options

		if not self.get("taxes"):
			if not self.get("taxes_and_charges"):
				# get the default tax master
				self.set("taxes_and_charges", frappe.db.get_value(tax_master_doctype, {"is_default": 1}))

			self.append_taxes_from_master(tax_master_doctype)

	def append_taxes_from_master(self, tax_master_doctype=None):
		if self.get("taxes_and_charges"):
			if not tax_master_doctype:
				tax_master_doctype = self.meta.get_field("taxes_and_charges").options

			self.extend("taxes", get_taxes_and_charges(tax_master_doctype, self.get("taxes_and_charges")))

	def set_other_charges(self):
		self.set("taxes", [])
		self.set_taxes()

	def validate_enabled_taxes_and_charges(self):
		taxes_and_charges_doctype = self.meta.get_options("taxes_and_charges")
		if frappe.db.get_value(taxes_and_charges_doctype, self.taxes_and_charges, "disabled"):
			frappe.throw(_("{0} '{1}' is disabled").format(taxes_and_charges_doctype, self.taxes_and_charges))

	def get_gl_dict(self, args, account_currency=None):
		"""this method populates the common properties of a gl entry record"""
		gl_dict = frappe._dict({
			'company': self.company,
			'posting_date': self.posting_date,
			'voucher_type': self.doctype,
			'voucher_no': self.name,
			'remarks': self.get("remarks"),
			'fiscal_year': self.fiscal_year,
			'debit': 0,
			'credit': 0,
			'debit_in_account_currency': 0,
			'credit_in_account_currency': 0,
			'is_opening': self.get("is_opening") or "No",
			'party_type': None,
			'party': None
		})
		gl_dict.update(args)

		if not account_currency:
			account_currency = get_account_currency(gl_dict.account)

		if self.doctype not in ["Journal Entry", "Period Closing Voucher"]:
			self.validate_account_currency(gl_dict.account, account_currency)
			self.set_balance_in_account_currency(gl_dict, account_currency)

		return gl_dict

	def validate_account_currency(self, account, account_currency=None):
		valid_currency = [self.company_currency]
		if self.get("currency") and self.currency != self.company_currency:
			valid_currency.append(self.currency)

		if account_currency not in valid_currency:
			frappe.throw(_("Account {0} is invalid. Account Currency must be {1}")
				.format(account, _(" or ").join(valid_currency)))

	def set_balance_in_account_currency(self, gl_dict, account_currency=None):
		if (not self.get("conversion_rate") and account_currency!=self.company_currency):
				frappe.throw(_("Account: {0} with currency: {1} can not be selected")
					.format(gl_dict.account, account_currency))

		gl_dict["account_currency"] = self.company_currency if account_currency==self.company_currency \
			else account_currency

		# set debit/credit in account currency if not provided
		if flt(gl_dict.debit) and not flt(gl_dict.debit_in_account_currency):
			gl_dict.debit_in_account_currency = gl_dict.debit if account_currency==self.company_currency \
				else flt(gl_dict.debit / (self.get("conversion_rate")), 2)

		if flt(gl_dict.credit) and not flt(gl_dict.credit_in_account_currency):
			gl_dict.credit_in_account_currency = gl_dict.credit if account_currency==self.company_currency \
				else flt(gl_dict.credit / (self.get("conversion_rate")), 2)

	def clear_unallocated_advances(self, childtype, parentfield):
		self.set(parentfield, self.get(parentfield, {"allocated_amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tab%s` where parentfield=%s and parent = %s
			and allocated_amount = 0""" % (childtype, '%s', '%s'), (parentfield, self.name))

	def get_advances(self, account_head, party_type, party, child_doctype, parentfield, dr_or_cr, against_order_field):
		"""Returns list of advances against Account, Party, Reference"""
		order_list = list(set([d.get(against_order_field) for d in self.get("items") if d.get(against_order_field)]))

		# conver sales_order to "Sales Order"
		reference_type = against_order_field.replace("_", " ").title()

		condition = ""
		if order_list:
			in_placeholder = ', '.join(['%s'] * len(order_list))
			condition = "or (t2.reference_type = '{0}' and ifnull(t2.reference_name, '') in ({1}))"\
				.format(reference_type, in_placeholder)

		res = frappe.db.sql("""
			select
				t1.name as jv_no, t1.remark, t2.{0} as amount, t2.name as jv_detail_no,
				reference_name as against_order
			from
				`tabJournal Entry` t1, `tabJournal Entry Account` t2
			where
				t1.name = t2.parent and t2.account = %s
				and t2.party_type = %s and t2.party = %s
				and t2.is_advance = 'Yes' and t1.docstatus = 1
				and (ifnull(t2.reference_type, '')='' {1})
			order by t1.posting_date""".format(dr_or_cr, condition),
			[account_head, party_type, party] + order_list, as_dict=1)

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

	def validate_advance_jv(self, reference_type):
		against_order_field = frappe.scrub(reference_type)
		order_list = list(set([d.get(against_order_field) for d in self.get("items") if d.get(against_order_field)]))
		if order_list:
			account = self.get("debit_to" if self.doctype=="Sales Invoice" else "credit_to")

			jv_against_order = frappe.db.sql("""select parent, reference_name as against_order
				from `tabJournal Entry Account`
				where docstatus=1 and account=%s and ifnull(is_advance, 'No') = 'Yes'
				and reference_type=%s
				and ifnull(reference_name, '') in ({0})
				group by parent, reference_name""".format(', '.join(['%s']*len(order_list))),
					tuple([account, reference_type] + order_list), as_dict=1)

			if jv_against_order:
				order_jv_map = {}
				for d in jv_against_order:
					order_jv_map.setdefault(d.against_order, []).append(d.parent)

				advance_jv_against_si = [d.journal_entry for d in self.get("advances")]

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
				from `tabItem` where name in (%s) and is_stock_item=1""" % \
				(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return stock_items

	def set_total_advance_paid(self):
		if self.doctype == "Sales Order":
			dr_or_cr = "credit_in_account_currency"
		else:
			dr_or_cr = "debit_in_account_currency"

		advance_paid = frappe.db.sql("""
			select
				sum({dr_or_cr})
			from
				`tabJournal Entry Account`
			where
				reference_type = %s and reference_name = %s
				and docstatus = 1 and is_advance = "Yes"
		""".format(dr_or_cr=dr_or_cr), (self.doctype, self.name))

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

	def validate_party(self):
		frozen_accounts_modifier = frappe.db.get_value( 'Accounts Settings', None,'frozen_accounts_modifier')
		if frozen_accounts_modifier in frappe.get_roles():
			return

		party_type, party = self.get_party()

		if party_type:
			if frappe.db.get_value(party_type, party, "is_frozen"):
				frappe.throw("{0} {1} is frozen".format(party_type, party), CustomerFrozen)

	def get_party(self):
		party_type = None
		if self.meta.get_field("customer"):
			party_type = 'Customer'

		elif self.meta.get_field("supplier"):
			party_type = 'Supplier'

		party = self.get(party_type.lower()) if party_type else None

		return party_type, party

	def validate_currency(self):
		if self.get("currency"):
			party_type, party = self.get_party()
			if party_type and party:
				party_account_currency = get_party_account_currency(party_type, party, self.company)

				if (party_account_currency
					and party_account_currency != self.company_currency
					and self.currency != party_account_currency):

					frappe.throw(_("Accounting Entry for {0}: {1} can only be made in currency: {2}")
						.format(party_type, party, party_account_currency), InvalidCurrency)

				# Note: not validating with gle account because we don't have the account at quotation / sales order level and we shouldn't stop someone from creating a sales invoice if sales order is already created

@frappe.whitelist()
def get_tax_rate(account_head):
	return frappe.db.get_value("Account", account_head, "tax_rate")

@frappe.whitelist()
def get_default_taxes_and_charges(master_doctype):
	default_tax = frappe.db.get_value(master_doctype, {"is_default": 1})
	return get_taxes_and_charges(master_doctype, default_tax)

@frappe.whitelist()
def get_taxes_and_charges(master_doctype, master_name):
	if not master_name:
		return
	from frappe.model import default_fields
	tax_master = frappe.get_doc(master_doctype, master_name)

	taxes_and_charges = []
	for i, tax in enumerate(tax_master.get("taxes")):
		tax = tax.as_dict()

		for fieldname in default_fields:
			if fieldname in tax:
				del tax[fieldname]

		taxes_and_charges.append(tax)

	return taxes_and_charges

def validate_conversion_rate(currency, conversion_rate, conversion_rate_label, company):
	"""common validation for currency and price list currency"""

	company_currency = frappe.db.get_value("Company", company, "default_currency", cache=True)

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
