# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _, throw
from frappe.utils import today, flt, cint, fmt_money, formatdate, getdate
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.utils import get_fiscal_years, validate_fiscal_year, get_account_currency
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.controllers.recurring_document import convert_to_recurring, validate_recurring_document
from erpnext.controllers.sales_and_purchase_return import validate_return
from erpnext.accounts.party import get_party_account_currency, validate_party_frozen_disabled
from erpnext.exceptions import InvalidCurrency

force_item_fields = ("item_group", "barcode", "brand", "stock_uom")

class AccountsController(TransactionBase):
	def __init__(self, arg1, arg2=None):
		super(AccountsController, self).__init__(arg1, arg2)

	@property
	def company_currency(self):
		if not hasattr(self, "__company_currency"):
			self.__company_currency = erpnext.get_company_currency(self.company)

		return self.__company_currency

	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value('Accounts Settings', 'make_payment_via_journal_entry')

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
			self.validate_advance_entries()

		if self.meta.get_field("taxes_and_charges"):
			self.validate_enabled_taxes_and_charges()

		self.validate_party()
		self.validate_currency()

		if self.meta.get_field("is_recurring"):
			if self.amended_from and self.recurring_id == self.amended_from:
				self.recurring_id = None
			if not self.get("__islocal"):
				validate_recurring_document(self)
				convert_to_recurring(self, self.get("posting_date") or self.get("transaction_date"))

		if self.doctype == 'Purchase Invoice':
			self.validate_paid_amount()

	def before_print(self):
		if self.doctype in ['Purchase Order', 'Sales Order']:
			if self.get("group_same_items"):
				self.group_similar_items()

	def validate_paid_amount(self):
		if hasattr(self, "is_pos") or hasattr(self, "is_paid"):
			is_paid = self.get("is_pos") or self.get("is_paid")
			if cint(is_paid) == 1:
				if flt(self.paid_amount) == 0 and flt(self.outstanding_amount) > 0:
					if self.cash_bank_account:
						self.paid_amount = flt(flt(self.grand_total) - flt(self.write_off_amount),
							self.precision("paid_amount"))
						self.base_paid_amount = flt(self.paid_amount * self.conversion_rate, self.precision("base_paid_amount"))
					else:
						# show message that the amount is not paid
						self.paid_amount = 0
						frappe.throw(_("Note: Payment Entry will not be created since 'Cash or Bank Account' was not specified"))
			else:
				frappe.db.set(self,'paid_amount',0)

	def on_update_after_submit(self):
		if self.meta.get_field("is_recurring"):
			validate_recurring_document(self)
			convert_to_recurring(self, self.get("posting_date") or self.get("transaction_date"))

	def set_missing_values(self, for_validate=False):
		if frappe.flags.in_test:
			for fieldname in ["posting_date","transaction_date"]:
				if self.meta.get_field(fieldname) and not self.get(fieldname):
					self.set(fieldname, today())
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
				validate_fiscal_year(self.get(date_field), self.fiscal_year, self.company,
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
		if self.meta.get_field("posting_date"):
			transaction_date = self.posting_date
		else:
			transaction_date = self.transaction_date

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
					self.plc_conversion_rate = get_exchange_rate(self.price_list_currency,
						self.company_currency, transaction_date)

			# currency
			if not self.currency:
				self.currency = self.price_list_currency
				self.conversion_rate = self.plc_conversion_rate
			elif self.currency == self.company_currency:
				self.conversion_rate = 1.0
			elif not self.conversion_rate:
				self.conversion_rate = get_exchange_rate(self.currency,
					self.company_currency, transaction_date)

	def set_missing_item_details(self, for_validate=False):
		"""set missing item values"""
		from erpnext.stock.get_item_details import get_item_details
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if hasattr(self, "items"):
			parent_dict = {}
			for fieldname in self.meta.get_valid_columns():
				parent_dict[fieldname] = self.get(fieldname)

			if self.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
				document_type = "{} Item".format(self.doctype)
				parent_dict.update({"document_type": document_type})

			for item in self.get("items"):
				if item.get("item_code"):
					args = parent_dict.copy()
					args.update(item.as_dict())

					args["doctype"] = self.doctype
					args["name"] = self.name

					if not args.get("transaction_date"):
						args["transaction_date"] = args.get("posting_date")

					if self.get("is_subcontracted"):
						args["is_subcontracted"] = self.is_subcontracted

					ret = get_item_details(args)

					for fieldname, value in ret.items():
						if item.meta.get_field(fieldname) and value is not None:
							if (item.get(fieldname) is None or fieldname in force_item_fields):
								item.set(fieldname, value)

							elif fieldname in ['cost_center', 'conversion_factor'] and not item.get(fieldname):
								item.set(fieldname, value)

							elif fieldname == "serial_no":
								stock_qty = item.get("stock_qty") * -1 if item.get("stock_qty") < 0 else item.get("stock_qty")
								if stock_qty != len(get_serial_nos(item.get('serial_no'))):
									item.set(fieldname, value)

							elif fieldname == "conversion_factor" and not item.get("conversion_factor"):
								item.set(fieldname, value)

					if ret.get("pricing_rule"):
						# if user changed the discount percentage then set user's discount percentage ?
						item.set("discount_percentage", ret.get("discount_percentage"))
						if ret.get("pricing_rule_for") == "Price":
							item.set("pricing_list_rate", ret.get("pricing_list_rate"))

						if item.price_list_rate:
							item.rate = flt(item.price_list_rate *
								(1.0 - (flt(item.discount_percentage) / 100.0)), item.precision("rate"))

			if self.doctype == "Purchase Invoice":
				self.set_expense_account(for_validate)

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

		fiscal_years = get_fiscal_years(self.posting_date, company=self.company)
		if len(fiscal_years) > 1:
			frappe.throw(_("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(formatdate(self.posting_date)))
		else:
			fiscal_year = fiscal_years[0][0]

		gl_dict = frappe._dict({
			'company': self.company,
			'posting_date': self.posting_date,
			'fiscal_year': fiscal_year,
			'voucher_type': self.doctype,
			'voucher_no': self.name,
			'remarks': self.get("remarks"),
			'debit': 0,
			'credit': 0,
			'debit_in_account_currency': 0,
			'credit_in_account_currency': 0,
			'is_opening': self.get("is_opening") or "No",
			'party_type': None,
			'party': None,
			'project': self.get("project")
		})
		gl_dict.update(args)

		if not account_currency:
			account_currency = get_account_currency(gl_dict.account)

		if gl_dict.account and self.doctype not in ["Journal Entry", 
			"Period Closing Voucher", "Payment Entry"]:
			
			self.validate_account_currency(gl_dict.account, account_currency)
			set_balance_in_account_currency(gl_dict, account_currency, self.get("conversion_rate"), self.company_currency)

		return gl_dict

	def validate_account_currency(self, account, account_currency=None):
		valid_currency = [self.company_currency]
		if self.get("currency") and self.currency != self.company_currency:
			valid_currency.append(self.currency)

		if account_currency not in valid_currency:
			frappe.throw(_("Account {0} is invalid. Account Currency must be {1}")
				.format(account, _(" or ").join(valid_currency)))

	def clear_unallocated_advances(self, childtype, parentfield):
		self.set(parentfield, self.get(parentfield, {"allocated_amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tab%s` where parentfield=%s and parent = %s
			and allocated_amount = 0""" % (childtype, '%s', '%s'), (parentfield, self.name))

	def set_advances(self):
		"""Returns list of advances against Account, Party, Reference"""

		res = self.get_advance_entries()

		self.set("advances", [])
		for d in res:
			self.append("advances", {
				"doctype": self.doctype + " Advance",
				"reference_type": d.reference_type,
				"reference_name": d.reference_name,
				"reference_row": d.reference_row,
				"remarks": d.remarks,
				"advance_amount": flt(d.amount),
				"allocated_amount": flt(d.amount) if d.against_order else 0
			})

	def get_advance_entries(self, include_unallocated=True):
		if self.doctype == "Sales Invoice":
			party_account = self.debit_to
			party_type = "Customer"
			party = self.customer
			amount_field = "credit_in_account_currency"
			order_field = "sales_order"
			order_doctype = "Sales Order"
		else:
			party_account = self.credit_to
			party_type = "Supplier"
			party = self.supplier
			amount_field = "debit_in_account_currency"
			order_field = "purchase_order"
			order_doctype = "Purchase Order"

		order_list = list(set([d.get(order_field)
			for d in self.get("items") if d.get(order_field)]))

		journal_entries = get_advance_journal_entries(party_type, party, party_account,
			amount_field, order_doctype, order_list, include_unallocated)

		payment_entries = get_advance_payment_entries(party_type, party, party_account,
			order_doctype, order_list, include_unallocated)

		res = journal_entries + payment_entries

		return res

	def validate_advance_entries(self):
		order_field = "sales_order" if self.doctype == "Sales Invoice" else "purchase_order"
		order_list = list(set([d.get(order_field)
			for d in self.get("items") if d.get(order_field)]))

		if not order_list: return

		advance_entries = self.get_advance_entries(include_unallocated=False)

		if advance_entries:
			advance_entries_against_si = [d.reference_name for d in self.get("advances")]
			for d in advance_entries:
				if not advance_entries_against_si or d.reference_name not in advance_entries_against_si:
					frappe.msgprint(_("Payment Entry {0} is linked against Order {1}, check if it should be pulled as advance in this invoice.")
						.format(d.reference_name, d.against_order))

	def update_against_document_in_jv(self):
		"""
			Links invoice and advance voucher:
				1. cancel advance voucher
				2. split into multiple rows if partially adjusted, assign against voucher
				3. submit advance voucher
		"""

		if self.doctype == "Sales Invoice":
			party_type = "Customer"
			party = self.customer
			party_account = self.debit_to
			dr_or_cr = "credit_in_account_currency"
		else:
			party_type = "Supplier"
			party = self.supplier
			party_account = self.credit_to
			dr_or_cr = "debit_in_account_currency"

		lst = []
		for d in self.get('advances'):
			if flt(d.allocated_amount) > 0:
				args = frappe._dict({
					'voucher_type': d.reference_type,
					'voucher_no' : d.reference_name,
					'voucher_detail_no' : d.reference_row,
					'against_voucher_type' : self.doctype,
					'against_voucher'  : self.name,
					'account' : party_account,
					'party_type': party_type,
					'party': party,
					'is_advance' : 'Yes',
					'dr_or_cr' : dr_or_cr,
					'unadjusted_amount' : flt(d.advance_amount),
					'allocated_amount' : flt(d.allocated_amount),
					'exchange_rate': (self.conversion_rate
						if self.party_account_currency != self.company_currency else 1),
					'grand_total': (self.base_grand_total
						if self.party_account_currency==self.company_currency else self.grand_total),
					'outstanding_amount': self.outstanding_amount
				})
				lst.append(args)

		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			reconcile_against_document(lst)

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
						frappe.throw(_("Cannot overbill for Item {0} in row {1} more than {2}. To allow over-billing, please set in Buying Settings").format(item.item_code, item.idx, max_allowed_amt))

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
			party = self.customer
		else:
			dr_or_cr = "debit_in_account_currency"
			party = self.supplier

		advance = frappe.db.sql("""
			select
				account_currency, sum({dr_or_cr}) as amount
			from
				`tabGL Entry`
			where
				against_voucher_type = %s and against_voucher = %s and party=%s
				and docstatus = 1
		""".format(dr_or_cr=dr_or_cr), (self.doctype, self.name, party), as_dict=1)

		if advance:
			advance = advance[0]
			advance_paid = flt(advance.amount, self.precision("advance_paid"))
			formatted_advance_paid = fmt_money(advance_paid, precision=self.precision("advance_paid"),
				currency=advance.account_currency)

			frappe.db.set_value(self.doctype, self.name, "party_account_currency",
				advance.account_currency)

			if advance.account_currency == self.currency:
				order_total = self.grand_total
				formatted_order_total = fmt_money(order_total, precision=self.precision("grand_total"),
					currency=advance.account_currency)
			else:
				order_total = self.base_grand_total
				formatted_order_total = fmt_money(order_total, precision=self.precision("base_grand_total"),
					currency=advance.account_currency)

			if self.currency == self.company_currency and advance_paid > order_total:
				frappe.throw(_("Total advance ({0}) against Order {1} cannot be greater than the Grand Total ({2})")
					.format(formatted_advance_paid, self.name, formatted_order_total))

			frappe.db.set_value(self.doctype, self.name, "advance_paid", advance_paid)

	@property
	def company_abbr(self):
		if not hasattr(self, "_abbr"):
			self._abbr = frappe.db.get_value("Company", self.company, "abbr")

		return self._abbr

	def validate_party(self):
		party_type, party = self.get_party()
		validate_party_frozen_disabled(party_type, party)

	def get_party(self):
		party_type = None
		if self.doctype in ("Opportunity", "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"):
			party_type = 'Customer'

		elif self.doctype in ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"):
			party_type = 'Supplier'

		elif self.meta.get_field("customer"):
			party_type = "Customer"

		elif self.meta.get_field("supplier"):
			party_type = "Supplier"

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

				# Note: not validating with gle account because we don't have the account
				# at quotation / sales order level and we shouldn't stop someone
				# from creating a sales invoice if sales order is already created

	def validate_fixed_asset(self):
		for d in self.get("items"):
			if d.is_fixed_asset:
				if d.qty > 1:
					frappe.throw(_("Row #{0}: Qty must be 1, as item is a fixed asset. Please use separate row for multiple qty.").format(d.idx))

				if d.meta.get_field("asset"):
					if not d.asset:
						frappe.throw(_("Row #{0}: Asset is mandatory for fixed asset purchase/sale")
							.format(d.idx))
					else:
						asset = frappe.get_doc("Asset", d.asset)

						if asset.company != self.company:
							frappe.throw(_("Row #{0}: Asset {1} does not belong to company {2}")
								.format(d.idx, d.asset, self.company))

						elif asset.item_code != d.item_code:
							frappe.throw(_("Row #{0}: Asset {1} does not linked to Item {2}")
								.format(d.idx, d.asset, d.item_code))

						elif asset.docstatus != 1:
							frappe.throw(_("Row #{0}: Asset {1} must be submitted").format(d.idx, d.asset))

						elif self.doctype == "Purchase Invoice":
							if asset.status != "Submitted":
								frappe.throw(_("Row #{0}: Asset {1} is already {2}")
									.format(d.idx, d.asset, asset.status))
							elif getdate(asset.purchase_date) != getdate(self.posting_date):
								frappe.throw(_("Row #{0}: Posting Date must be same as purchase date {1} of asset {2}").format(d.idx, asset.purchase_date, d.asset))
							elif asset.is_existing_asset:
								frappe.throw(_("Row #{0}: Purchase Invoice cannot be made against an existing asset {1}").format(d.idx, d.asset))

						elif self.docstatus=="Sales Invoice" and self.docstatus == 1:
							if self.update_stock:
								frappe.throw(_("'Update Stock' cannot be checked for fixed asset sale"))

							elif asset.status in ("Scrapped", "Cancelled", "Sold"):
								frappe.throw(_("Row #{0}: Asset {1} cannot be submitted, it is already {2}")
									.format(d.idx, d.asset, asset.status))

	def delink_advance_entries(self, linked_doc_name):
		total_allocated_amount = 0
		for adv in self.advances:
			consider_for_total_advance = True
			if adv.reference_name == linked_doc_name:
				frappe.db.sql("""delete from `tab{0} Advance`
					where name = %s""".format(self.doctype), adv.name)
				consider_for_total_advance = False

			if consider_for_total_advance:
				total_allocated_amount += flt(adv.allocated_amount, adv.precision("allocated_amount"))

		frappe.db.set_value(self.doctype, self.name, "total_advance",
			total_allocated_amount, update_modified=False)

	def group_similar_items(self):
		group_item_qty = {}
		group_item_amount = {}

		for item in self.items:
			group_item_qty[item.item_code] = group_item_qty.get(item.item_code, 0) + item.qty
			group_item_amount[item.item_code] = group_item_amount.get(item.item_code, 0) + item.amount

		duplicate_list = []

		for item in self.items:
			if item.item_code in group_item_qty:
				item.qty = group_item_qty[item.item_code]
				item.amount = group_item_amount[item.item_code]
				del group_item_qty[item.item_code]
			else:
				duplicate_list.append(item)

		for item in duplicate_list:
			self.remove(item)

@frappe.whitelist()
def get_tax_rate(account_head):
	return frappe.db.get_value("Account", account_head, ["tax_rate", "account_name"], as_dict=True)

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

def set_balance_in_account_currency(gl_dict, account_currency=None, conversion_rate=None, company_currency=None):
	if (not conversion_rate) and (account_currency!=company_currency):
			frappe.throw(_("Account: {0} with currency: {1} can not be selected")
				.format(gl_dict.account, account_currency))

	gl_dict["account_currency"] = company_currency if account_currency==company_currency \
		else account_currency

	# set debit/credit in account currency if not provided
	if flt(gl_dict.debit) and not flt(gl_dict.debit_in_account_currency):
		gl_dict.debit_in_account_currency = gl_dict.debit if account_currency==company_currency \
			else flt(gl_dict.debit / conversion_rate, 2)

	if flt(gl_dict.credit) and not flt(gl_dict.credit_in_account_currency):
		gl_dict.credit_in_account_currency = gl_dict.credit if account_currency==company_currency \
			else flt(gl_dict.credit / conversion_rate, 2)


def get_advance_journal_entries(party_type, party, party_account, amount_field,
		order_doctype, order_list, include_unallocated=True):

	dr_or_cr = "credit_in_account_currency" if party_type=="Customer" else "debit_in_account_currency"

	conditions = []
	if include_unallocated:
		conditions.append("ifnull(t2.reference_name, '')=''")

	if order_list:
		order_condition = ', '.join(['%s'] * len(order_list))
		conditions.append(" (t2.reference_type = '{0}' and ifnull(t2.reference_name, '') in ({1}))"\
			.format(order_doctype, order_condition))

	reference_condition = " and (" + " or ".join(conditions) + ")" if conditions else ""

	journal_entries = frappe.db.sql("""
		select
			"Journal Entry" as reference_type, t1.name as reference_name,
			t1.remark as remarks, t2.{0} as amount, t2.name as reference_row,
			t2.reference_name as against_order
		from
			`tabJournal Entry` t1, `tabJournal Entry Account` t2
		where
			t1.name = t2.parent and t2.account = %s
			and t2.party_type = %s and t2.party = %s
			and t2.is_advance = 'Yes' and t1.docstatus = 1
			and {1} > 0 {2}
		order by t1.posting_date""".format(amount_field, dr_or_cr, reference_condition),
		[party_account, party_type, party] + order_list, as_dict=1)

	return list(journal_entries)

def get_advance_payment_entries(party_type, party, party_account,
		order_doctype, order_list=None, include_unallocated=True, against_all_orders=False):
	party_account_field = "paid_from" if party_type == "Customer" else "paid_to"
	payment_type = "Receive" if party_type == "Customer" else "Pay"
	payment_entries_against_order, unallocated_payment_entries = [], []

	if order_list or against_all_orders:
		if order_list:
			reference_condition = " and t2.reference_name in ({0})"\
				.format(', '.join(['%s'] * len(order_list)))
		else:
			reference_condition = ""
			order_list = []

		payment_entries_against_order = frappe.db.sql("""
			select
				"Payment Entry" as reference_type, t1.name as reference_name,
				t1.remarks, t2.allocated_amount as amount, t2.name as reference_row,
				t2.reference_name as against_order, t1.posting_date
			from `tabPayment Entry` t1, `tabPayment Entry Reference` t2
			where
				t1.name = t2.parent and t1.{0} = %s and t1.payment_type = %s
				and t1.party_type = %s and t1.party = %s and t1.docstatus = 1
				and t2.reference_doctype = %s {1}
		""".format(party_account_field, reference_condition),
		[party_account, payment_type, party_type, party, order_doctype] + order_list, as_dict=1)

	if include_unallocated:
		unallocated_payment_entries = frappe.db.sql("""
				select "Payment Entry" as reference_type, name as reference_name,
				remarks, unallocated_amount as amount
				from `tabPayment Entry`
				where
					{0} = %s and party_type = %s and party = %s and payment_type = %s
					and docstatus = 1 and unallocated_amount > 0
			""".format(party_account_field), (party_account, party_type, party, payment_type), as_dict=1)

	return list(payment_entries_against_order) + list(unallocated_payment_entries)

def update_invoice_status():
	# Daily update the status of the invoices

	frappe.db.sql(""" update `tabSales Invoice` set status = 'Overdue'
		where due_date < CURDATE() and docstatus = 1 and outstanding_amount > 0""")

	frappe.db.sql(""" update `tabPurchase Invoice` set status = 'Overdue'
		where due_date < CURDATE() and docstatus = 1 and outstanding_amount > 0""")