# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Base class and free functions for per-document GL entry composition.

``BaseGLComposer`` holds the document being composed and exposes
``get_gl_dict`` / ``add_gl_entry`` as instance methods. The underlying logic
lives in the module-level free functions below (``doc`` as first argument), so
``AccountsController`` and ``StockController`` can delegate to them via thin
shims without forcing every GL-building doctype to inherit from those classes.

Subclasses implement ``compose`` to return the voucher-specific list of GL
entries.
"""

import frappe
from frappe import _
from frappe.utils import flt, formatdate

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from erpnext.accounts.services.taxes import set_balance_in_account_currency
from erpnext.accounts.utils import get_account_currency, get_fiscal_years
from erpnext.utilities.regional import temporary_flag


def get_gl_dict(doc, args: dict, account_currency: str | None = None, item=None) -> dict:
	"""Build a GL entry dict populated with doc-level fields."""
	posting_date = args.get("posting_date") or doc.get("posting_date")
	fiscal_years = get_fiscal_years(posting_date, company=doc.company)
	if len(fiscal_years) > 1:
		frappe.throw(
			_("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(
				formatdate(posting_date)
			)
		)
	else:
		fiscal_year = fiscal_years[0][0]

	gl_dict = frappe._dict(
		{
			"company": doc.company,
			"posting_date": posting_date,
			"fiscal_year": fiscal_year,
			"voucher_type": doc.doctype,
			"voucher_no": doc.name,
			"remarks": doc.get("remarks") or doc.get("remark"),
			"debit": 0,
			"credit": 0,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": 0,
			"is_opening": doc.get("is_opening") or "No",
			"party_type": None,
			"party": None,
			"project": doc.get("project"),
			"post_net_value": args.get("post_net_value"),
			"voucher_detail_no": args.get("voucher_detail_no"),
			"voucher_subtype": get_voucher_subtype(doc),
		}
	)

	with temporary_flag("company", doc.company):
		update_gl_dict_with_regional_fields(doc, gl_dict)

	update_gl_dict_with_app_based_fields(doc, gl_dict)

	accounting_dimensions = get_accounting_dimensions()
	dimension_dict = frappe._dict()
	for dimension in accounting_dimensions:
		dimension_dict[dimension] = doc.get(dimension)
		if item and item.get(dimension):
			dimension_dict[dimension] = item.get(dimension)

	gl_dict.update(dimension_dict)
	gl_dict.update(args)

	if not account_currency:
		account_currency = get_account_currency(gl_dict.account)

	if gl_dict.account and doc.doctype not in [
		"Journal Entry",
		"Period Closing Voucher",
		"Payment Entry",
		"Purchase Receipt",
		"Purchase Invoice",
		"Stock Entry",
	]:
		validate_account_currency(doc, gl_dict.account, account_currency)

	if gl_dict.account and doc.doctype not in [
		"Journal Entry",
		"Period Closing Voucher",
		"Payment Entry",
	]:
		set_balance_in_account_currency(
			gl_dict,
			account_currency,
			args.get("transaction_exchange_rate") or doc.get("conversion_rate"),
			doc.company_currency,
		)

	if doc.doctype not in ["Purchase Invoice", "Sales Invoice", "Journal Entry", "Payment Entry"]:
		gl_dict.update(
			{
				"transaction_currency": doc.get("currency") or doc.company_currency,
				"transaction_exchange_rate": args.get("transaction_exchange_rate")
				or doc.get("conversion_rate", 1),
				"debit_in_transaction_currency": get_value_in_transaction_currency(
					doc, account_currency, gl_dict, "debit"
				),
				"credit_in_transaction_currency": get_value_in_transaction_currency(
					doc, account_currency, gl_dict, "credit"
				),
			}
		)

	if not args.get("against_voucher_type") and doc.get("against_voucher_type"):
		gl_dict.update({"against_voucher_type": doc.get("against_voucher_type")})

	if not args.get("against_voucher") and doc.get("against_voucher"):
		gl_dict.update({"against_voucher": doc.get("against_voucher")})

	return gl_dict


def add_gl_entry(
	doc,
	gl_entries: list,
	account: str,
	cost_center: str,
	debit: float,
	credit: float,
	remarks: str,
	against_account: str,
	debit_in_account_currency: float | None = None,
	credit_in_account_currency: float | None = None,
	account_currency: str | None = None,
	project: str | None = None,
	voucher_detail_no: str | None = None,
	item=None,
	posting_date=None,
) -> None:
	"""Build a GL entry via get_gl_dict and append it to gl_entries."""
	gl_entry = {
		"account": account,
		"cost_center": cost_center,
		"debit": debit,
		"credit": credit,
		"against": against_account,
		"remarks": remarks,
	}

	if voucher_detail_no:
		gl_entry["voucher_detail_no"] = voucher_detail_no

	if debit_in_account_currency:
		gl_entry["debit_in_account_currency"] = debit_in_account_currency

	if credit_in_account_currency:
		gl_entry["credit_in_account_currency"] = credit_in_account_currency

	if posting_date:
		gl_entry["posting_date"] = posting_date

	gl_entries.append(get_gl_dict(doc, gl_entry, account_currency, item=item))


def get_voucher_subtype(doc) -> str:
	voucher_subtypes = {
		"Journal Entry": "voucher_type",
		"Payment Entry": "payment_type",
		"Stock Entry": "stock_entry_type",
		"Asset Capitalization": "entry_type",
	}

	for method_name in frappe.get_hooks("voucher_subtypes"):
		voucher_subtype = frappe.get_attr(method_name)(doc)
		if voucher_subtype:
			return voucher_subtype

	if doc.doctype in voucher_subtypes:
		return doc.get(voucher_subtypes[doc.doctype])
	elif doc.doctype == "Purchase Receipt" and doc.is_return:
		return "Purchase Return"
	elif doc.doctype == "Delivery Note" and doc.is_return:
		return "Sales Return"
	elif doc.doctype == "Sales Invoice" and doc.is_return:
		return "Credit Note"
	elif doc.doctype == "Sales Invoice" and doc.is_debit_note:
		return "Debit Note"
	elif doc.doctype == "Purchase Invoice" and doc.is_return:
		return "Debit Note"

	return doc.doctype


def get_value_in_transaction_currency(doc, account_currency: str, gl_dict: dict, field: str) -> float:
	if account_currency == doc.get("currency"):
		return gl_dict.get(field + "_in_account_currency")
	return flt(gl_dict.get(field, 0) / doc.get("conversion_rate", 1))


def validate_account_currency(doc, account: str, account_currency: str | None = None) -> None:
	valid_currency = [doc.company_currency]
	if doc.get("currency") and doc.currency != doc.company_currency:
		valid_currency.append(doc.currency)

	if account_currency not in valid_currency:
		frappe.throw(
			_("Account {0} is invalid. Account Currency must be {1}").format(
				account, (" " + _("or") + " ").join(valid_currency)
			)
		)


@erpnext.allow_regional
def update_gl_dict_with_regional_fields(doc, gl_dict):
	pass


def update_gl_dict_with_app_based_fields(doc, gl_dict):
	for method in frappe.get_hooks("update_gl_dict_with_app_based_fields", default=[]):
		frappe.get_attr(method)(doc, gl_dict)


class BaseGLComposer:
	def __init__(self, doc):
		self.doc = doc

	def compose(self):
		raise NotImplementedError

	def get_gl_dict(self, args: dict, account_currency: str | None = None, item=None) -> dict:
		return get_gl_dict(self.doc, args, account_currency, item)

	def add_gl_entry(
		self,
		gl_entries: list,
		account: str,
		cost_center: str,
		debit: float,
		credit: float,
		remarks: str,
		against_account: str,
		debit_in_account_currency: float | None = None,
		credit_in_account_currency: float | None = None,
		account_currency: str | None = None,
		project: str | None = None,
		voucher_detail_no: str | None = None,
		item=None,
		posting_date=None,
	) -> None:
		add_gl_entry(
			self.doc,
			gl_entries,
			account,
			cost_center,
			debit,
			credit,
			remarks,
			against_account,
			debit_in_account_currency,
			credit_in_account_currency,
			account_currency,
			project,
			voucher_detail_no,
			item,
			posting_date,
		)
