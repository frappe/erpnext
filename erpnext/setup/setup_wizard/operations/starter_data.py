# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt, nowdate

STARTER_FIELDS = (
	"starter_customers",
	"starter_suppliers",
	"starter_items",
	"starter_stock",
	"starter_receivables",
	"starter_payables",
	"starter_bank_balance",
)


def has_starter_data(setup_values):
	return any(_parse_rows(setup_values.get(field)) for field in STARTER_FIELDS)


def create_starter_data(setup_values):
	created = frappe._dict(
		customers=[],
		suppliers=[],
		items=[],
		stock_entries=[],
		receivables=[],
		payables=[],
		bank_entries=[],
	)

	created.customers = create_customers(setup_values)
	created.suppliers = create_suppliers(setup_values)
	created.items = create_items(setup_values)
	created.stock_entries = create_opening_stock(setup_values)
	created.receivables = create_opening_invoices(setup_values, "Sales")
	created.payables = create_opening_invoices(setup_values, "Purchase")
	created.bank_entries = create_bank_balance(setup_values)

	return created


def create_customers(setup_values):
	customer_group = _first_existing("Customer Group", [_("Commercial"), _("Individual")])
	territory = _first_existing("Territory", [setup_values.get("country"), _("Rest Of The World")])
	customers = []

	for row in _parse_rows(setup_values.get("starter_customers")):
		customer_name = _clean(row.get("customer_name"))
		if not customer_name:
			continue

		existing = frappe.db.exists("Customer", {"customer_name": customer_name})
		if existing:
			customers.append(existing)
			continue

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_group": customer_group,
				"territory": territory,
				"customer_type": "Company",
			}
		)
		customer.flags.ignore_mandatory = True
		customer.insert(ignore_permissions=True)
		customers.append(customer.name)

	return customers


def create_suppliers(setup_values):
	supplier_group = _first_existing("Supplier Group", [_("Services"), _("Local")])
	suppliers = []

	for row in _parse_rows(setup_values.get("starter_suppliers")):
		supplier_name = _clean(row.get("supplier_name"))
		if not supplier_name:
			continue

		existing = frappe.db.exists("Supplier", {"supplier_name": supplier_name})
		if existing:
			suppliers.append(existing)
			continue

		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": supplier_name,
				"supplier_group": supplier_group,
				"supplier_type": "Company",
			}
		)
		supplier.flags.ignore_mandatory = True
		supplier.insert(ignore_permissions=True)
		suppliers.append(supplier.name)

	return suppliers


def create_items(setup_values):
	items = []

	for row in _parse_rows(setup_values.get("starter_items")):
		item_name = _clean(row.get("item_name"))
		if not item_name:
			continue

		existing = frappe.db.exists("Item", {"item_name": item_name}) or frappe.db.exists("Item", item_name)
		if existing:
			items.append(existing)
			continue

		is_stock_item = 1 if row.get("is_stock_item") else 0
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_name,
				"item_name": item_name,
				"item_group": _("Products") if is_stock_item else _("Services"),
				"stock_uom": "Nos",
				"is_stock_item": is_stock_item,
				"is_sales_item": 1 if row.get("is_sales_item") else 0,
				"is_purchase_item": 1 if row.get("is_purchase_item") else 0,
			}
		)
		item.flags.ignore_mandatory = True
		item.insert(ignore_permissions=True)
		items.append(item.name)

	return items


def create_opening_stock(setup_values):
	entries = []
	company = setup_values.get("company_name") or frappe.defaults.get_global_default("company")
	default_warehouse = _get_default_warehouse(company)
	temporary_opening_account = _get_temporary_opening_account(company)
	rows = _parse_rows(setup_values.get("starter_stock")) + _get_opening_stock_from_items(setup_values)

	for row in rows:
		item_code = _clean(row.get("item_code"))
		qty = flt(row.get("qty"))
		if not item_code or qty <= 0:
			continue

		item_code = _get_item(item_code) or item_code
		warehouse = row.get("warehouse") or default_warehouse
		if not warehouse:
			continue

		entry_name = _setup_name("SE", item_code, warehouse)
		if frappe.db.exists("Stock Entry", entry_name):
			entries.append(entry_name)
			continue

		stock_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"name": entry_name,
				"company": company,
				"purpose": "Material Receipt",
				"is_opening": "Yes",
				"posting_date": row.get("posting_date") or nowdate(),
				"set_posting_time": 1,
				"items": [
					{
						"item_code": item_code,
						"t_warehouse": warehouse,
						"qty": qty,
						"basic_rate": flt(row.get("valuation_rate")) or 0,
						"expense_account": temporary_opening_account,
						"allow_zero_valuation_rate": 1,
					}
				],
			}
		)
		stock_entry.flags.ignore_mandatory = True
		stock_entry.insert(ignore_permissions=True, set_name=entry_name)
		stock_entry.submit()
		entries.append(stock_entry.name)

	return entries


def _get_opening_stock_from_items(setup_values):
	rows = []
	for row in _parse_rows(setup_values.get("starter_items")):
		qty = flt(row.get("opening_qty"))
		if not row.get("is_stock_item") or qty <= 0:
			continue

		item_name = _clean(row.get("item_name"))
		if not item_name:
			continue

		rows.append({"item_code": item_name, "qty": qty})

	return rows


def create_opening_invoices(setup_values, invoice_type):
	fieldname = "starter_receivables" if invoice_type == "Sales" else "starter_payables"
	party_type = "Customer" if invoice_type == "Sales" else "Supplier"
	invoice_doctype = "Sales Invoice" if invoice_type == "Sales" else "Purchase Invoice"
	created = []

	rows = _parse_rows(setup_values.get(fieldname)) + _get_opening_invoice_rows_from_parties(
		setup_values, invoice_type
	)
	if not rows:
		return created

	company = setup_values.get("company_name") or frappe.defaults.get_global_default("company")

	temporary_opening_account = _get_temporary_opening_account(company)
	from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import (
		start_import,
	)

	invoices = []
	for row in rows:
		party = _clean(row.get("customer") if party_type == "Customer" else row.get("supplier"))
		amount = flt(row.get("amount"))
		if not party or amount <= 0:
			continue

		party = _get_party(party_type, party) or party
		if not frappe.db.exists(party_type, party):
			continue

		invoice_number = _setup_name("SI" if invoice_type == "Sales" else "PI", party)
		if frappe.db.exists(invoice_doctype, invoice_number):
			created.append(invoice_number)
			continue

		row = frappe._dict(
			{
				"party": party,
				"party_type": party_type,
				"outstanding_amount": amount,
				"posting_date": row.get("posting_date") or nowdate(),
				"due_date": row.get("posting_date") or nowdate(),
				"temporary_opening_account": temporary_opening_account,
				"invoice_number": invoice_number,
				"item_name": _("Opening Invoice Item"),
				"qty": 1,
			}
		)
		tool = frappe.new_doc("Opening Invoice Creation Tool")
		tool.company = company
		tool.invoice_type = invoice_type
		invoices.append(tool.get_invoice_dict(row))

	if invoices:
		created.extend(start_import(invoices))

	return created


def _get_opening_invoice_rows_from_parties(setup_values, invoice_type):
	rows = []
	if invoice_type == "Sales":
		fieldname = "starter_customers"
		party_name_field = "customer_name"
		party_field = "customer"
	else:
		fieldname = "starter_suppliers"
		party_name_field = "supplier_name"
		party_field = "supplier"

	for row in _parse_rows(setup_values.get(fieldname)):
		party = _clean(row.get(party_name_field))
		amount = flt(row.get("opening_amount"))
		if party and amount > 0:
			rows.append({party_field: party, "amount": amount})

	return rows


def _get_temporary_opening_account(company):
	from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import (
		get_temporary_opening_account,
	)

	return get_temporary_opening_account(company)


def create_bank_balance(setup_values):
	rows = _parse_rows(setup_values.get("starter_bank_balance"))
	if not rows:
		return []

	company = setup_values.get("company_name") or frappe.defaults.get_global_default("company")
	company_abbr = frappe.get_cached_value("Company", company, "abbr")
	equity_account = _get_account(company, root_type="Equity")
	created = []

	for row in rows:
		account_name = _clean(row.get("account_name")) or _("Opening Bank")
		amount = flt(row.get("amount"))
		if amount <= 0 or not equity_account:
			continue

		account = _get_or_create_bank_account(account_name, company, company_abbr)
		entry_name = _setup_name("JE-BANK", account)
		if frappe.db.exists("Journal Entry", entry_name):
			created.append(entry_name)
			continue

		journal_entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"name": entry_name,
				"voucher_type": "Opening Entry",
				"is_opening": "Yes",
				"company": company,
				"posting_date": row.get("posting_date") or nowdate(),
				"accounts": [
					{"account": account, "debit_in_account_currency": amount},
					{"account": equity_account, "credit_in_account_currency": amount},
				],
			}
		)
		journal_entry.flags.ignore_mandatory = True
		journal_entry.insert(ignore_permissions=True, set_name=entry_name)
		journal_entry.submit()
		created.append(journal_entry.name)

	return created


def _parse_rows(value):
	if not value:
		return []
	if isinstance(value, list):
		return [frappe._dict(row) for row in value if row]
	if isinstance(value, dict):
		return [frappe._dict(value)]
	try:
		parsed = json.loads(value)
	except (TypeError, ValueError):
		return []
	if isinstance(parsed, list):
		return [frappe._dict(row) for row in parsed if row]
	if isinstance(parsed, dict):
		return [frappe._dict(parsed)]
	return []


def _clean(value):
	return (value or "").strip()


def _first_existing(doctype, names):
	for name in names:
		if name and frappe.db.exists(doctype, name):
			return name
	return frappe.db.get_value(doctype, {"is_group": 0}, "name")


def _get_item(item):
	return frappe.db.exists("Item", item) or frappe.db.get_value("Item", {"item_name": item})


def _get_party(party_type, party):
	party_name_field = "customer_name" if party_type == "Customer" else "supplier_name"
	return frappe.db.exists(party_type, party) or frappe.db.get_value(party_type, {party_name_field: party})


def _get_default_warehouse(company):
	warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
	if warehouse:
		return warehouse
	return frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": _("Stores")})


def _get_account(company, **filters):
	filters.update({"company": company, "is_group": 0})
	return frappe.db.get_value("Account", filters, "name")


def _get_or_create_bank_account(account_name, company, company_abbr):
	account = frappe.db.exists("Account", f"{account_name} - {company_abbr}")
	if account:
		return account

	parent_account = _get_account(company, root_type="Asset", account_type="Bank") or _get_account(
		company, root_type="Asset"
	)
	parent = frappe.get_cached_value("Account", parent_account, "parent_account") if parent_account else None

	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": account_name,
			"parent_account": parent or parent_account,
			"company": company,
			"account_type": "Bank",
		}
	)
	account.flags.ignore_mandatory = True
	account.insert(ignore_permissions=True)
	return account.name


def _setup_name(prefix, *parts):
	name = "-".join([prefix, *[frappe.scrub(str(part)).replace("_", "-") for part in parts if part]])
	return name[:140]
