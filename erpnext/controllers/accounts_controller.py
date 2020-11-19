# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import json
from frappe import _, throw
from frappe.utils import (today, flt, cint, fmt_money, formatdate,
	getdate, add_days, add_months, get_last_day, nowdate, get_link_to_form)
from frappe.model.workflow import get_workflow_name, is_transition_condition_satisfied, WorkflowPermissionError
from erpnext.stock.get_item_details import get_conversion_factor, get_item_details
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.utils import get_fiscal_years, validate_fiscal_year, get_account_currency
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.buying.utils import update_last_purchase_rate
from erpnext.controllers.sales_and_purchase_return import validate_return
from erpnext.accounts.party import get_party_account_currency, validate_party_frozen_disabled
from erpnext.accounts.doctype.pricing_rule.utils import (apply_pricing_rule_on_transaction,
	apply_pricing_rule_for_free_items, get_applied_pricing_rules)
from erpnext.exceptions import InvalidCurrency
from six import text_type
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from erpnext.stock.get_item_details import get_item_warehouse, _get_item_tax_template, get_item_tax_map
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

force_item_fields = ("item_group", "brand", "stock_uom", "is_fixed_asset", "item_tax_rate", "pricing_rules")

class AccountsController(TransactionBase):
	def __init__(self, *args, **kwargs):
		super(AccountsController, self).__init__(*args, **kwargs)

	@property
	def company_currency(self):
		if not hasattr(self, "__company_currency"):
			self.__company_currency = erpnext.get_company_currency(self.company)

		return self.__company_currency

	def onload(self):
		self.set_onload("make_payment_via_journal_entry",
			frappe.db.get_single_value('Accounts Settings', 'make_payment_via_journal_entry'))

		if self.is_new():
			relevant_docs = ("Quotation", "Purchase Order", "Sales Order",
							 "Purchase Invoice", "Sales Invoice")
			if self.doctype in relevant_docs:
				self.set_payment_schedule()

	def ensure_supplier_is_not_blocked(self):
		is_supplier_payment = self.doctype == 'Payment Entry' and self.party_type == 'Supplier'
		is_buying_invoice = self.doctype in ['Purchase Invoice', 'Purchase Order']
		supplier = None
		supplier_name = None

		if is_buying_invoice or is_supplier_payment:
			supplier_name = self.supplier if is_buying_invoice else self.party
			supplier = frappe.get_doc('Supplier', supplier_name)

		if supplier and supplier_name and supplier.on_hold:
			if (is_buying_invoice and supplier.hold_type in ['All', 'Invoices']) or \
					(is_supplier_payment and supplier.hold_type in ['All', 'Payments']):
				if not supplier.release_date or getdate(nowdate()) <= supplier.release_date:
					frappe.msgprint(
						_('{0} is blocked so this transaction cannot proceed'.format(supplier_name)), raise_exception=1)

	def validate(self):
		if not self.get('is_return'):
			self.validate_qty_is_not_zero()

		if self.get("_action") and self._action != "update_after_submit":
			self.set_missing_values(for_validate=True)

		self.ensure_supplier_is_not_blocked()

		self.validate_date_with_fiscal_year()

		if self.meta.get_field("currency"):
			self.calculate_taxes_and_totals()

			if not self.meta.get_field("is_return") or not self.is_return:
				self.validate_value("base_grand_total", ">=", 0)

			validate_return(self)
			self.set_total_in_words()

		self.validate_all_documents_schedule()

		if self.meta.get_field("taxes_and_charges"):
			self.validate_enabled_taxes_and_charges()
			self.validate_tax_account_company()

		self.validate_party()
		self.validate_currency()

		if self.doctype == 'Purchase Invoice':
			self.calculate_paid_amount()

		if self.doctype in ['Purchase Invoice', 'Sales Invoice']:
			pos_check_field = "is_pos" if self.doctype=="Sales Invoice" else "is_paid"
			if cint(self.allocate_advances_automatically) and not cint(self.get(pos_check_field)):
				self.set_advances()

			if self.is_return:
				self.validate_qty()
			else:
				self.validate_deferred_start_and_end_date()

		validate_regional(self)
		if self.doctype != 'Material Request':
			apply_pricing_rule_on_transaction(self)

	def validate_deferred_start_and_end_date(self):
		for d in self.items:
			if d.get("enable_deferred_revenue") or d.get("enable_deferred_expense"):
				if not (d.service_start_date and d.service_end_date):
					frappe.throw(_("Row #{0}: Service Start and End Date is required for deferred accounting").format(d.idx))
				elif getdate(d.service_start_date) > getdate(d.service_end_date):
					frappe.throw(_("Row #{0}: Service Start Date cannot be greater than Service End Date").format(d.idx))
				elif getdate(self.posting_date) > getdate(d.service_end_date):
					frappe.throw(_("Row #{0}: Service End Date cannot be before Invoice Posting Date").format(d.idx))

	def validate_invoice_documents_schedule(self):
		self.validate_payment_schedule_dates()
		self.set_due_date()
		self.set_payment_schedule()
		self.validate_payment_schedule_amount()
		self.validate_due_date()
		self.validate_advance_entries()

	def validate_non_invoice_documents_schedule(self):
		self.set_payment_schedule()
		self.validate_payment_schedule_dates()
		self.validate_payment_schedule_amount()

	def validate_all_documents_schedule(self):
		if self.doctype in ("Sales Invoice", "Purchase Invoice") and not self.is_return:
			self.validate_invoice_documents_schedule()
		elif self.doctype in ("Quotation", "Purchase Order", "Sales Order"):
			self.validate_non_invoice_documents_schedule()

	def before_print(self):
		if self.doctype in ['Purchase Order', 'Sales Order', 'Sales Invoice', 'Purchase Invoice',
							'Supplier Quotation', 'Purchase Receipt', 'Delivery Note', 'Quotation']:
			if self.get("group_same_items"):
				self.group_similar_items()

			df = self.meta.get_field("discount_amount")
			if self.get("discount_amount") and hasattr(self, "taxes") and not len(self.taxes):
				df.set("print_hide", 0)
				self.discount_amount = -self.discount_amount
			else:
				df.set("print_hide", 1)

	def calculate_paid_amount(self):
		if hasattr(self, "is_pos") or hasattr(self, "is_paid"):
			is_paid = self.get("is_pos") or self.get("is_paid")

			if is_paid:
				if not self.cash_bank_account:
					# show message that the amount is not paid
					frappe.throw(_("Note: Payment Entry will not be created since 'Cash or Bank Account' was not specified"))

				if cint(self.is_return) and self.grand_total > self.paid_amount:
					self.paid_amount = flt(flt(self.grand_total), self.precision("paid_amount"))

				elif not flt(self.paid_amount) and flt(self.outstanding_amount) > 0:
					self.paid_amount = flt(flt(self.outstanding_amount), self.precision("paid_amount"))

				self.base_paid_amount = flt(self.paid_amount * self.conversion_rate,
										self.precision("base_paid_amount"))

	def set_missing_values(self, for_validate=False):
		if frappe.flags.in_test:
			for fieldname in ["posting_date", "transaction_date"]:
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
		if self.meta.get_field("fiscal_year"):
			date_field = ""
			if self.meta.get_field("posting_date"):
				date_field = "posting_date"
			elif self.meta.get_field("transaction_date"):
				date_field = "transaction_date"

			if date_field and self.get(date_field):
				validate_fiscal_year(self.get(date_field), self.fiscal_year, self.company,
									 self.meta.get_label(date_field), self)

	def validate_due_date(self):
		if self.get('is_pos'): return

		from erpnext.accounts.party import validate_due_date
		if self.doctype == "Sales Invoice":
			if not self.due_date:
				frappe.throw(_("Due Date is mandatory"))

			validate_due_date(self.posting_date, self.due_date,
				"Customer", self.customer, self.company, self.payment_terms_template)
		elif self.doctype == "Purchase Invoice":
			validate_due_date(self.bill_date or self.posting_date, self.due_date,
				"Supplier", self.supplier, self.company, self.bill_date, self.payment_terms_template)

	def set_price_list_currency(self, buying_or_selling):
		if self.meta.get_field("posting_date"):
			transaction_date = self.posting_date
		else:
			transaction_date = self.transaction_date

		if self.meta.get_field("currency"):
			# price list part
			if buying_or_selling.lower() == "selling":
				fieldname = "selling_price_list"
				args = "for_selling"
			else:
				fieldname = "buying_price_list"
				args = "for_buying"

			if self.meta.get_field(fieldname) and self.get(fieldname):
				self.price_list_currency = frappe.db.get_value("Price List",
															   self.get(fieldname), "currency")

				if self.price_list_currency == self.company_currency:
					self.plc_conversion_rate = 1.0

				elif not self.plc_conversion_rate:
					self.plc_conversion_rate = get_exchange_rate(self.price_list_currency,
																 self.company_currency, transaction_date, args)

			# currency
			if not self.currency:
				self.currency = self.price_list_currency
				self.conversion_rate = self.plc_conversion_rate
			elif self.currency == self.company_currency:
				self.conversion_rate = 1.0
			elif not self.conversion_rate:
				self.conversion_rate = get_exchange_rate(self.currency,
														 self.company_currency, transaction_date, args)

	def set_missing_item_details(self, for_validate=False):
		"""set missing item values"""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if hasattr(self, "items"):
			parent_dict = {}
			for fieldname in self.meta.get_valid_columns():
				parent_dict[fieldname] = self.get(fieldname)

			if self.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
				document_type = "{} Item".format(self.doctype)
				parent_dict.update({"document_type": document_type})

			# party_name field used for customer in quotation
			if self.doctype == "Quotation" and self.quotation_to == "Customer" and parent_dict.get("party_name"):
				parent_dict.update({"customer": parent_dict.get("party_name")})

			for item in self.get("items"):
				if item.get("item_code"):
					args = parent_dict.copy()
					args.update(item.as_dict())

					args["doctype"] = self.doctype
					args["name"] = self.name
					args["child_docname"] = item.name

					if not args.get("transaction_date"):
						args["transaction_date"] = args.get("posting_date")

					if self.get("is_subcontracted"):
						args["is_subcontracted"] = self.is_subcontracted

					ret = get_item_details(args, self, for_validate=True, overwrite_warehouse=False)

					for fieldname, value in ret.items():
						if item.meta.get_field(fieldname) and value is not None:
							if (item.get(fieldname) is None or fieldname in force_item_fields):
								item.set(fieldname, value)

							elif fieldname in ['cost_center', 'conversion_factor'] and not item.get(fieldname):
								item.set(fieldname, value)

							elif fieldname == "serial_no":
								# Ensure that serial numbers are matched against Stock UOM
								item_conversion_factor = item.get("conversion_factor") or 1.0
								item_qty = abs(item.get("qty")) * item_conversion_factor

								if item_qty != len(get_serial_nos(item.get('serial_no'))):
									item.set(fieldname, value)

					if self.doctype in ["Purchase Invoice", "Sales Invoice"] and item.meta.get_field('is_fixed_asset'):
						item.set('is_fixed_asset', ret.get('is_fixed_asset', 0))

					if ret.get("pricing_rules"):
						self.apply_pricing_rule_on_items(item, ret)

			if self.doctype == "Purchase Invoice":
				self.set_expense_account(for_validate)

	def apply_pricing_rule_on_items(self, item, pricing_rule_args):
		if not pricing_rule_args.get("validate_applied_rule", 0):
			# if user changed the discount percentage then set user's discount percentage ?
			if pricing_rule_args.get("price_or_product_discount") == 'Price':
				item.set("pricing_rules", pricing_rule_args.get("pricing_rules"))
				item.set("discount_percentage", pricing_rule_args.get("discount_percentage"))
				item.set("discount_amount", pricing_rule_args.get("discount_amount"))
				if pricing_rule_args.get("pricing_rule_for") == "Rate":
					item.set("price_list_rate", pricing_rule_args.get("price_list_rate"))

				if item.get("price_list_rate"):
					item.rate = flt(item.price_list_rate *
						(1.0 - (flt(item.discount_percentage) / 100.0)), item.precision("rate"))

					if item.get('discount_amount'):
						item.rate = item.price_list_rate - item.discount_amount

			elif pricing_rule_args.get('free_item_data'):
				apply_pricing_rule_for_free_items(self, pricing_rule_args.get('free_item_data'))

		elif pricing_rule_args.get("validate_applied_rule"):
			for pricing_rule in get_applied_pricing_rules(item.get('pricing_rules')):
				pricing_rule_doc = frappe.get_cached_doc("Pricing Rule", pricing_rule)
				for field in ['discount_percentage', 'discount_amount', 'rate']:
					if item.get(field) < pricing_rule_doc.get(field):
						title = get_link_to_form("Pricing Rule", pricing_rule)

						frappe.msgprint(_("Row {0}: user has not applied the rule {1} on the item {2}")
							.format(item.idx, frappe.bold(title), frappe.bold(item.item_code)))

	def set_taxes(self):
		if not self.meta.get_field("taxes"):
			return

		tax_master_doctype = self.meta.get_field("taxes_and_charges").options

		if (self.is_new() or self.is_pos_profile_changed()) and not self.get("taxes"):
			if self.company and not self.get("taxes_and_charges"):
				# get the default tax master
				self.taxes_and_charges = frappe.db.get_value(tax_master_doctype,
															 {"is_default": 1, 'company': self.company})

			self.append_taxes_from_master(tax_master_doctype)

	def is_pos_profile_changed(self):
		if (self.doctype == 'Sales Invoice' and self.is_pos and
				self.pos_profile != frappe.db.get_value('Sales Invoice', self.name, 'pos_profile')):
			return True

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

	def validate_tax_account_company(self):
		for d in self.get("taxes"):
			if d.account_head:
				tax_account_company = frappe.db.get_value("Account", d.account_head, "company")
				if tax_account_company != self.company:
					frappe.throw(_("Row #{0}: Account {1} does not belong to company {2}")
								 .format(d.idx, d.account_head, self.company))

	def get_gl_dict(self, args, account_currency=None, item=None):
		"""this method populates the common properties of a gl entry record"""

		posting_date = args.get('posting_date') or self.get('posting_date')
		fiscal_years = get_fiscal_years(posting_date, company=self.company)
		if len(fiscal_years) > 1:
			frappe.throw(_("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(
				formatdate(posting_date)))
		else:
			fiscal_year = fiscal_years[0][0]

		gl_dict = frappe._dict({
			'company': self.company,
			'posting_date': posting_date,
			'fiscal_year': fiscal_year,
			'voucher_type': self.doctype,
			'voucher_no': self.name,
			'remarks': self.get("remarks") or self.get("remark"),
			'debit': 0,
			'credit': 0,
			'debit_in_account_currency': 0,
			'credit_in_account_currency': 0,
			'is_opening': self.get("is_opening") or "No",
			'party_type': None,
			'party': None,
			'project': self.get("project")
		})

		accounting_dimensions = get_accounting_dimensions()
		dimension_dict = frappe._dict()

		for dimension in accounting_dimensions:
			dimension_dict[dimension] = self.get(dimension)
			if item and item.get(dimension):
				dimension_dict[dimension] = item.get(dimension)

		gl_dict.update(dimension_dict)
		gl_dict.update(args)

		if not account_currency:
			account_currency = get_account_currency(gl_dict.account)

		if gl_dict.account and self.doctype not in ["Journal Entry",
													"Period Closing Voucher", "Payment Entry"]:
			self.validate_account_currency(gl_dict.account, account_currency)
			set_balance_in_account_currency(gl_dict, account_currency, self.get("conversion_rate"),
											self.company_currency)

		return gl_dict

	def validate_qty_is_not_zero(self):
		if self.doctype != "Purchase Receipt":
			for item in self.items:
				if not item.qty:
					frappe.throw(_("Item quantity can not be zero"))

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

	def apply_shipping_rule(self):
		if self.shipping_rule:
			shipping_rule = frappe.get_doc("Shipping Rule", self.shipping_rule)
			shipping_rule.apply(self)
			self.calculate_taxes_and_totals()

	def get_shipping_address(self):
		'''Returns Address object from shipping address fields if present'''

		# shipping address fields can be `shipping_address_name` or `shipping_address`
		# try getting value from both

		for fieldname in ('shipping_address_name', 'shipping_address'):
			shipping_field = self.meta.get_field(fieldname)
			if shipping_field and shipping_field.fieldtype == 'Link':
				if self.get(fieldname):
					return frappe.get_doc('Address', self.get(fieldname))

		return {}

	def set_advances(self):
		"""Returns list of advances against Account, Party, Reference"""

		res = self.get_advance_entries()

		self.set("advances", [])
		advance_allocated = 0
		for d in res:
			if d.against_order:
				allocated_amount = flt(d.amount)
			else:
				amount = self.rounded_total or self.grand_total
				allocated_amount = min(amount - advance_allocated, d.amount)
			advance_allocated += flt(allocated_amount)

			self.append("advances", {
				"doctype": self.doctype + " Advance",
				"reference_type": d.reference_type,
				"reference_name": d.reference_name,
				"reference_row": d.reference_row,
				"remarks": d.remarks,
				"advance_amount": flt(d.amount),
				"allocated_amount": allocated_amount
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

	def is_inclusive_tax(self):
		is_inclusive = cint(frappe.db.get_single_value("Accounts Settings", "show_inclusive_tax_in_print"))

		if is_inclusive:
			is_inclusive = 0
			if self.get("taxes", filters={"included_in_print_rate": 1}):
				is_inclusive = 1

		return is_inclusive

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
					frappe.msgprint(_(
						"Payment Entry {0} is linked against Order {1}, check if it should be pulled as advance in this invoice.")
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
					'voucher_no': d.reference_name,
					'voucher_detail_no': d.reference_row,
					'against_voucher_type': self.doctype,
					'against_voucher': self.name,
					'account': party_account,
					'party_type': party_type,
					'party': party,
					'is_advance': 'Yes',
					'dr_or_cr': dr_or_cr,
					'unadjusted_amount': flt(d.advance_amount),
					'allocated_amount': flt(d.allocated_amount),
					'exchange_rate': (self.conversion_rate
						if self.party_account_currency != self.company_currency else 1),
					'grand_total': (self.base_grand_total
						if self.party_account_currency == self.company_currency else self.grand_total),
					'outstanding_amount': self.outstanding_amount
				})
				lst.append(args)

		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			reconcile_against_document(lst)

	def on_cancel(self):
		from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries

		if self.doctype in ["Sales Invoice", "Purchase Invoice"]:
			if frappe.db.get_single_value('Accounts Settings', 'unlink_payment_on_cancellation_of_invoice'):
				unlink_ref_doc_from_payment_entries(self)

		elif self.doctype in ["Sales Order", "Purchase Order"]:
			if frappe.db.get_single_value('Accounts Settings', 'unlink_advance_payment_on_cancelation_of_order'):
				unlink_ref_doc_from_payment_entries(self)

	def validate_multiple_billing(self, ref_dt, item_ref_dn, based_on, parentfield):
		from erpnext.controllers.status_updater import get_allowance_for
		item_allowance = {}
		global_qty_allowance, global_amount_allowance = None, None

		for item in self.get("items"):
			if item.get(item_ref_dn):
				ref_amt = flt(frappe.db.get_value(ref_dt + " Item",
					item.get(item_ref_dn), based_on), self.precision(based_on, item))
				if not ref_amt:
					frappe.msgprint(
						_("Warning: System will not check overbilling since amount for Item {0} in {1} is zero")
							.format(item.item_code, ref_dt))
				else:
					already_billed = frappe.db.sql("""
						select sum(%s)
						from `tab%s`
						where %s=%s and docstatus=1 and parent != %s
					""" % (based_on, self.doctype + " Item", item_ref_dn, '%s', '%s'),
					   (item.get(item_ref_dn), self.name))[0][0]

					total_billed_amt = flt(flt(already_billed) + flt(item.get(based_on)),
						self.precision(based_on, item))

					allowance, item_allowance, global_qty_allowance, global_amount_allowance = \
						get_allowance_for(item.item_code, item_allowance, global_qty_allowance, global_amount_allowance, "amount")

					max_allowed_amt = flt(ref_amt * (100 + allowance) / 100)

					if total_billed_amt < 0 and max_allowed_amt < 0:
						# while making debit note against purchase return entry(purchase receipt) getting overbill error
						total_billed_amt = abs(total_billed_amt)
						max_allowed_amt = abs(max_allowed_amt)

					if total_billed_amt - max_allowed_amt > 0.01:
						frappe.throw(_("Cannot overbill for Item {0} in row {1} more than {2}. To allow over-billing, please set allowance in Accounts Settings")
							.format(item.item_code, item.idx, max_allowed_amt))

	def get_company_default(self, fieldname):
		from erpnext.accounts.utils import get_company_default
		return get_company_default(self.company, fieldname)

	def get_stock_items(self):
		stock_items = []
		item_codes = list(set(item.item_code for item in self.get("items")))
		if item_codes:
			stock_items = [r[0] for r in frappe.db.sql("""
				select name from `tabItem`
				where name in (%s) and is_stock_item=1
			""" % (", ".join((["%s"] * len(item_codes))),), item_codes)]

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
				order_total = self.get("rounded_total") or self.grand_total
				precision = "rounded_total" if self.get("rounded_total") else "grand_total"
			else:
				order_total = self.get("base_rounded_total") or self.base_grand_total
				precision = "base_rounded_total" if self.get("base_rounded_total") else "base_grand_total"

			formatted_order_total = fmt_money(order_total, precision=self.precision(precision),
											  currency=advance.account_currency)

			if self.currency == self.company_currency and advance_paid > order_total:
				frappe.throw(_("Total advance ({0}) against Order {1} cannot be greater than the Grand Total ({2})")
							 .format(formatted_advance_paid, self.name, formatted_order_total))

			frappe.db.set_value(self.doctype, self.name, "advance_paid", advance_paid)

	@property
	def company_abbr(self):
		if not hasattr(self, "_abbr"):
			self._abbr = frappe.db.get_value('Company',  self.company,  "abbr")

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
		# to update serial number in print
		count = 0

		for item in self.items:
			group_item_qty[item.item_code] = group_item_qty.get(item.item_code, 0) + item.qty
			group_item_amount[item.item_code] = group_item_amount.get(item.item_code, 0) + item.amount

		duplicate_list = []
		for item in self.items:
			if item.item_code in group_item_qty:
				count += 1
				item.qty = group_item_qty[item.item_code]
				item.amount = group_item_amount[item.item_code]

				if item.qty:
					item.rate = flt(flt(item.amount) / flt(item.qty), item.precision("rate"))
				else:
					item.rate = 0

				item.idx = count
				del group_item_qty[item.item_code]
			else:
				duplicate_list.append(item)
		for item in duplicate_list:
			self.remove(item)

	def set_payment_schedule(self):
		if self.doctype == 'Sales Invoice' and self.is_pos:
			self.payment_terms_template = ''
			return

		posting_date = self.get("bill_date") or self.get("posting_date") or self.get("transaction_date")
		date = self.get("due_date")
		due_date = date or posting_date
		grand_total = self.get("rounded_total") or self.grand_total
		if self.doctype in ("Sales Invoice", "Purchase Invoice"):
			grand_total = grand_total - flt(self.write_off_amount)

		if self.get("total_advance"):
			grand_total -= self.get("total_advance")

		if not self.get("payment_schedule"):
			if self.get("payment_terms_template"):
				data = get_payment_terms(self.payment_terms_template, posting_date, grand_total)
				for item in data:
					self.append("payment_schedule", item)
			else:
				data = dict(due_date=due_date, invoice_portion=100, payment_amount=grand_total)
				self.append("payment_schedule", data)
		else:
			for d in self.get("payment_schedule"):
				if d.invoice_portion:
					d.payment_amount = flt(grand_total * flt(d.invoice_portion) / 100, d.precision('payment_amount'))

	def set_due_date(self):
		due_dates = [d.due_date for d in self.get("payment_schedule") if d.due_date]
		if due_dates:
			self.due_date = max(due_dates)

	def validate_payment_schedule_dates(self):
		dates = []
		li = []

		if self.doctype == 'Sales Invoice' and self.is_pos: return

		for d in self.get("payment_schedule"):
			if self.doctype == "Sales Order" and getdate(d.due_date) < getdate(self.transaction_date):
				frappe.throw(_("Row {0}: Due Date in the Payment Terms table cannot be before Posting Date").format(d.idx))
			elif d.due_date in dates:
				li.append(_("{0} in row {1}").format(d.due_date, d.idx))
			dates.append(d.due_date)

		if li:
			duplicates = '<br>' + '<br>'.join(li)
			frappe.throw(_("Rows with duplicate due dates in other rows were found: {0}").format(duplicates))

	def validate_payment_schedule_amount(self):
		if self.doctype == 'Sales Invoice' and self.is_pos: return

		if self.get("payment_schedule"):
			total = 0
			for d in self.get("payment_schedule"):
				total += flt(d.payment_amount)
			total = flt(total, self.precision("grand_total"))

			grand_total = flt(self.get("rounded_total") or self.grand_total, self.precision('grand_total'))
			if self.get("total_advance"):
				grand_total -= self.get("total_advance")

			if self.doctype in ("Sales Invoice", "Purchase Invoice"):
				grand_total = grand_total - flt(self.write_off_amount)
			if total != flt(grand_total, self.precision("grand_total")):
				frappe.throw(_("Total Payment Amount in Payment Schedule must be equal to Grand / Rounded Total"))

	def is_rounded_total_disabled(self):
		if self.meta.get_field("disable_rounded_total"):
			return self.disable_rounded_total
		else:
			return frappe.db.get_single_value("Global Defaults", "disable_rounded_total")

@frappe.whitelist()
def get_tax_rate(account_head):
	return frappe.db.get_value("Account", account_head, ["tax_rate", "account_name"], as_dict=True)


@frappe.whitelist()
def get_default_taxes_and_charges(master_doctype, tax_template=None, company=None):
	if not company: return {}

	if tax_template and company:
		tax_template_company = frappe.db.get_value(master_doctype, tax_template, "company")
		if tax_template_company == company:
			return

	default_tax = frappe.db.get_value(master_doctype, {"is_default": 1, "company": company})

	return {
		'taxes_and_charges': default_tax,
		'taxes': get_taxes_and_charges(master_doctype, default_tax)
	}


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

	company_currency = frappe.get_cached_value('Company',  company,  "default_currency")

	if not conversion_rate:
		throw(_("{0} is mandatory. Maybe Currency Exchange record is not created for {1} to {2}.").format(
			conversion_rate_label, currency, company_currency))


def validate_taxes_and_charges(tax):
	if tax.charge_type in ['Actual', 'On Net Total'] and tax.row_id:
		frappe.throw(_("Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'"))
	elif tax.charge_type in ['On Previous Row Amount', 'On Previous Row Total']:
		if cint(tax.idx) == 1:
			frappe.throw(
				_("Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"))
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
			frappe.throw(_("Valuation type charges can not be marked as Inclusive"))


def set_balance_in_account_currency(gl_dict, account_currency=None, conversion_rate=None, company_currency=None):
	if (not conversion_rate) and (account_currency != company_currency):
		frappe.throw(_("Account: {0} with currency: {1} can not be selected")
					 .format(gl_dict.account, account_currency))

	gl_dict["account_currency"] = company_currency if account_currency == company_currency \
		else account_currency

	# set debit/credit in account currency if not provided
	if flt(gl_dict.debit) and not flt(gl_dict.debit_in_account_currency):
		gl_dict.debit_in_account_currency = gl_dict.debit if account_currency == company_currency \
			else flt(gl_dict.debit / conversion_rate, 2)

	if flt(gl_dict.credit) and not flt(gl_dict.credit_in_account_currency):
		gl_dict.credit_in_account_currency = gl_dict.credit if account_currency == company_currency \
			else flt(gl_dict.credit / conversion_rate, 2)


def get_advance_journal_entries(party_type, party, party_account, amount_field,
								order_doctype, order_list, include_unallocated=True):
	dr_or_cr = "credit_in_account_currency" if party_type == "Customer" else "debit_in_account_currency"

	conditions = []
	if include_unallocated:
		conditions.append("ifnull(t2.reference_name, '')=''")

	if order_list:
		order_condition = ', '.join(['%s'] * len(order_list))
		conditions.append(" (t2.reference_type = '{0}' and ifnull(t2.reference_name, '') in ({1}))" \
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


def get_advance_payment_entries(party_type, party, party_account, order_doctype,
		order_list=None, include_unallocated=True, against_all_orders=False, limit=None):
	party_account_field = "paid_from" if party_type == "Customer" else "paid_to"
	currency_field = "paid_from_account_currency" if party_type == "Customer" else "paid_to_account_currency"
	payment_type = "Receive" if party_type == "Customer" else "Pay"
	payment_entries_against_order, unallocated_payment_entries = [], []
	limit_cond = "limit %s" % limit if limit else ""

	if order_list or against_all_orders:
		if order_list:
			reference_condition = " and t2.reference_name in ({0})" \
				.format(', '.join(['%s'] * len(order_list)))
		else:
			reference_condition = ""
			order_list = []

		payment_entries_against_order = frappe.db.sql("""
			select
				"Payment Entry" as reference_type, t1.name as reference_name,
				t1.remarks, t2.allocated_amount as amount, t2.name as reference_row,
				t2.reference_name as against_order, t1.posting_date,
				t1.{0} as currency
			from `tabPayment Entry` t1, `tabPayment Entry Reference` t2
			where
				t1.name = t2.parent and t1.{1} = %s and t1.payment_type = %s
				and t1.party_type = %s and t1.party = %s and t1.docstatus = 1
				and t2.reference_doctype = %s {2}
			order by t1.posting_date {3}
		""".format(currency_field, party_account_field, reference_condition, limit_cond),
													  [party_account, payment_type, party_type, party,
													   order_doctype] + order_list, as_dict=1)

	if include_unallocated:
		unallocated_payment_entries = frappe.db.sql("""
				select "Payment Entry" as reference_type, name as reference_name,
				remarks, unallocated_amount as amount
				from `tabPayment Entry`
				where
					{0} = %s and party_type = %s and party = %s and payment_type = %s
					and docstatus = 1 and unallocated_amount > 0
				order by posting_date {1}
			""".format(party_account_field, limit_cond), (party_account, party_type, party, payment_type), as_dict=1)

	return list(payment_entries_against_order) + list(unallocated_payment_entries)


def update_invoice_status():
	# Daily update the status of the invoices

	frappe.db.sql(""" update `tabSales Invoice` set status = 'Overdue'
		where due_date < CURDATE() and docstatus = 1 and outstanding_amount > 0""")

	frappe.db.sql(""" update `tabPurchase Invoice` set status = 'Overdue'
		where due_date < CURDATE() and docstatus = 1 and outstanding_amount > 0""")


@frappe.whitelist()
def get_payment_terms(terms_template, posting_date=None, grand_total=None, bill_date=None):
	if not terms_template:
		return

	terms_doc = frappe.get_doc("Payment Terms Template", terms_template)

	schedule = []
	for d in terms_doc.get("terms"):
		term_details = get_payment_term_details(d, posting_date, grand_total, bill_date)
		schedule.append(term_details)

	return schedule


@frappe.whitelist()
def get_payment_term_details(term, posting_date=None, grand_total=None, bill_date=None):
	term_details = frappe._dict()
	if isinstance(term, text_type):
		term = frappe.get_doc("Payment Term", term)
	else:
		term_details.payment_term = term.payment_term
	term_details.description = term.description
	term_details.invoice_portion = term.invoice_portion
	term_details.payment_amount = flt(term.invoice_portion) * flt(grand_total) / 100
	if bill_date:
		term_details.due_date = get_due_date(term, bill_date)
	elif posting_date:
		term_details.due_date = get_due_date(term, posting_date)

	if getdate(term_details.due_date) < getdate(posting_date):
		term_details.due_date = posting_date
	term_details.mode_of_payment = term.mode_of_payment

	return term_details


def get_due_date(term, posting_date=None, bill_date=None):
	due_date = None
	date = bill_date or posting_date
	if term.due_date_based_on == "Day(s) after invoice date":
		due_date = add_days(date, term.credit_days)
	elif term.due_date_based_on == "Day(s) after the end of the invoice month":
		due_date = add_days(get_last_day(date), term.credit_days)
	elif term.due_date_based_on == "Month(s) after the end of the invoice month":
		due_date = add_months(get_last_day(date), term.credit_months)
	return due_date


def get_supplier_block_status(party_name):
	"""
	Returns a dict containing the values of `on_hold`, `release_date` and `hold_type` of
	a `Supplier`
	"""
	supplier = frappe.get_doc('Supplier', party_name)
	info = {
		'on_hold': supplier.on_hold,
		'release_date': supplier.release_date,
		'hold_type': supplier.hold_type
	}
	return info

def set_child_tax_template_and_map(item, child_item, parent_doc):
	args = {
			'item_code': item.item_code,
			'posting_date': parent_doc.transaction_date,
			'tax_category': parent_doc.get('tax_category'),
			'company': parent_doc.get('company')
		}

	child_item.item_tax_template = _get_item_tax_template(args, item.taxes)
	if child_item.get("item_tax_template"):
		child_item.item_tax_rate = get_item_tax_map(parent_doc.get('company'), child_item.item_tax_template, as_json=True)

def add_taxes_from_tax_template(child_item, parent_doc):
	add_taxes_from_item_tax_template = frappe.db.get_single_value("Accounts Settings", "add_taxes_from_item_tax_template")

	if child_item.get("item_tax_rate") and add_taxes_from_item_tax_template:
		tax_map = json.loads(child_item.get("item_tax_rate"))
		for tax_type in tax_map:
			tax_rate = flt(tax_map[tax_type])
			taxes = parent_doc.get('taxes') or []
			# add new row for tax head only if missing
			found = any(tax.account_head == tax_type for tax in taxes)
			if not found:
				tax_row = parent_doc.append("taxes", {})
				tax_row.update({
					"description" : str(tax_type).split(' - ')[0],
					"charge_type" : "On Net Total",
					"account_head" : tax_type,
					"rate" : tax_rate
				})
				if parent_doc.doctype == "Purchase Order":
					tax_row.update({
						"category" : "Total",
						"add_deduct_tax" : "Add"
					})
				tax_row.db_insert()

def set_sales_order_defaults(parent_doctype, parent_doctype_name, child_docname, trans_item):
	"""
	Returns a Sales Order Item child item containing the default values
	"""
	p_doc = frappe.get_doc(parent_doctype, parent_doctype_name)
	child_item = frappe.new_doc('Sales Order Item', p_doc, child_docname)
	item = frappe.get_doc("Item", trans_item.get('item_code'))
	child_item.item_code = item.item_code
	child_item.item_name = item.item_name
	child_item.description = item.description
	child_item.delivery_date = trans_item.get('delivery_date') or p_doc.delivery_date
	child_item.conversion_factor = flt(trans_item.get('conversion_factor')) or get_conversion_factor(item.item_code, item.stock_uom).get("conversion_factor") or 1.0
	child_item.uom = item.stock_uom
	set_child_tax_template_and_map(item, child_item, p_doc)
	add_taxes_from_tax_template(child_item, p_doc)
	child_item.warehouse = get_item_warehouse(item, p_doc, overwrite_warehouse=True)
	if not child_item.warehouse:
		frappe.throw(_("Cannot find {} for item {}. Please set the same in Item Master or Stock Settings.")
			.format(frappe.bold("default warehouse"), frappe.bold(item.item_code)))
	return child_item


def set_purchase_order_defaults(parent_doctype, parent_doctype_name, child_docname, trans_item):
	"""
	Returns a Purchase Order Item child item containing the default values
	"""
	p_doc = frappe.get_doc(parent_doctype, parent_doctype_name)
	child_item = frappe.new_doc('Purchase Order Item', p_doc, child_docname)
	item = frappe.get_doc("Item", trans_item.get('item_code'))
	child_item.item_code = item.item_code
	child_item.item_name = item.item_name
	child_item.description = item.description
	child_item.schedule_date = trans_item.get('schedule_date') or p_doc.schedule_date
	child_item.conversion_factor = flt(trans_item.get('conversion_factor')) or get_conversion_factor(item.item_code, item.stock_uom).get("conversion_factor") or 1.0
	child_item.uom = item.stock_uom
	child_item.base_rate = 1 # Initiallize value will update in parent validation
	child_item.base_amount = 1 # Initiallize value will update in parent validation
	set_child_tax_template_and_map(item, child_item, p_doc)
	add_taxes_from_tax_template(child_item, p_doc)
	return child_item

def validate_and_delete_children(parent, data):
	deleted_children = []
	updated_item_names = [d.get("docname") for d in data]
	for item in parent.items:
		if item.name not in updated_item_names:
			deleted_children.append(item)

	for d in deleted_children:
		if parent.doctype == "Sales Order":
			if flt(d.delivered_qty):
				frappe.throw(_("Row #{0}: Cannot delete item {1} which has already been delivered").format(d.idx, d.item_code))
			if flt(d.work_order_qty):
				frappe.throw(_("Row #{0}: Cannot delete item {1} which has work order assigned to it.").format(d.idx, d.item_code))
			if flt(d.ordered_qty):
				frappe.throw(_("Row #{0}: Cannot delete item {1} which is assigned to customer's purchase order.").format(d.idx, d.item_code))

		if parent.doctype == "Purchase Order" and flt(d.received_qty):
			frappe.throw(_("Row #{0}: Cannot delete item {1} which has already been received").format(d.idx, d.item_code))

		if flt(d.billed_amt):
			frappe.throw(_("Row #{0}: Cannot delete item {1} which has already been billed.").format(d.idx, d.item_code))

		d.cancel()
		d.delete()

@frappe.whitelist()
def update_child_qty_rate(parent_doctype, trans_items, parent_doctype_name, child_docname="items"):
	def check_doc_permissions(doc, perm_type='create'):
		try:
			doc.check_permission(perm_type)
		except frappe.PermissionError:
			actions = { 'create': 'add', 'write': 'update'}

			frappe.throw(_("You do not have permissions to {} items in a {}.")
				.format(actions[perm_type], parent_doctype), title=_("Insufficient Permissions"))

	def validate_workflow_conditions(doc):
		workflow = get_workflow_name(doc.doctype)
		if not workflow:
			return

		workflow_doc = frappe.get_doc("Workflow", workflow)
		current_state = doc.get(workflow_doc.workflow_state_field)
		roles = frappe.get_roles()

		transitions = []
		for transition in workflow_doc.transitions:
			if transition.next_state == current_state and transition.allowed in roles:
				if not is_transition_condition_satisfied(transition, doc):
					continue
				transitions.append(transition.as_dict())

		if not transitions:
			frappe.throw(
				_("You are not allowed to update as per the conditions set in {} Workflow.").format(get_link_to_form("Workflow", workflow)),
				title=_("Insufficient Permissions")
			)

	def get_new_child_item(item_row):
		new_child_function = set_sales_order_defaults if parent_doctype == "Sales Order" else set_purchase_order_defaults
		return new_child_function(parent_doctype, parent_doctype_name, child_docname, item_row)

	def validate_quantity(child_item, d):
		if parent_doctype == "Sales Order" and flt(d.get("qty")) < flt(child_item.delivered_qty):
			frappe.throw(_("Cannot set quantity less than delivered quantity"))

		if parent_doctype == "Purchase Order" and flt(d.get("qty")) < flt(child_item.received_qty):
			frappe.throw(_("Cannot set quantity less than received quantity"))

	data = json.loads(trans_items)

	sales_doctypes = ['Sales Order', 'Sales Invoice', 'Delivery Note', 'Quotation']
	parent = frappe.get_doc(parent_doctype, parent_doctype_name)

	check_doc_permissions(parent, 'write')
	validate_and_delete_children(parent, data)

	for d in data:
		new_child_flag = False
		if not d.get("docname"):
			new_child_flag = True
			check_doc_permissions(parent, 'create')
			child_item = get_new_child_item(d)
		else:
			check_doc_permissions(parent, 'write')
			child_item = frappe.get_doc(parent_doctype + ' Item', d.get("docname"))

			prev_rate, new_rate = flt(child_item.get("rate")), flt(d.get("rate"))
			prev_qty, new_qty = flt(child_item.get("qty")), flt(d.get("qty"))
			prev_con_fac, new_con_fac = flt(child_item.get("conversion_factor")), flt(d.get("conversion_factor"))

			if parent_doctype == 'Sales Order':
				prev_date, new_date = child_item.get("delivery_date"), d.get("delivery_date")
			elif parent_doctype == 'Purchase Order':
				prev_date, new_date = child_item.get("schedule_date"), d.get("schedule_date")

			rate_unchanged = prev_rate == new_rate
			qty_unchanged = prev_qty == new_qty
			conversion_factor_unchanged = prev_con_fac == new_con_fac
			date_unchanged = prev_date == new_date if prev_date and new_date else False # in case of delivery note etc
			if rate_unchanged and qty_unchanged and conversion_factor_unchanged and date_unchanged:
				continue

		validate_quantity(child_item, d)

		child_item.qty = flt(d.get("qty"))
		rate_precision = child_item.precision("rate") or 2
		conv_fac_precision = child_item.precision("conversion_factor") or 2
		qty_precision = child_item.precision("qty") or 2

		if flt(child_item.billed_amt, rate_precision) > flt(flt(d.get("rate"), rate_precision) * flt(d.get("qty"), qty_precision), rate_precision):
			frappe.throw(_("Row #{0}: Cannot set Rate if amount is greater than billed amount for Item {1}.")
						 .format(child_item.idx, child_item.item_code))
		else:
			child_item.rate = flt(d.get("rate"), rate_precision)

		if d.get("conversion_factor"):
			if child_item.stock_uom == child_item.uom:
				child_item.conversion_factor = 1
			else:
				child_item.conversion_factor = flt(d.get('conversion_factor'), conv_fac_precision)

		if d.get("delivery_date") and parent_doctype == 'Sales Order':
			child_item.delivery_date = d.get('delivery_date')

		if d.get("schedule_date") and parent_doctype == 'Purchase Order':
			child_item.schedule_date = d.get('schedule_date')

		if flt(child_item.price_list_rate):
			if flt(child_item.rate) > flt(child_item.price_list_rate):
				#  if rate is greater than price_list_rate, set margin
				#  or set discount
				child_item.discount_percentage = 0

				if parent_doctype in sales_doctypes:
					child_item.margin_type = "Amount"
					child_item.margin_rate_or_amount = flt(child_item.rate - child_item.price_list_rate,
						child_item.precision("margin_rate_or_amount"))
					child_item.rate_with_margin = child_item.rate
			else:
				child_item.discount_percentage = flt((1 - flt(child_item.rate) / flt(child_item.price_list_rate)) * 100.0,
					child_item.precision("discount_percentage"))
				child_item.discount_amount = flt(
					child_item.price_list_rate) - flt(child_item.rate)

				if parent_doctype in sales_doctypes:
					child_item.margin_type = ""
					child_item.margin_rate_or_amount = 0
					child_item.rate_with_margin = 0

		child_item.flags.ignore_validate_update_after_submit = True
		if new_child_flag:
			parent.load_from_db()
			child_item.idx = len(parent.items) + 1
			child_item.insert()
		else:
			child_item.save()

	parent.reload()
	parent.flags.ignore_validate_update_after_submit = True
	parent.set_qty_as_per_stock_uom()
	parent.calculate_taxes_and_totals()
	if parent_doctype == "Sales Order":
		make_packing_list(parent)
		parent.set_gross_profit()
	frappe.get_doc('Authorization Control').validate_approving_authority(parent.doctype,
		parent.company, parent.base_grand_total)

	parent.set_payment_schedule()
	if parent_doctype == 'Purchase Order':
		parent.validate_minimum_order_qty()
		parent.validate_budget()
		if parent.is_against_so():
			parent.update_status_updater()
	else:
		parent.check_credit_limit()
	parent.save()

	if parent_doctype == 'Purchase Order':
		update_last_purchase_rate(parent, is_submit = 1)
		parent.update_prevdoc_status()
		parent.update_requested_qty()
		parent.update_ordered_qty()
		parent.update_ordered_and_reserved_qty()
		parent.update_receiving_percentage()
		if parent.is_subcontracted == "Yes":
			parent.update_reserved_qty_for_subcontract()
	else:
		parent.update_reserved_qty()
		parent.update_project()
		parent.update_prevdoc_status('submit')
		parent.update_delivery_status()

	parent.reload()
	validate_workflow_conditions(parent)

	parent.update_blanket_order()
	parent.update_billing_percentage()
	parent.set_status()

@erpnext.allow_regional
def validate_regional(doc):
	pass
