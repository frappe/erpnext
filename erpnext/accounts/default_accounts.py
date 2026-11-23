# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Registry of the default accounts of a Company.

Each purpose defines one default account: its label, the filters an account must match and
where the account is stored. Read and write default accounts with `get_default_account` and
`set_default_account` instead of the Company fields.

Other apps add purposes with the hook `company_default_accounts`, a list of dicts with the
fields of `DefaultAccountPurpose`.
"""

from dataclasses import dataclass

import frappe
from frappe import _

BANK = "BANK"
CASH = "CASH"
RECEIVABLE = "RECEIVABLE"
PAYABLE = "PAYABLE"
WRITE_OFF = "WRITE_OFF"
BANK_CHARGES = "BANK_CHARGES"
UNREALIZED_PROFIT_LOSS = "UNREALIZED_PROFIT_LOSS"
COST_OF_GOODS_SOLD = "COST_OF_GOODS_SOLD"
INCOME = "INCOME"
PAYMENT_DISCOUNT = "PAYMENT_DISCOUNT"
EXCHANGE_GAIN_LOSS = "EXCHANGE_GAIN_LOSS"
EXCHANGE_GAIN = "EXCHANGE_GAIN"
EXCHANGE_LOSS = "EXCHANGE_LOSS"
UNREALIZED_EXCHANGE_GAIN_LOSS = "UNREALIZED_EXCHANGE_GAIN_LOSS"
ROUND_OFF = "ROUND_OFF"
ROUND_OFF_FOR_OPENING = "ROUND_OFF_FOR_OPENING"
DEFERRED_REVENUE = "DEFERRED_REVENUE"
DEFERRED_EXPENSE = "DEFERRED_EXPENSE"
ADVANCE_RECEIVED = "ADVANCE_RECEIVED"
ADVANCE_PAID = "ADVANCE_PAID"
ACCUMULATED_DEPRECIATION = "ACCUMULATED_DEPRECIATION"
DEPRECIATION_EXPENSE = "DEPRECIATION_EXPENSE"
ASSET_DISPOSAL = "ASSET_DISPOSAL"
CAPITAL_WORK_IN_PROGRESS = "CAPITAL_WORK_IN_PROGRESS"
ASSET_RECEIVED_BUT_NOT_BILLED = "ASSET_RECEIVED_BUT_NOT_BILLED"
PURCHASE_EXPENSE = "PURCHASE_EXPENSE"
SERVICE_EXPENSE = "SERVICE_EXPENSE"
PURCHASE_EXPENSE_CONTRA = "PURCHASE_EXPENSE_CONTRA"
EXPENSES_ADDED_TO_STOCK = "EXPENSES_ADDED_TO_STOCK"
EXPENSES_ADDED_TO_STOCK_CONTRA = "EXPENSES_ADDED_TO_STOCK_CONTRA"
INVENTORY = "INVENTORY"
STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT"
PURCHASE_PRICE_VARIANCE = "PURCHASE_PRICE_VARIANCE"
MANUFACTURING_VARIANCE = "MANUFACTURING_VARIANCE"
STOCK_RECEIVED_BUT_NOT_BILLED = "STOCK_RECEIVED_BUT_NOT_BILLED"
STOCK_DELIVERED_BUT_NOT_BILLED = "STOCK_DELIVERED_BUT_NOT_BILLED"
PROVISIONAL = "PROVISIONAL"
OPERATING_COST = "OPERATING_COST"


@dataclass(frozen=True)
class DefaultAccountPurpose:
	key: str
	# Untranslated label, for example "Default Receivable Account"
	label: str
	# Account filters, each value is a str or ["in", [...]]
	filters: dict
	# Company field that stores the account
	fieldname: str | None = None
	# Purpose to use when this purpose has no account
	fallback: str | None = None
	# Account type to find the account when a Company is set up
	account_type: str | None = None
	# Find the account on setup only when perpetual inventory is enabled
	perpetual_inventory_only: bool = False


# Order of the Company form
DEFAULT_ACCOUNT_PURPOSES = [
	DefaultAccountPurpose(
		key=BANK,
		label="Default Bank Account",
		filters={"account_type": "Bank"},
		fieldname="default_bank_account",
		account_type="Bank",
	),
	DefaultAccountPurpose(
		key=CASH,
		label="Default Cash Account",
		filters={"account_type": "Cash"},
		fieldname="default_cash_account",
		account_type="Cash",
	),
	DefaultAccountPurpose(
		key=RECEIVABLE,
		label="Default Receivable Account",
		filters={"root_type": "Asset", "account_type": "Receivable"},
		fieldname="default_receivable_account",
	),
	DefaultAccountPurpose(
		key=PAYABLE,
		label="Default Payable Account",
		filters={"root_type": "Liability", "account_type": "Payable"},
		fieldname="default_payable_account",
	),
	DefaultAccountPurpose(
		key=WRITE_OFF,
		label="Write Off Account",
		filters={"root_type": "Expense"},
		fieldname="write_off_account",
	),
	DefaultAccountPurpose(
		key=BANK_CHARGES,
		label="Bank Charges Account",
		filters={"root_type": "Expense"},
		fieldname="bank_charges_account",
	),
	DefaultAccountPurpose(
		key=UNREALIZED_PROFIT_LOSS,
		label="Unrealized Profit / Loss Account",
		filters={"root_type": ["in", ["Liability", "Asset"]]},
		fieldname="unrealized_profit_loss_account",
	),
	DefaultAccountPurpose(
		key=COST_OF_GOODS_SOLD,
		label="Default Cost of Goods Sold Account",
		filters={"root_type": "Expense"},
		fieldname="default_expense_account",
		account_type="Cost of Goods Sold",
	),
	DefaultAccountPurpose(
		key=INCOME,
		label="Default Income Account",
		filters={"root_type": "Income"},
		fieldname="default_income_account",
	),
	DefaultAccountPurpose(
		key=PAYMENT_DISCOUNT,
		label="Default Payment Discount Account",
		filters={},
		fieldname="default_discount_account",
	),
	DefaultAccountPurpose(
		key=EXCHANGE_GAIN_LOSS,
		label="Exchange Gain / Loss Account",
		filters={"root_type": ["in", ["Expense", "Income"]]},
		fieldname="exchange_gain_loss_account",
	),
	DefaultAccountPurpose(
		key=EXCHANGE_GAIN,
		label="Exchange Gain Account",
		filters={"root_type": ["in", ["Expense", "Income"]]},
		fieldname="exchange_gain_account",
		fallback=EXCHANGE_GAIN_LOSS,
	),
	DefaultAccountPurpose(
		key=EXCHANGE_LOSS,
		label="Exchange Loss Account",
		filters={"root_type": ["in", ["Expense", "Income"]]},
		fieldname="exchange_loss_account",
		fallback=EXCHANGE_GAIN_LOSS,
	),
	DefaultAccountPurpose(
		key=UNREALIZED_EXCHANGE_GAIN_LOSS,
		label="Unrealized Exchange Gain/Loss Account",
		filters={"root_type": ["in", ["Expense", "Income", "Equity", "Liability"]]},
		fieldname="unrealized_exchange_gain_loss_account",
	),
	DefaultAccountPurpose(
		key=ROUND_OFF,
		label="Round Off Account",
		filters={"root_type": ["in", ["Expense", "Income"]]},
		fieldname="round_off_account",
		account_type="Round Off",
	),
	DefaultAccountPurpose(
		key=ROUND_OFF_FOR_OPENING,
		label="Round Off for Opening",
		filters={"root_type": "Liability", "account_type": "Round Off for Opening"},
		fieldname="round_off_for_opening",
	),
	DefaultAccountPurpose(
		key=DEFERRED_REVENUE,
		label="Default Deferred Revenue Account",
		filters={},
		fieldname="default_deferred_revenue_account",
	),
	DefaultAccountPurpose(
		key=DEFERRED_EXPENSE,
		label="Default Deferred Expense Account",
		filters={},
		fieldname="default_deferred_expense_account",
	),
	DefaultAccountPurpose(
		key=ADVANCE_RECEIVED,
		label="Default Advance Received Account",
		filters={"root_type": "Liability", "account_type": "Receivable"},
		fieldname="default_advance_received_account",
	),
	DefaultAccountPurpose(
		key=ADVANCE_PAID,
		label="Default Advance Paid Account",
		filters={"root_type": "Asset", "account_type": "Payable"},
		fieldname="default_advance_paid_account",
	),
	DefaultAccountPurpose(
		key=ACCUMULATED_DEPRECIATION,
		label="Accumulated Depreciation Account",
		filters={"root_type": "Asset", "account_type": "Accumulated Depreciation"},
		fieldname="accumulated_depreciation_account",
		account_type="Accumulated Depreciation",
	),
	DefaultAccountPurpose(
		key=DEPRECIATION_EXPENSE,
		label="Depreciation Expense Account",
		filters={"root_type": "Expense", "account_type": "Depreciation"},
		fieldname="depreciation_expense_account",
		account_type="Depreciation",
	),
	DefaultAccountPurpose(
		key=ASSET_DISPOSAL,
		label="Gain/Loss Account on Asset Disposal",
		filters={"report_type": "Profit and Loss"},
		fieldname="disposal_account",
	),
	DefaultAccountPurpose(
		key=CAPITAL_WORK_IN_PROGRESS,
		label="Capital Work In Progress Account",
		filters={"account_type": "Capital Work in Progress"},
		fieldname="capital_work_in_progress_account",
		account_type="Capital Work in Progress",
	),
	DefaultAccountPurpose(
		key=ASSET_RECEIVED_BUT_NOT_BILLED,
		label="Asset Received But Not Billed",
		filters={"account_type": "Asset Received But Not Billed"},
		fieldname="asset_received_but_not_billed",
		account_type="Asset Received But Not Billed",
	),
	DefaultAccountPurpose(
		key=PURCHASE_EXPENSE,
		label="Purchase Expense Account",
		filters={"root_type": "Expense"},
		fieldname="purchase_expense_account",
	),
	DefaultAccountPurpose(
		key=SERVICE_EXPENSE,
		label="Service Expense Account",
		filters={"root_type": "Expense"},
		fieldname="service_expense_account",
	),
	DefaultAccountPurpose(
		key=PURCHASE_EXPENSE_CONTRA,
		label="Purchase Expense Contra Account",
		filters={"root_type": "Expense"},
		fieldname="purchase_expense_contra_account",
	),
	DefaultAccountPurpose(
		key=EXPENSES_ADDED_TO_STOCK,
		label="Expenses Added To Stock Account",
		filters={"root_type": "Expense"},
		fieldname="expenses_added_to_stock_account",
	),
	DefaultAccountPurpose(
		key=EXPENSES_ADDED_TO_STOCK_CONTRA,
		label="Expenses Added To Stock Contra Account",
		filters={"root_type": "Expense"},
		fieldname="expenses_added_to_stock_contra_account",
	),
	DefaultAccountPurpose(
		key=INVENTORY,
		label="Default Inventory Account",
		filters={"account_type": "Stock"},
		fieldname="default_inventory_account",
		account_type="Stock",
		perpetual_inventory_only=True,
	),
	DefaultAccountPurpose(
		key=STOCK_ADJUSTMENT,
		label="Stock Adjustment Account",
		filters={"root_type": "Expense", "account_type": "Stock Adjustment"},
		fieldname="stock_adjustment_account",
		account_type="Stock Adjustment",
		perpetual_inventory_only=True,
	),
	DefaultAccountPurpose(
		key=PURCHASE_PRICE_VARIANCE,
		label="Default Purchase Price Variance Account",
		filters={},
		fieldname="default_purchase_price_variance_account",
	),
	DefaultAccountPurpose(
		key=MANUFACTURING_VARIANCE,
		label="Default Manufacturing Variance Account",
		filters={},
		fieldname="default_manufacturing_variance_account",
	),
	DefaultAccountPurpose(
		key=STOCK_RECEIVED_BUT_NOT_BILLED,
		label="Stock Received But Not Billed",
		filters={"root_type": "Liability", "account_type": "Stock Received But Not Billed"},
		fieldname="stock_received_but_not_billed",
		account_type="Stock Received But Not Billed",
		perpetual_inventory_only=True,
	),
	DefaultAccountPurpose(
		key=STOCK_DELIVERED_BUT_NOT_BILLED,
		label="Stock Delivered But Not Billed",
		filters={"root_type": "Asset", "account_type": "Stock Delivered But Not Billed"},
		fieldname="stock_delivered_but_not_billed",
		account_type="Stock Delivered But Not Billed",
		perpetual_inventory_only=True,
	),
	DefaultAccountPurpose(
		key=PROVISIONAL,
		label="Default Provisional Account",
		filters={"root_type": ["in", ["Liability", "Asset"]]},
		fieldname="default_provisional_account",
	),
	DefaultAccountPurpose(
		key=OPERATING_COST,
		label="Default Operating Cost Account",
		filters={"root_type": "Expense"},
		fieldname="default_operating_cost_account",
	),
]


def get_purposes() -> dict[str, DefaultAccountPurpose]:
	"""Return all purposes by key: the ERPNext purposes, then the purposes of other apps."""
	purposes = {purpose.key: purpose for purpose in DEFAULT_ACCOUNT_PURPOSES}
	for entry in frappe.get_hooks("company_default_accounts"):
		purpose = DefaultAccountPurpose(**entry)
		purposes[purpose.key] = purpose

	return purposes


def get_purpose(key: str) -> DefaultAccountPurpose:
	purpose = get_purposes().get(key)
	if not purpose:
		frappe.throw(_("{0} is not a valid default account purpose").format(key))

	return purpose


def get_default_account(company: str, purpose: str, required: bool = False) -> str | None:
	"""Return the account of this purpose, else the account of its fallback purpose.

	If no account is found and `required` is set, throw an error.
	"""
	return frappe.get_cached_doc("Company", company).get_default_account(purpose, required)


def set_default_account(company: str, purpose: str, account: str | None) -> None:
	"""Store the account of this purpose without validation. Do not change the Company timestamp."""
	frappe.db.set_value("Company", company, get_purpose(purpose).fieldname, account, update_modified=False)


@frappe.whitelist()
def get_purpose_options() -> list[dict]:
	return [
		{
			"value": purpose.key,
			"label": _(purpose.label),
			"filters": purpose.filters,
			"fieldname": purpose.fieldname,
		}
		for purpose in get_purposes().values()
	]


@frappe.whitelist()
def get_company_default_account(company: str, purpose: str) -> str | None:
	frappe.has_permission("Company", "read", company, throw=True)
	return get_default_account(company, purpose)
