# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Tax helpers: TaxService class for doc-mutating operations, free functions for stateless utilities."""

import json

import frappe
from frappe import _, throw
from frappe.utils import cint, flt, parse_json

import erpnext
from erpnext.stock.get_item_details import (
	NOT_APPLICABLE_TAX,
	ItemDetailsCtx,
	_get_item_tax_template,
	_get_item_tax_template_from_item_group,
	get_item_tax_map,
)


class TaxService:
	def __init__(self, doc):
		self.doc = doc

	def set_taxes(self) -> None:
		doc = self.doc
		if not doc.meta.get_field("taxes"):
			return

		tax_master_doctype = doc.meta.get_field("taxes_and_charges").options

		if (doc.is_new() or self.is_pos_profile_changed()) and not doc.get("taxes"):
			if doc.company and not doc.get("taxes_and_charges"):
				doc.taxes_and_charges = frappe.db.get_value(
					tax_master_doctype, {"is_default": 1, "company": doc.company}
				)
			self.append_taxes_from_master(tax_master_doctype)

	def is_pos_profile_changed(self) -> bool:
		doc = self.doc
		if (
			doc.doctype == "Sales Invoice"
			and doc.is_pos
			and doc.pos_profile != frappe.db.get_value("Sales Invoice", doc.name, "pos_profile")
		):
			return True

	def set_taxes_and_charges(self) -> None:
		doc = self.doc
		if doc.doctype == "Material Request":
			return

		if doc.get("taxes") or doc.get("is_pos"):
			return

		if frappe.get_single_value(
			"Accounts Settings", "add_taxes_from_taxes_and_charges_template"
		) and hasattr(doc, "taxes_and_charges"):
			if tax_master_doctype := doc.meta.get_field("taxes_and_charges").options:
				self.append_taxes_from_master(tax_master_doctype)

		if frappe.get_single_value("Accounts Settings", "add_taxes_from_item_tax_template"):
			self.append_taxes_from_item_tax_template()

	def append_taxes_from_master(self, tax_master_doctype=None) -> None:
		doc = self.doc
		if doc.get("taxes_and_charges"):
			if not tax_master_doctype:
				tax_master_doctype = doc.meta.get_field("taxes_and_charges").options
			doc.extend("taxes", get_taxes_and_charges(tax_master_doctype, doc.get("taxes_and_charges")))

	def append_taxes_from_item_tax_template(self) -> None:
		doc = self.doc
		if not frappe.get_single_value("Accounts Settings", "add_taxes_from_item_tax_template"):
			return

		for row in doc.items:
			item_tax_rate = row.get("item_tax_rate")
			if not item_tax_rate:
				continue

			if isinstance(item_tax_rate, str):
				item_tax_rate = parse_json(item_tax_rate)

			for account_head, _rate in item_tax_rate.items():
				if not self.get_tax_row(account_head):
					doc.append(
						"taxes",
						{
							"charge_type": "On Net Total",
							"account_head": account_head,
							"rate": 0,
							"description": account_head,
							"set_by_item_tax_template": 1,
							"category": "Total",
							"add_deduct_tax": "Add",
						},
					)

	def get_tax_row(self, account_head):
		for row in self.doc.taxes:
			if row.account_head == account_head:
				return row

	def set_other_charges(self) -> None:
		self.doc.set("taxes", [])
		self.set_taxes()

	def validate_enabled_taxes_and_charges(self) -> None:
		doc = self.doc
		taxes_and_charges_doctype = doc.meta.get_options("taxes_and_charges")
		if doc.taxes_and_charges and frappe.get_cached_value(
			taxes_and_charges_doctype, doc.taxes_and_charges, "disabled"
		):
			frappe.throw(_("{0} '{1}' is disabled").format(taxes_and_charges_doctype, doc.taxes_and_charges))

	def validate_tax_account_company(self) -> None:
		doc = self.doc
		for d in doc.get("taxes"):
			if d.account_head:
				tax_account_company = frappe.get_cached_value("Account", d.account_head, "company")
				if tax_account_company != doc.company:
					frappe.throw(
						_("Row #{0}: Account {1} does not belong to company {2}").format(
							d.idx, d.account_head, doc.company
						)
					)

	def get_tax_map(self) -> dict:
		tax_map = {}
		for tax in self.doc.get("taxes"):
			tax_map.setdefault(tax.account_head, 0.0)
			tax_map[tax.account_head] += tax.tax_amount
		return tax_map

	def get_amount_and_base_amount(self, item, enable_discount_accounting):
		doc = self.doc
		amount = item.net_amount
		base_amount = item.base_net_amount

		if (
			enable_discount_accounting
			and doc.get("discount_amount")
			and doc.get("additional_discount_account")
		):
			if not hasattr(doc, "__has_distributed_discount_set"):
				doc.__has_distributed_discount_set = any(
					i.distributed_discount_amount for i in doc.get("items")
				)

			if not doc.__has_distributed_discount_set:
				return item.amount, item.base_amount

			amount += item.distributed_discount_amount
			base_amount += flt(
				item.distributed_discount_amount * doc.get("conversion_rate"),
				item.precision("distributed_discount_amount"),
			)

		return amount, base_amount

	def get_tax_amounts(self, tax, enable_discount_accounting):
		doc = self.doc
		amount = tax.tax_amount_after_discount_amount
		base_amount = tax.base_tax_amount_after_discount_amount

		if (
			enable_discount_accounting
			and doc.get("discount_amount")
			and doc.get("additional_discount_account")
			and doc.get("apply_discount_on") == "Grand Total"
		):
			amount = tax.tax_amount
			base_amount = tax.base_tax_amount

		return amount, base_amount


def get_tax_rate(account_head: str) -> dict:
	return frappe.get_cached_value("Account", account_head, ["tax_rate", "account_name"], as_dict=True)


@frappe.whitelist()
def get_default_taxes_and_charges(
	master_doctype: str, tax_template: str | None = None, company: str | None = None
) -> dict | None:
	if not company:
		return {}

	if tax_template and company:
		tax_template_company = frappe.get_cached_value(master_doctype, tax_template, "company")
		if tax_template_company == company:
			return

	default_tax = frappe.db.get_value(master_doctype, {"is_default": 1, "company": company})

	return {
		"taxes_and_charges": default_tax,
		"taxes": get_taxes_and_charges(master_doctype, default_tax),
	}


@frappe.whitelist()
def get_taxes_and_charges(master_doctype: str, master_name: str | None = None) -> list | None:
	if not master_name:
		return
	from frappe.model import child_table_fields, default_fields

	tax_master = frappe.get_doc(master_doctype, master_name)

	taxes_and_charges = []
	for _i, tax in enumerate(tax_master.get("taxes")):
		tax = tax.as_dict()

		for fieldname in default_fields + child_table_fields:
			if fieldname in tax:
				del tax[fieldname]

		taxes_and_charges.append(tax)

	return taxes_and_charges


def validate_conversion_rate(
	currency: str, conversion_rate: float, conversion_rate_label: str, company: str
) -> None:
	"""Throw a validation error if conversion_rate is falsy."""
	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	if not conversion_rate:
		throw(
			_("{0} is mandatory. Maybe Currency Exchange record is not created for {1} to {2}.").format(
				conversion_rate_label, currency, company_currency
			)
		)


def validate_taxes_and_charges(tax) -> None:
	if tax.charge_type in ["Actual", "On Net Total", "On Paid Amount"] and tax.row_id:
		frappe.throw(
			_("Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'")
		)
	elif tax.charge_type in ["On Previous Row Amount", "On Previous Row Total"]:
		if cint(tax.idx) == 1:
			frappe.throw(
				_(
					"Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"
				)
			)
		elif not tax.row_id:
			frappe.throw(
				_("Please specify a valid Row ID for row {0} in table {1}").format(tax.idx, _(tax.doctype))
			)
		elif tax.row_id and cint(tax.row_id) >= cint(tax.idx):
			frappe.throw(
				_("Cannot refer row number greater than or equal to current row number for this Charge type")
			)

	if tax.charge_type == "Actual":
		tax.rate = None


def validate_account_head(idx: int, account: str, company: str, context: str | None = None) -> None:
	"""Throw a ValidationError if the account belongs to a different company or is a group account."""
	if company != frappe.get_cached_value("Account", account, "company"):
		frappe.throw(
			_("Row {0}: The {3} Account {1} does not belong to the company {2}").format(
				idx, frappe.bold(account), frappe.bold(company), context or ""
			),
			title=_("Invalid Account"),
		)

	if frappe.get_cached_value("Account", account, "is_group"):
		frappe.throw(
			_(
				"You selected the account group {1} as {2} Account in row {0}. Please select a single account."
			).format(idx, frappe.bold(account), context or ""),
			title=_("Invalid Account"),
		)


def validate_cost_center(tax, doc) -> None:
	if not tax.cost_center:
		return

	company = frappe.get_cached_value("Cost Center", tax.cost_center, "company")

	if company != doc.company:
		frappe.throw(
			_("Row {0}: Cost Center {1} does not belong to Company {2}").format(
				tax.idx, frappe.bold(tax.cost_center), frappe.bold(doc.company)
			),
			title=_("Invalid Cost Center"),
		)


def validate_inclusive_tax(tax, doc) -> None:
	def _on_previous_row_error(row_range):
		throw(
			_("To include tax in row {0} in Item rate, taxes in rows {1} must also be included").format(
				tax.idx, row_range
			)
		)

	if cint(getattr(tax, "included_in_print_rate", None)):
		if tax.charge_type == "Actual":
			throw(
				_("Charge of type 'Actual' in row {0} cannot be included in Item Rate or Paid Amount").format(
					tax.idx
				)
			)
		elif tax.charge_type == "On Previous Row Amount" and not cint(
			doc.get("taxes")[cint(tax.row_id) - 1].included_in_print_rate
		):
			_on_previous_row_error(tax.row_id)
		elif tax.charge_type == "On Previous Row Total" and not all(
			[cint(t.included_in_print_rate) for t in doc.get("taxes")[: cint(tax.row_id) - 1]]
		):
			_on_previous_row_error("1 - %d" % (tax.row_id,))
		elif tax.get("category") == "Valuation":
			frappe.throw(_("Valuation type charges can not be marked as Inclusive"))


def set_balance_in_account_currency(
	gl_dict,
	account_currency: str | None = None,
	conversion_rate: float | None = None,
	company_currency: str | None = None,
) -> None:
	if (not conversion_rate) and (account_currency != company_currency):
		frappe.throw(
			_("Account: {0} with currency: {1} can not be selected").format(gl_dict.account, account_currency)
		)

	gl_dict["account_currency"] = account_currency

	if flt(gl_dict.debit) and not flt(gl_dict.debit_in_account_currency):
		gl_dict.debit_in_account_currency = (
			gl_dict.debit if account_currency == company_currency else flt(gl_dict.debit / conversion_rate, 2)
		)

	if flt(gl_dict.credit) and not flt(gl_dict.credit_in_account_currency):
		gl_dict.credit_in_account_currency = (
			gl_dict.credit
			if account_currency == company_currency
			else flt(gl_dict.credit / conversion_rate, 2)
		)


def set_child_tax_template_and_map(item, child_item, parent_doc) -> None:
	ctx = ItemDetailsCtx(
		{
			"item_code": item.item_code,
			"posting_date": parent_doc.transaction_date,
			"tax_category": parent_doc.get("tax_category"),
			"company": parent_doc.get("company"),
			"base_net_rate": item.get("base_net_rate"),
		}
	)

	item_tax_template = _get_item_tax_template(ctx, item.taxes)

	if not item_tax_template:
		item_tax_template = _get_item_tax_template_from_item_group(ctx, item.item_group)

	child_item.item_tax_template = item_tax_template
	child_item.item_tax_rate = get_item_tax_map(
		doc=parent_doc,
		tax_template=child_item.item_tax_template,
		as_json=True,
	)


def add_taxes_from_tax_template(child_item, parent_doc, db_insert: bool = True) -> None:
	add_taxes_from_item_tax_template = frappe.get_single_value(
		"Accounts Settings", "add_taxes_from_item_tax_template"
	)

	if child_item.get("item_tax_rate") and add_taxes_from_item_tax_template:
		tax_map = json.loads(child_item.get("item_tax_rate"))
		for tax_type, tax_rate in tax_map.items():
			if tax_rate == NOT_APPLICABLE_TAX:
				continue

			tax_rate = flt(tax_rate)
			taxes = parent_doc.get("taxes") or []
			found = any(tax.account_head == tax_type for tax in taxes)
			if not found:
				tax_row = parent_doc.append("taxes", {})
				tax_row.update(
					{
						"description": str(tax_type).split(" - ")[0],
						"charge_type": "On Net Total",
						"account_head": tax_type,
						"rate": tax_rate,
						"set_by_item_tax_template": 1,
					}
				)
				if parent_doc.doctype == "Purchase Order":
					tax_row.update({"category": "Total", "add_deduct_tax": "Add"})
				if db_insert:
					tax_row.db_insert()


def merge_taxes(source_doc, target_doc) -> None:
	tax_map = {}
	for tax in source_doc.get("taxes") or []:
		found = False
		for t in target_doc.get("taxes") or []:
			if t.account_head == tax.account_head and t.cost_center == tax.cost_center:
				t.tax_amount = flt(t.tax_amount) + flt(tax.tax_amount_after_discount_amount)
				t.base_tax_amount = flt(t.base_tax_amount) + flt(tax.base_tax_amount_after_discount_amount)
				tax_map[tax.name] = t
				found = True

		if not found:
			tax.charge_type = "Actual"
			tax.included_in_print_rate = 0
			tax.dont_recompute_tax = 1
			tax.row_id = None
			tax.idx = None
			tax.tax_amount = tax.tax_amount_after_discount_amount
			tax.base_tax_amount = tax.base_tax_amount_after_discount_amount
			tax_map[tax.name] = target_doc.append("taxes", tax)

	item_map = {d._old_name: d for d in target_doc.get("items") if d.get("_old_name")}

	item_tax_details = target_doc.get("_item_wise_tax_details") or []
	for row in source_doc.get("item_wise_tax_details"):
		item = item_map.get(row.item_row)
		tax = tax_map.get(row.tax_row)
		if not (item and tax):
			continue

		item_tax_details.append(
			frappe._dict(
				item=item,
				tax=tax,
				amount=row.amount,
				rate=row.rate,
				taxable_amount=row.taxable_amount,
			)
		)

	target_doc._item_wise_tax_details = item_tax_details
