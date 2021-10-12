# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _, throw
from frappe.model.workflow import get_workflow_name, is_transition_condition_satisfied
from frappe.utils import (
	add_days,
	add_months,
	cint,
	flt,
	fmt_money,
	formatdate,
	get_last_day,
	get_link_to_form,
	getdate,
	nowdate,
	today,
)
from six import text_type

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.pricing_rule.utils import (
	apply_pricing_rule_for_free_items,
	apply_pricing_rule_on_transaction,
	get_applied_pricing_rules,
)
from erpnext.accounts.party import (
	get_party_account,
	get_party_account_currency,
	validate_party_frozen_disabled,
)
from erpnext.accounts.utils import get_account_currency, get_fiscal_years, validate_fiscal_year
from erpnext.buying.utils import update_last_purchase_rate
from erpnext.controllers.print_settings import (
	set_print_templates_for_item_table,
	set_print_templates_for_taxes,
)
from erpnext.controllers.sales_and_purchase_return import validate_return
from erpnext.exceptions import InvalidCurrency
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
from erpnext.stock.get_item_details import (
	_get_item_tax_template,
	get_conversion_factor,
	get_item_details,
	get_item_tax_map,
	get_item_warehouse,
)
from erpnext.utilities.transaction_base import TransactionBase


class AccountMissingError(frappe.ValidationError): pass

force_item_fields = ("item_group", "brand", "stock_uom", "is_fixed_asset", "item_tax_rate",
	"pricing_rules", "weight_per_unit", "weight_uom", "total_weight")

class AccountsController(TransactionBase):
	def __init__(self, *args, **kwargs):
		super(AccountsController, self).__init__(*args, **kwargs)

	def get_print_settings(self):
		print_setting_fields = []
		items_field = self.meta.get_field('items')

		if items_field and items_field.fieldtype == 'Table':
			print_setting_fields += ['compact_item_print', 'print_uom_after_quantity']

		taxes_field = self.meta.get_field('taxes')
		if taxes_field and taxes_field.fieldtype == 'Table':
			print_setting_fields += ['print_taxes_with_zero_amount']

		return print_setting_fields

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
						_('{0} is blocked so this transaction cannot proceed').format(supplier_name), raise_exception=1)

	def validate(self):
		if not self.get('is_return'):
			self.validate_qty_is_not_zero()

		if self.get("_action") and self._action != "update_after_submit":
			self.set_missing_values(for_validate=True)

		self.ensure_supplier_is_not_blocked()

		self.validate_date_with_fiscal_year()
		self.validate_party_accounts()

		self.validate_inter_company_reference()

		self.set_incoming_rate()

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
			# apply tax withholding only if checked and applicable
			self.set_tax_withholding()

		if self.doctype in ['Purchase Invoice', 'Sales Invoice']:
			pos_check_field = "is_pos" if self.doctype=="Sales Invoice" else "is_paid"
			if cint(self.allocate_advances_automatically) and not cint(self.get(pos_check_field)):
				self.set_advances()

			self.set_advance_gain_or_loss()

			if self.is_return:
				self.validate_qty()
			else:
				self.validate_deferred_start_and_end_date()

			self.set_inter_company_account()

		validate_regional(self)

		if self.doctype != 'Material Request':
			apply_pricing_rule_on_transaction(self)

	def on_trash(self):
		# delete sl and gl entries on deletion of transaction
		if frappe.db.get_single_value('Accounts Settings', 'delete_linked_ledger_entries'):
			frappe.db.sql("delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s", (self.doctype, self.name))
			frappe.db.sql("delete from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s", (self.doctype, self.name))

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
		if not self.get('ignore_default_payment_terms_template'):
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

	def before_print(self, settings=None):
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

		set_print_templates_for_item_table(self, settings)
		set_print_templates_for_taxes(self, settings)

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
			date_field = None
			if self.meta.get_field("posting_date"):
				date_field = "posting_date"
			elif self.meta.get_field("transaction_date"):
				date_field = "transaction_date"

			if date_field and self.get(date_field):
				validate_fiscal_year(self.get(date_field), self.fiscal_year, self.company,
									 self.meta.get_label(date_field), self)

	def validate_party_accounts(self):
		if self.doctype not in ('Sales Invoice', 'Purchase Invoice'):
			return

		if self.doctype == 'Sales Invoice':
			party_account_field = 'debit_to'
			item_field = 'income_account'
		else:
			party_account_field = 'credit_to'
			item_field = 'expense_account'

		for item in self.get('items'):
			if item.get(item_field) == self.get(party_account_field):
				frappe.throw(_("Row {0}: {1} {2} cannot be same as {3} (Party Account) {4}").format(item.idx,
					frappe.bold(frappe.unscrub(item_field)), item.get(item_field),
					frappe.bold(frappe.unscrub(party_account_field)), self.get(party_account_field)))

	def validate_inter_company_reference(self):
		if self.doctype not in ('Purchase Invoice', 'Purchase Receipt', 'Purchase Order'):
			return

		if self.is_internal_transfer():
			if not (self.get('inter_company_reference') or self.get('inter_company_invoice_reference')
				or self.get('inter_company_order_reference')):
				msg = _("Internal Sale or Delivery Reference missing.")
				msg += _("Please create purchase from internal sale or delivery document itself")
				frappe.throw(msg, title=_("Internal Sales Reference Missing"))

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

			self.pricing_rules = []
			for item in self.get("items"):
				if item.get("item_code"):
					args = parent_dict.copy()
					args.update(item.as_dict())

					args["doctype"] = self.doctype
					args["name"] = self.name
					args["child_docname"] = item.name
					args["ignore_pricing_rule"] = self.ignore_pricing_rule if hasattr(self, 'ignore_pricing_rule') else 0

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

					# Double check for cost center
					# Items add via promotional scheme may not have cost center set
					if hasattr(item, 'cost_center') and not item.get('cost_center'):
						item.set('cost_center', self.get('cost_center') or erpnext.get_default_cost_center(self.company))

					if ret.get("pricing_rules"):
						self.apply_pricing_rule_on_items(item, ret)
						self.set_pricing_rule_details(item, ret)

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

				if item.get("apply_discount_on_discounted_rate") and pricing_rule_args.get("rate"):
					item.rate = pricing_rule_args.get("rate")

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

	def set_pricing_rule_details(self, item_row, args):
		pricing_rules = get_applied_pricing_rules(args.get("pricing_rules"))
		if not pricing_rules: return

		for pricing_rule in pricing_rules:
			self.append("pricing_rules", {
				"pricing_rule": pricing_rule,
				"item_code": item_row.item_code,
				"child_docname": item_row.name,
				"rule_applied": True
			})

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
			"Period Closing Voucher", "Payment Entry", "Purchase Receipt", "Purchase Invoice", "Stock Entry"]:
			self.validate_account_currency(gl_dict.account, account_currency)

		if gl_dict.account and self.doctype not in ["Journal Entry", "Period Closing Voucher", "Payment Entry"]:
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
				.format(account, (' ' + _("or") + ' ').join(valid_currency)))

	def clear_unallocated_advances(self, childtype, parentfield):
		self.set(parentfield, self.get(parentfield, {"allocated_amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tab%s` where parentfield=%s and parent = %s
			and allocated_amount = 0""" % (childtype, '%s', '%s'), (parentfield, self.name))

	@frappe.whitelist()
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

	@frappe.whitelist()
	def set_advances(self):
		"""Returns list of advances against Account, Party, Reference"""

		res = self.get_advance_entries()

		self.set("advances", [])
		advance_allocated = 0
		for d in res:
			if d.against_order:
				allocated_amount = flt(d.amount)
			else:
				if self.get('party_account_currency') == self.company_currency:
					amount = self.get('base_rounded_total') or self.base_grand_total
				else:
					amount = self.get('rounded_total') or self.grand_total

				allocated_amount = min(amount - advance_allocated, d.amount)
			advance_allocated += flt(allocated_amount)

			advance_row = {
				"doctype": self.doctype + " Advance",
				"reference_type": d.reference_type,
				"reference_name": d.reference_name,
				"reference_row": d.reference_row,
				"remarks": d.remarks,
				"advance_amount": flt(d.amount),
				"allocated_amount": allocated_amount,
				"ref_exchange_rate": flt(d.exchange_rate) # exchange_rate of advance entry
			}

			self.append("advances", advance_row)

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

		order_list = list(set(d.get(order_field)
			for d in self.get("items") if d.get(order_field)))

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
		order_list = list(set(d.get(order_field)
			for d in self.get("items") if d.get(order_field)))

		if not order_list: return

		advance_entries = self.get_advance_entries(include_unallocated=False)

		if advance_entries:
			advance_entries_against_si = [d.reference_name for d in self.get("advances")]
			for d in advance_entries:
				if not advance_entries_against_si or d.reference_name not in advance_entries_against_si:
					frappe.msgprint(_(
						"Payment Entry {0} is linked against Order {1}, check if it should be pulled as advance in this invoice.")
							.format(d.reference_name, d.against_order))

	def set_advance_gain_or_loss(self):
		if self.get('conversion_rate') == 1 or not self.get("advances"):
			return

		is_purchase_invoice = self.doctype == 'Purchase Invoice'
		party_account = self.credit_to if is_purchase_invoice else self.debit_to
		if get_account_currency(party_account) != self.currency:
			return

		for d in self.get("advances"):
			advance_exchange_rate = d.ref_exchange_rate
			if (d.allocated_amount and self.conversion_rate != advance_exchange_rate):

				base_allocated_amount_in_ref_rate = advance_exchange_rate * d.allocated_amount
				base_allocated_amount_in_inv_rate = self.conversion_rate * d.allocated_amount
				difference = base_allocated_amount_in_ref_rate - base_allocated_amount_in_inv_rate

				d.exchange_gain_loss = difference

	def make_exchange_gain_loss_gl_entries(self, gl_entries):
		if self.get('doctype') in ['Purchase Invoice', 'Sales Invoice']:
			for d in self.get("advances"):
				if d.exchange_gain_loss:
					is_purchase_invoice = self.get('doctype') == 'Purchase Invoice'
					party = self.supplier if is_purchase_invoice else self.customer
					party_account = self.credit_to if is_purchase_invoice else self.debit_to
					party_type = "Supplier" if is_purchase_invoice else "Customer"

					gain_loss_account = frappe.db.get_value('Company', self.company, 'exchange_gain_loss_account')
					if not gain_loss_account:
						frappe.throw(_("Please set default Exchange Gain/Loss Account in Company {}")
							.format(self.get('company')))
					account_currency = get_account_currency(gain_loss_account)
					if account_currency != self.company_currency:
						frappe.throw(_("Currency for {0} must be {1}").format(gain_loss_account, self.company_currency))

					# for purchase
					dr_or_cr = 'debit' if d.exchange_gain_loss > 0 else 'credit'
					if not is_purchase_invoice:
						# just reverse for sales?
						dr_or_cr = 'debit' if dr_or_cr == 'credit' else 'credit'

					gl_entries.append(
						self.get_gl_dict({
							"account": gain_loss_account,
							"account_currency": account_currency,
							"against": party,
							dr_or_cr + "_in_account_currency": abs(d.exchange_gain_loss),
							dr_or_cr: abs(d.exchange_gain_loss),
							"cost_center": self.cost_center or erpnext.get_default_cost_center(self.company),
							"project": self.project
						}, item=d)
					)

					dr_or_cr = 'debit' if dr_or_cr == 'credit' else 'credit'

					gl_entries.append(
						self.get_gl_dict({
							"account": party_account,
							"party_type": party_type,
							"party": party,
							"against": gain_loss_account,
							dr_or_cr + "_in_account_currency": flt(abs(d.exchange_gain_loss) / self.conversion_rate),
							dr_or_cr: abs(d.exchange_gain_loss),
							"cost_center": self.cost_center,
							"project": self.project
						}, self.party_account_currency, item=self)
					)

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
					'precision': d.precision('advance_amount'),
					'exchange_rate': (self.conversion_rate
						if self.party_account_currency != self.company_currency else 1),
					'grand_total': (self.base_grand_total
						if self.party_account_currency == self.company_currency else self.grand_total),
					'outstanding_amount': self.outstanding_amount,
					'difference_account': frappe.db.get_value('Company', self.company, 'exchange_gain_loss_account'),
					'exchange_gain_loss': flt(d.get('exchange_gain_loss'))
				})
				lst.append(args)

		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			reconcile_against_document(lst)

	def on_cancel(self):
		from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries

		if self.doctype in ["Sales Invoice", "Purchase Invoice"]:
			self.update_allocated_advance_taxes_on_cancel()
			if frappe.db.get_single_value('Accounts Settings', 'unlink_payment_on_cancellation_of_invoice'):
				unlink_ref_doc_from_payment_entries(self)

		elif self.doctype in ["Sales Order", "Purchase Order"]:
			if frappe.db.get_single_value('Accounts Settings', 'unlink_advance_payment_on_cancelation_of_order'):
				unlink_ref_doc_from_payment_entries(self)

	def get_tax_map(self):
		tax_map = {}
		for tax in self.get('taxes'):
			tax_map.setdefault(tax.account_head, 0.0)
			tax_map[tax.account_head] += tax.tax_amount

		return tax_map

	def update_allocated_advance_taxes_on_cancel(self):
		if self.get('advances'):
			tax_accounts = [d.account_head for d in self.get('taxes')]
			allocated_tax_map = frappe._dict(frappe.get_all('GL Entry', fields=['account', 'sum(credit - debit)'],
				filters={'voucher_no': self.name, 'account': ('in', tax_accounts)},
				group_by='account', as_list=1))

			tax_map = self.get_tax_map()

			for pe in self.get('advances'):
				if pe.reference_type == 'Payment Entry':
					pe = frappe.get_doc('Payment Entry', pe.reference_name)
					for tax in pe.get('taxes'):
						allocated_amount = tax_map.get(tax.account_head) - allocated_tax_map.get(tax.account_head)
						if allocated_amount > tax.tax_amount:
							allocated_amount = tax.tax_amount

						if allocated_amount:
							frappe.db.set_value('Advance Taxes and Charges', tax.name, 'allocated_amount',
								tax.allocated_amount - allocated_amount)
							tax_map[tax.account_head] -= allocated_amount
							allocated_tax_map[tax.account_head] -= allocated_amount

	def get_amount_and_base_amount(self, item, enable_discount_accounting):
		amount = item.net_amount
		base_amount = item.base_net_amount

		if enable_discount_accounting and self.get('discount_amount') and self.get('additional_discount_account'):
			amount = item.amount
			base_amount = item.base_amount

		return amount, base_amount

	def get_tax_amounts(self, tax, enable_discount_accounting):
		amount = tax.tax_amount_after_discount_amount
		base_amount = tax.base_tax_amount_after_discount_amount

		if enable_discount_accounting and self.get('discount_amount') and self.get('additional_discount_account') \
			and self.get('apply_discount_on') == 'Grand Total':
			amount = tax.tax_amount
			base_amount = tax.base_tax_amount

		return amount, base_amount

	def make_discount_gl_entries(self, gl_entries):
		enable_discount_accounting = cint(frappe.db.get_single_value('Accounts Settings', 'enable_discount_accounting'))

		if enable_discount_accounting:
			if self.doctype == "Purchase Invoice":
				dr_or_cr = "credit"
				rev_dr_cr = "debit"
				supplier_or_customer = self.supplier

			else:
				dr_or_cr = "debit"
				rev_dr_cr = "credit"
				supplier_or_customer = self.customer

			for item in self.get("items"):
				if item.get('discount_amount') and item.get('discount_account'):
					discount_amount = item.discount_amount * item.qty
					if self.doctype == "Purchase Invoice":
						income_or_expense_account = (item.expense_account
							if (not item.enable_deferred_expense or self.is_return)
							else item.deferred_expense_account)
					else:
						income_or_expense_account = (item.income_account
							if (not item.enable_deferred_revenue or self.is_return)
							else item.deferred_revenue_account)

					account_currency = get_account_currency(item.discount_account)
					gl_entries.append(
						self.get_gl_dict({
							"account": item.discount_account,
							"against": supplier_or_customer,
							dr_or_cr: flt(discount_amount, item.precision('discount_amount')),
							dr_or_cr + "_in_account_currency": flt(discount_amount * self.get('conversion_rate'),
								item.precision('discount_amount')),
							"cost_center": item.cost_center,
							"project": item.project
						}, account_currency, item=item)
					)

					account_currency = get_account_currency(income_or_expense_account)
					gl_entries.append(
						self.get_gl_dict({
							"account": income_or_expense_account,
							"against": supplier_or_customer,
							rev_dr_cr: flt(discount_amount, item.precision('discount_amount')),
							rev_dr_cr + "_in_account_currency": flt(discount_amount * self.get('conversion_rate'),
								item.precision('discount_amount')),
							"cost_center": item.cost_center,
							"project": item.project or self.project
						}, account_currency, item=item)
					)

			if self.get('discount_amount') and self.get('additional_discount_account'):
				gl_entries.append(
					self.get_gl_dict({
						"account": self.additional_discount_account,
						"against": supplier_or_customer,
						dr_or_cr: self.discount_amount,
						"cost_center": self.cost_center
					}, item=self)
				)

	def allocate_advance_taxes(self, gl_entries):
		tax_map = self.get_tax_map()
		for pe in self.get("advances"):
			if pe.reference_type == "Payment Entry" and \
				frappe.db.get_value('Payment Entry', pe.reference_name, 'advance_tax_account'):
				pe = frappe.get_doc("Payment Entry", pe.reference_name)
				for tax in pe.get("taxes"):
					account_currency = get_account_currency(tax.account_head)

					if self.doctype == "Purchase Invoice":
						dr_or_cr = "debit" if tax.add_deduct_tax == "Add" else "credit"
						rev_dr_cr = "credit" if tax.add_deduct_tax == "Add" else "debit"
					else:
						dr_or_cr = "credit" if tax.add_deduct_tax == "Add" else "debit"
						rev_dr_cr = "debit" if tax.add_deduct_tax == "Add" else "credit"

					party = self.supplier if self.doctype == "Purchase Invoice" else self.customer
					unallocated_amount = tax.tax_amount - tax.allocated_amount
					if tax_map.get(tax.account_head):
						amount = tax_map.get(tax.account_head)
						if amount < unallocated_amount:
							unallocated_amount = amount

						gl_entries.append(
							self.get_gl_dict({
								"account": tax.account_head,
								"against": party,
								dr_or_cr: unallocated_amount,
								dr_or_cr + "_in_account_currency": unallocated_amount
								if account_currency==self.company_currency
								else unallocated_amount,
								"cost_center": tax.cost_center
							}, account_currency, item=tax))

						gl_entries.append(
							self.get_gl_dict({
								"account": pe.advance_tax_account,
								"against": party,
								rev_dr_cr: unallocated_amount,
								rev_dr_cr + "_in_account_currency": unallocated_amount
								if account_currency==self.company_currency
								else unallocated_amount,
								"cost_center": tax.cost_center
							}, account_currency, item=tax))

						frappe.db.set_value("Advance Taxes and Charges", tax.name, "allocated_amount",
							tax.allocated_amount + unallocated_amount)

						tax_map[tax.account_head] -= unallocated_amount

	def validate_multiple_billing(self, ref_dt, item_ref_dn, based_on, parentfield):
		from erpnext.controllers.status_updater import get_allowance_for
		item_allowance = {}
		global_qty_allowance, global_amount_allowance = None, None

		role_allowed_to_over_bill = frappe.db.get_single_value('Accounts Settings', 'role_allowed_to_over_bill')
		user_roles = frappe.get_roles()

		total_overbilled_amt = 0.0

		for item in self.get("items"):
			if not item.get(item_ref_dn):
				continue

			ref_amt = flt(frappe.db.get_value(ref_dt + " Item",
				item.get(item_ref_dn), based_on), self.precision(based_on, item))
			if not ref_amt:
				frappe.msgprint(
					_("System will not check overbilling since amount for Item {0} in {1} is zero")
						.format(item.item_code, ref_dt), title=_("Warning"), indicator="orange")
				continue

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

			overbill_amt = total_billed_amt - max_allowed_amt
			total_overbilled_amt += overbill_amt

			if overbill_amt > 0.01 and role_allowed_to_over_bill not in user_roles:
				if self.doctype != "Purchase Invoice":
					self.throw_overbill_exception(item, max_allowed_amt)
				elif not cint(frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice")):
					self.throw_overbill_exception(item, max_allowed_amt)

		if role_allowed_to_over_bill in user_roles and total_overbilled_amt > 0.1:
			frappe.msgprint(_("Overbilling of {} ignored because you have {} role.")
					.format(total_overbilled_amt, role_allowed_to_over_bill), title=_("Warning"), indicator="orange")

	def throw_overbill_exception(self, item, max_allowed_amt):
		frappe.throw(_("Cannot overbill for Item {0} in row {1} more than {2}. To allow over-billing, please set allowance in Accounts Settings")
			.format(item.item_code, item.idx, max_allowed_amt))

	def get_company_default(self, fieldname, ignore_validation=False):
		from erpnext.accounts.utils import get_company_default
		return get_company_default(self.company, fieldname, ignore_validation=ignore_validation)

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
			rev_dr_or_cr = "debit_in_account_currency"
			party = self.customer
		else:
			dr_or_cr = "debit_in_account_currency"
			rev_dr_or_cr = "credit_in_account_currency"
			party = self.supplier

		advance = frappe.db.sql("""
			select
				account_currency, sum({dr_or_cr}) - sum({rev_dr_cr}) as amount
			from
				`tabGL Entry`
			where
				against_voucher_type = %s and against_voucher = %s and party=%s
				and docstatus = 1
		""".format(dr_or_cr=dr_or_cr, rev_dr_cr=rev_dr_or_cr), (self.doctype, self.name, party), as_dict=1) #nosec

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

	def raise_missing_debit_credit_account_error(self, party_type, party):
		"""Raise an error if debit to/credit to account does not exist."""
		db_or_cr = frappe.bold("Debit To") if self.doctype == "Sales Invoice" else frappe.bold("Credit To")
		rec_or_pay = "Receivable" if self.doctype == "Sales Invoice" else "Payable"

		link_to_party = frappe.utils.get_link_to_form(party_type, party)
		link_to_company = frappe.utils.get_link_to_form("Company", self.company)

		message = _("{0} Account not found against Customer {1}.").format(db_or_cr, frappe.bold(party) or '')
		message += "<br>" + _("Please set one of the following:") + "<br>"
		message += "<br><ul><li>" + _("'Account' in the Accounting section of Customer {0}").format(link_to_party) + "</li>"
		message += "<li>" + _("'Default {0} Account' in Company {1}").format(rec_or_pay, link_to_company) + "</li></ul>"

		frappe.throw(message, title=_("Account Missing"), exc=AccountMissingError)

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

		party_account_currency = self.get('party_account_currency')
		if not party_account_currency:
			party_type, party = self.get_party()

			if party_type and party:
				party_account_currency = get_party_account_currency(party_type, party, self.company)

		posting_date = self.get("bill_date") or self.get("posting_date") or self.get("transaction_date")
		date = self.get("due_date")
		due_date = date or posting_date

		base_grand_total = self.get("base_rounded_total") or self.base_grand_total
		grand_total = self.get("rounded_total") or self.grand_total

		if self.doctype in ("Sales Invoice", "Purchase Invoice"):
			base_grand_total = base_grand_total - flt(self.base_write_off_amount)
			grand_total = grand_total - flt(self.write_off_amount)
			po_or_so, doctype, fieldname = self.get_order_details()
			automatically_fetch_payment_terms = cint(frappe.db.get_single_value('Accounts Settings', 'automatically_fetch_payment_terms'))

		if self.get("total_advance"):
			if party_account_currency == self.company_currency:
				base_grand_total -= self.get("total_advance")
				grand_total = flt(base_grand_total / self.get("conversion_rate"), self.precision("grand_total"))
			else:
				grand_total -= self.get("total_advance")
				base_grand_total = flt(grand_total * self.get("conversion_rate"), self.precision("base_grand_total"))

		if not self.get("payment_schedule"):
			if self.doctype in ["Sales Invoice", "Purchase Invoice"] and automatically_fetch_payment_terms \
				and self.linked_order_has_payment_terms(po_or_so, fieldname, doctype):
				self.fetch_payment_terms_from_order(po_or_so, doctype)
				if self.get('payment_terms_template'):
					self.ignore_default_payment_terms_template = 1
			elif self.get("payment_terms_template"):
				data = get_payment_terms(self.payment_terms_template, posting_date, grand_total, base_grand_total)
				for item in data:
					self.append("payment_schedule", item)
			elif self.doctype not in ["Purchase Receipt"]:
				data = dict(due_date=due_date, invoice_portion=100, payment_amount=grand_total, base_payment_amount=base_grand_total)
				self.append("payment_schedule", data)

		for d in self.get("payment_schedule"):
			if d.invoice_portion:
				d.payment_amount = flt(grand_total * flt(d.invoice_portion / 100), d.precision('payment_amount'))
				d.base_payment_amount = flt(base_grand_total * flt(d.invoice_portion / 100), d.precision('base_payment_amount'))
				d.outstanding = d.payment_amount
			elif not d.invoice_portion:
				d.base_payment_amount = flt(d.payment_amount * self.get("conversion_rate"), d.precision('base_payment_amount'))


	def get_order_details(self):
		if self.doctype == "Sales Invoice":
			po_or_so = self.get('items')[0].get('sales_order')
			po_or_so_doctype = "Sales Order"
			po_or_so_doctype_name = "sales_order"

		else:
			po_or_so = self.get('items')[0].get('purchase_order')
			po_or_so_doctype = "Purchase Order"
			po_or_so_doctype_name = "purchase_order"

		return po_or_so, po_or_so_doctype, po_or_so_doctype_name

	def linked_order_has_payment_terms(self, po_or_so, fieldname, doctype):
		if po_or_so and self.all_items_have_same_po_or_so(po_or_so, fieldname):
			if self.linked_order_has_payment_terms_template(po_or_so, doctype):
				return True
			elif self.linked_order_has_payment_schedule(po_or_so):
				return True

		return False

	def all_items_have_same_po_or_so(self, po_or_so, fieldname):
		for item in self.get('items'):
			if item.get(fieldname) != po_or_so:
				return False

		return True

	def linked_order_has_payment_terms_template(self, po_or_so, doctype):
		return frappe.get_value(doctype, po_or_so, 'payment_terms_template')

	def linked_order_has_payment_schedule(self, po_or_so):
		return frappe.get_all('Payment Schedule', filters={'parent': po_or_so})

	def fetch_payment_terms_from_order(self, po_or_so, po_or_so_doctype):
		"""
			Fetch Payment Terms from Purchase/Sales Order on creating a new Purchase/Sales Invoice.
		"""
		po_or_so = frappe.get_cached_doc(po_or_so_doctype, po_or_so)

		self.payment_schedule = []
		self.payment_terms_template = po_or_so.payment_terms_template

		for schedule in po_or_so.payment_schedule:
			payment_schedule = {
				'payment_term': schedule.payment_term,
				'due_date': schedule.due_date,
				'invoice_portion': schedule.invoice_portion,
				'mode_of_payment': schedule.mode_of_payment,
				'description': schedule.description
			}

			if schedule.discount_type == 'Percentage':
				payment_schedule['discount_type'] = schedule.discount_type
				payment_schedule['discount'] = schedule.discount

			self.append("payment_schedule", payment_schedule)

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

		party_account_currency = self.get('party_account_currency')
		if not party_account_currency:
			party_type, party = self.get_party()

			if party_type and party:
				party_account_currency = get_party_account_currency(party_type, party, self.company)

		if self.get("payment_schedule"):
			total = 0
			base_total = 0
			for d in self.get("payment_schedule"):
				total += flt(d.payment_amount)
				base_total += flt(d.base_payment_amount)

			base_grand_total = self.get("base_rounded_total") or self.base_grand_total
			grand_total = self.get("rounded_total") or self.grand_total

			if self.doctype in ("Sales Invoice", "Purchase Invoice"):
				base_grand_total = base_grand_total - flt(self.base_write_off_amount)
				grand_total = grand_total - flt(self.write_off_amount)

			if self.get("total_advance"):
				if party_account_currency == self.company_currency:
					base_grand_total -= self.get("total_advance")
					grand_total = flt(base_grand_total / self.get("conversion_rate"), self.precision("grand_total"))
				else:
					grand_total -= self.get("total_advance")
					base_grand_total = flt(grand_total * self.get("conversion_rate"), self.precision("base_grand_total"))
			if total != flt(grand_total, self.precision("grand_total")) or \
				base_total != flt(base_grand_total, self.precision("base_grand_total")):
				frappe.throw(_("Total Payment Amount in Payment Schedule must be equal to Grand / Rounded Total"))

	def is_rounded_total_disabled(self):
		if self.meta.get_field("disable_rounded_total"):
			return self.disable_rounded_total
		else:
			return frappe.db.get_single_value("Global Defaults", "disable_rounded_total")

	def set_inter_company_account(self):
		"""
			Set intercompany account for inter warehouse transactions
			This account will be used in case billing company and internal customer's
			representation company is same
		"""

		if self.is_internal_transfer() and not self.unrealized_profit_loss_account:
			unrealized_profit_loss_account = frappe.db.get_value('Company', self.company, 'unrealized_profit_loss_account')

			if not unrealized_profit_loss_account:
				msg = _("Please select Unrealized Profit / Loss account or add default Unrealized Profit / Loss account account for company {0}").format(
						frappe.bold(self.company))
				frappe.throw(msg)

			self.unrealized_profit_loss_account = unrealized_profit_loss_account

	def is_internal_transfer(self):
		"""
			It will an internal transfer if its an internal customer and representation
			company is same as billing company
		"""
		if self.doctype in ('Sales Invoice', 'Delivery Note', 'Sales Order'):
			internal_party_field = 'is_internal_customer'
		elif self.doctype in ('Purchase Invoice', 'Purchase Receipt', 'Purchase Order'):
			internal_party_field = 'is_internal_supplier'

		if self.get(internal_party_field) and (self.represents_company == self.company):
			return True

		return False

	def process_common_party_accounting(self):
		is_invoice = self.doctype in ['Sales Invoice', 'Purchase Invoice']
		if not is_invoice:
			return

		if frappe.db.get_single_value('Accounts Settings', 'enable_common_party_accounting'):
			party_link = self.get_common_party_link()
			if party_link and self.outstanding_amount:
				self.create_advance_and_reconcile(party_link)

	def get_common_party_link(self):
		party_type, party = self.get_party()
		return frappe.db.get_value(
			doctype='Party Link',
			filters={'secondary_role': party_type, 'secondary_party': party},
			fieldname=['primary_role', 'primary_party'],
			as_dict=True
		)

	def create_advance_and_reconcile(self, party_link):
		secondary_party_type, secondary_party = self.get_party()
		primary_party_type, primary_party = party_link.primary_role, party_link.primary_party

		primary_account = get_party_account(primary_party_type, primary_party, self.company)
		secondary_account = get_party_account(secondary_party_type, secondary_party, self.company)

		jv = frappe.new_doc('Journal Entry')
		jv.voucher_type = 'Journal Entry'
		jv.posting_date = self.posting_date
		jv.company = self.company
		jv.remark = 'Adjustment for {} {}'.format(self.doctype, self.name)

		reconcilation_entry = frappe._dict()
		advance_entry = frappe._dict()

		reconcilation_entry.account = secondary_account
		reconcilation_entry.party_type = secondary_party_type
		reconcilation_entry.party = secondary_party
		reconcilation_entry.reference_type = self.doctype
		reconcilation_entry.reference_name = self.name
		reconcilation_entry.cost_center = self.cost_center

		advance_entry.account = primary_account
		advance_entry.party_type = primary_party_type
		advance_entry.party = primary_party
		advance_entry.cost_center = self.cost_center
		advance_entry.is_advance = 'Yes'

		if self.doctype == 'Sales Invoice':
			reconcilation_entry.credit_in_account_currency = self.outstanding_amount
			advance_entry.debit_in_account_currency = self.outstanding_amount
		else:
			advance_entry.credit_in_account_currency = self.outstanding_amount
			reconcilation_entry.debit_in_account_currency = self.outstanding_amount

		jv.append('accounts', reconcilation_entry)
		jv.append('accounts', advance_entry)

		jv.save()
		jv.submit()

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
		throw(
			_("{0} is mandatory. Maybe Currency Exchange record is not created for {1} to {2}.")
			.format(conversion_rate_label, currency, company_currency)
		)


def validate_taxes_and_charges(tax):
	if tax.charge_type in ['Actual', 'On Net Total', 'On Paid Amount'] and tax.row_id:
		frappe.throw(_("Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'"))
	elif tax.charge_type in ['On Previous Row Amount', 'On Previous Row Total']:
		if cint(tax.idx) == 1:
			frappe.throw(
				_("Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"))
		elif not tax.row_id:
			frappe.throw(_("Please specify a valid Row ID for row {0} in table {1}").format(tax.idx, _(tax.doctype)))
		elif tax.row_id and cint(tax.row_id) >= cint(tax.idx):
			frappe.throw(_("Cannot refer row number greater than or equal to current row number for this Charge type"))

	if tax.charge_type == "Actual":
		tax.rate = None


def validate_account_head(tax, doc):
	company = frappe.get_cached_value('Account',
		tax.account_head, 'company')

	if company != doc.company:
		frappe.throw(_('Row {0}: Account {1} does not belong to Company {2}')
			.format(tax.idx, frappe.bold(tax.account_head), frappe.bold(doc.company)), title=_('Invalid Account'))


def validate_cost_center(tax, doc):
	if not tax.cost_center:
		return

	company = frappe.get_cached_value('Cost Center',
		tax.cost_center, 'company')

	if company != doc.company:
		frappe.throw(_('Row {0}: Cost Center {1} does not belong to Company {2}')
			.format(tax.idx, frappe.bold(tax.cost_center), frappe.bold(doc.company)), title=_('Invalid Cost Center'))


def validate_inclusive_tax(tax, doc):
	def _on_previous_row_error(row_range):
		throw(_("To include tax in row {0} in Item rate, taxes in rows {1} must also be included").format(tax.idx, row_range))

	if cint(getattr(tax, "included_in_print_rate", None)):
		if tax.charge_type == "Actual":
			# inclusive tax cannot be of type Actual
			throw(_("Charge of type 'Actual' in row {0} cannot be included in Item Rate or Paid Amount").format(tax.idx))
		elif tax.charge_type == "On Previous Row Amount" and \
				not cint(doc.get("taxes")[cint(tax.row_id) - 1].included_in_print_rate):
			# referred row should also be inclusive
			_on_previous_row_error(tax.row_id)
		elif tax.charge_type == "On Previous Row Total" and \
				not all([cint(t.included_in_print_rate) for t in doc.get("taxes")[:cint(tax.row_id) - 1]]):
			# all rows about the referred tax should be inclusive
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
		order_list=None, include_unallocated=True, against_all_orders=False, limit=None, condition=None):
	party_account_field = "paid_from" if party_type == "Customer" else "paid_to"
	currency_field = "paid_from_account_currency" if party_type == "Customer" else "paid_to_account_currency"
	payment_type = "Receive" if party_type == "Customer" else "Pay"
	exchange_rate_field = "source_exchange_rate" if payment_type == "Receive" else "target_exchange_rate"

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
				t1.{0} as currency, t1.{4} as exchange_rate
			from `tabPayment Entry` t1, `tabPayment Entry Reference` t2
			where
				t1.name = t2.parent and t1.{1} = %s and t1.payment_type = %s
				and t1.party_type = %s and t1.party = %s and t1.docstatus = 1
				and t2.reference_doctype = %s {2}
			order by t1.posting_date {3}
		""".format(currency_field, party_account_field, reference_condition, limit_cond, exchange_rate_field),
													  [party_account, payment_type, party_type, party,
													   order_doctype] + order_list, as_dict=1)

	if include_unallocated:
		unallocated_payment_entries = frappe.db.sql("""
				select "Payment Entry" as reference_type, name as reference_name, posting_date,
				remarks, unallocated_amount as amount, {2} as exchange_rate, {3} as currency
				from `tabPayment Entry`
				where
					{0} = %s and party_type = %s and party = %s and payment_type = %s
					and docstatus = 1 and unallocated_amount > 0 {condition}
				order by posting_date {1}
			""".format(party_account_field, limit_cond, exchange_rate_field, currency_field, condition=condition or ""),
			(party_account, party_type, party, payment_type), as_dict=1)

	return list(payment_entries_against_order) + list(unallocated_payment_entries)

def update_invoice_status():
	"""Updates status as Overdue for applicable invoices. Runs daily."""

	for doctype in ("Sales Invoice", "Purchase Invoice"):
		frappe.db.sql("""
			update `tab{}` as dt set dt.status = 'Overdue'
			where dt.docstatus = 1
				and dt.status != 'Overdue'
				and dt.outstanding_amount > 0
				and (dt.grand_total - dt.outstanding_amount) <
					(select sum(payment_amount) from `tabPayment Schedule` as ps
						where ps.parent = dt.name and ps.due_date < %s)
		""".format(doctype), getdate())

@frappe.whitelist()
def get_payment_terms(terms_template, posting_date=None, grand_total=None, base_grand_total=None, bill_date=None):
	if not terms_template:
		return

	terms_doc = frappe.get_doc("Payment Terms Template", terms_template)

	schedule = []
	for d in terms_doc.get("terms"):
		term_details = get_payment_term_details(d, posting_date, grand_total, base_grand_total, bill_date)
		schedule.append(term_details)

	return schedule


@frappe.whitelist()
def get_payment_term_details(term, posting_date=None, grand_total=None, base_grand_total=None, bill_date=None):
	term_details = frappe._dict()
	if isinstance(term, text_type):
		term = frappe.get_doc("Payment Term", term)
	else:
		term_details.payment_term = term.payment_term
	term_details.description = term.description
	term_details.invoice_portion = term.invoice_portion
	term_details.payment_amount = flt(term.invoice_portion) * flt(grand_total) / 100
	term_details.base_payment_amount = flt(term.invoice_portion) * flt(base_grand_total) / 100
	term_details.discount_type = term.discount_type
	term_details.discount = term.discount
	term_details.outstanding = term_details.payment_amount
	term_details.mode_of_payment = term.mode_of_payment

	if bill_date:
		term_details.due_date = get_due_date(term, bill_date)
		term_details.discount_date = get_discount_date(term, bill_date)
	elif posting_date:
		term_details.due_date = get_due_date(term, posting_date)
		term_details.discount_date = get_discount_date(term, posting_date)

	if getdate(term_details.due_date) < getdate(posting_date):
		term_details.due_date = posting_date

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

def get_discount_date(term, posting_date=None, bill_date=None):
	discount_validity = None
	date = bill_date or posting_date
	if term.discount_validity_based_on == "Day(s) after invoice date":
		discount_validity = add_days(date, term.discount_validity)
	elif term.discount_validity_based_on == "Day(s) after the end of the invoice month":
		discount_validity = add_days(get_last_day(date), term.discount_validity)
	elif term.discount_validity_based_on == "Month(s) after the end of the invoice month":
		discount_validity = add_months(get_last_day(date), term.discount_validity)
	return discount_validity

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

def add_taxes_from_tax_template(child_item, parent_doc, db_insert=True):
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
				if db_insert:
					tax_row.db_insert()

def set_order_defaults(parent_doctype, parent_doctype_name, child_doctype, child_docname, trans_item):
	"""
	Returns a Sales/Purchase Order Item child item containing the default values
	"""
	p_doc = frappe.get_doc(parent_doctype, parent_doctype_name)
	child_item = frappe.new_doc(child_doctype, p_doc, child_docname)
	item = frappe.get_doc("Item", trans_item.get('item_code'))

	for field in ("item_code", "item_name", "description", "item_group"):
		child_item.update({field: item.get(field)})

	date_fieldname = "delivery_date" if child_doctype == "Sales Order Item" else "schedule_date"
	child_item.update({date_fieldname: trans_item.get(date_fieldname) or p_doc.get(date_fieldname)})
	child_item.stock_uom = item.stock_uom
	child_item.uom = trans_item.get("uom") or item.stock_uom
	child_item.warehouse = get_item_warehouse(item, p_doc, overwrite_warehouse=True)
	conversion_factor = flt(get_conversion_factor(item.item_code, child_item.uom).get("conversion_factor"))
	child_item.conversion_factor = flt(trans_item.get('conversion_factor')) or conversion_factor

	if child_doctype == "Purchase Order Item":
		# Initialized value will update in parent validation
		child_item.base_rate = 1
		child_item.base_amount = 1
	if child_doctype == "Sales Order Item":
		child_item.warehouse = get_item_warehouse(item, p_doc, overwrite_warehouse=True)
		if not child_item.warehouse:
			frappe.throw(_("Cannot find {} for item {}. Please set the same in Item Master or Stock Settings.")
				.format(frappe.bold("default warehouse"), frappe.bold(item.item_code)))

	set_child_tax_template_and_map(item, child_item, p_doc)
	add_taxes_from_tax_template(child_item, p_doc)
	return child_item

def validate_child_on_delete(row, parent):
	"""Check if partially transacted item (row) is being deleted."""
	if parent.doctype == "Sales Order":
		if flt(row.delivered_qty):
			frappe.throw(_("Row #{0}: Cannot delete item {1} which has already been delivered").format(row.idx, row.item_code))
		if flt(row.work_order_qty):
			frappe.throw(_("Row #{0}: Cannot delete item {1} which has work order assigned to it.").format(row.idx, row.item_code))
		if flt(row.ordered_qty):
			frappe.throw(_("Row #{0}: Cannot delete item {1} which is assigned to customer's purchase order.").format(row.idx, row.item_code))

	if parent.doctype == "Purchase Order" and flt(row.received_qty):
		frappe.throw(_("Row #{0}: Cannot delete item {1} which has already been received").format(row.idx, row.item_code))

	if flt(row.billed_amt):
		frappe.throw(_("Row #{0}: Cannot delete item {1} which has already been billed.").format(row.idx, row.item_code))

def update_bin_on_delete(row, doctype):
	"""Update bin for deleted item (row)."""
	from erpnext.stock.stock_balance import (
		get_indented_qty,
		get_ordered_qty,
		get_reserved_qty,
		update_bin_qty,
	)
	qty_dict = {}

	if doctype == "Sales Order":
		qty_dict["reserved_qty"] = get_reserved_qty(row.item_code, row.warehouse)
	else:
		if row.material_request_item:
			qty_dict["indented_qty"] = get_indented_qty(row.item_code, row.warehouse)

		qty_dict["ordered_qty"] = get_ordered_qty(row.item_code, row.warehouse)

	update_bin_qty(row.item_code, row.warehouse, qty_dict)

def validate_and_delete_children(parent, data):
	deleted_children = []
	updated_item_names = [d.get("docname") for d in data]
	for item in parent.items:
		if item.name not in updated_item_names:
			deleted_children.append(item)

	for d in deleted_children:
		validate_child_on_delete(d, parent)
		d.cancel()
		d.delete()

	# need to update ordered qty in Material Request first
	# bin uses Material Request Items to recalculate & update
	parent.update_prevdoc_status()

	for d in deleted_children:
		update_bin_on_delete(d, parent.doctype)


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
		child_doctype = "Sales Order Item" if parent_doctype == "Sales Order" else "Purchase Order Item"
		return set_order_defaults(parent_doctype, parent_doctype_name, child_doctype, child_docname, item_row)

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

		if not d.get("item_code"):
			# ignore empty rows
			continue

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
			prev_uom, new_uom = child_item.get("uom"), d.get("uom")

			if parent_doctype == 'Sales Order':
				prev_date, new_date = child_item.get("delivery_date"), d.get("delivery_date")
			elif parent_doctype == 'Purchase Order':
				prev_date, new_date = child_item.get("schedule_date"), d.get("schedule_date")

			rate_unchanged = prev_rate == new_rate
			qty_unchanged = prev_qty == new_qty
			uom_unchanged = prev_uom == new_uom
			conversion_factor_unchanged = prev_con_fac == new_con_fac
			date_unchanged = prev_date == getdate(new_date) if prev_date and new_date else False # in case of delivery note etc
			if rate_unchanged and qty_unchanged and conversion_factor_unchanged and uom_unchanged and date_unchanged:
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

		if d.get("uom"):
			child_item.uom = d.get("uom")
			conversion_factor = flt(get_conversion_factor(child_item.item_code, child_item.uom).get("conversion_factor"))
			child_item.conversion_factor = flt(d.get('conversion_factor'), conv_fac_precision) or conversion_factor

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
	parent.set_total_in_words()
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
			parent.create_raw_materials_supplied("supplied_items")
			parent.save()
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
