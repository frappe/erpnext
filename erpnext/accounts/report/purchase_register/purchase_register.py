# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import flt, getdate
from pypika import Order

from erpnext.accounts.party import get_party_account
from erpnext.accounts.report.utils import (
	apply_common_conditions,
	get_advance_taxes_and_charges,
	get_journal_entries,
	get_opening_row,
	get_party_details,
	get_payment_entries,
	get_query_columns,
	get_taxes_query,
	get_values_for_columns,
)


def execute(filters=None):
	return _execute(filters)


def _execute(filters=None, additional_table_columns=None):
	if not filters:
		filters = {}

	include_payments = filters.get("include_payments")
	if filters.get("include_payments") and not filters.get("supplier"):
		frappe.throw(_("Please select a supplier for fetching payments."))
	invoice_list = get_invoices(filters, get_query_columns(additional_table_columns))
	if filters.get("include_payments"):
		invoice_list += get_payments(filters)

	columns, expense_accounts, tax_accounts, unrealized_profit_loss_accounts = get_columns(
		invoice_list, additional_table_columns, include_payments
	)

	if not invoice_list:
		msgprint(_("No record found"))
		return columns, invoice_list

	invoice_expense_map = get_invoice_expense_map(invoice_list)
	internal_invoice_map = get_internal_invoice_map(invoice_list)
	invoice_expense_map, invoice_tax_map = get_invoice_tax_map(
		invoice_list, invoice_expense_map, expense_accounts, include_payments
	)
	invoice_po_pr_map = get_invoice_po_pr_map(invoice_list)
	suppliers = list(set(d.supplier for d in invoice_list))
	supplier_details = get_party_details("Supplier", suppliers)

	company_currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	res = []
	if include_payments:
		opening_row = get_opening_row(
			"Supplier", filters.supplier, getdate(filters.from_date), filters.company
		)[0]
		res.append(
			{
				"payable_account": opening_row.account,
				"debit": flt(opening_row.debit),
				"credit": flt(opening_row.credit),
				"balance": flt(opening_row.balance),
			}
		)

	data = []
	for inv in invoice_list:
		# invoice details
		purchase_order = list(set(invoice_po_pr_map.get(inv.name, {}).get("purchase_order", [])))
		purchase_receipt = list(set(invoice_po_pr_map.get(inv.name, {}).get("purchase_receipt", [])))
		project = list(set(invoice_po_pr_map.get(inv.name, {}).get("project", [])))

		row = {
			"voucher_type": inv.doctype,
			"voucher_no": inv.name,
			"posting_date": inv.posting_date,
			"supplier_id": inv.supplier,
			"supplier_name": inv.supplier_name,
			**get_values_for_columns(additional_table_columns, inv),
			"supplier_group": supplier_details.get(inv.supplier).get("supplier_group"),
			"tax_id": supplier_details.get(inv.supplier).get("tax_id"),
			"payable_account": inv.credit_to,
			"mode_of_payment": inv.mode_of_payment,
			"project": ", ".join(project) if inv.doctype == "Purchase Invoice" else inv.project,
			"bill_no": inv.bill_no,
			"bill_date": inv.bill_date,
			"remarks": inv.remarks,
			"purchase_order": ", ".join(purchase_order),
			"purchase_receipt": ", ".join(purchase_receipt),
			"currency": company_currency,
		}

		# map expense values
		base_net_total = 0
		for expense_acc in expense_accounts:
			if inv.is_internal_supplier and inv.company == inv.represents_company:
				expense_amount = 0
			else:
				expense_amount = flt(invoice_expense_map.get(inv.name, {}).get(expense_acc))
			base_net_total += expense_amount
			row.update({frappe.scrub(expense_acc): expense_amount})

		# Add amount in unrealized account
		for account in unrealized_profit_loss_accounts:
			row.update(
				{frappe.scrub(account + "_unrealized"): flt(internal_invoice_map.get((inv.name, account)))}
			)

		# net total
		row.update({"net_total": base_net_total or inv.base_net_total})

		# tax account
		total_tax = 0
		for tax_acc in tax_accounts:
			if tax_acc not in expense_accounts:
				tax_amount = flt(invoice_tax_map.get(inv.name, {}).get(tax_acc))
				total_tax += tax_amount
				row.update({frappe.scrub(tax_acc): tax_amount})

		# total tax, grand total, rounded total & outstanding amount
		row.update(
			{
				"total_tax": total_tax,
				"grand_total": inv.base_grand_total,
				"rounded_total": inv.base_rounded_total,
				"outstanding_amount": inv.outstanding_amount,
			}
		)

		if inv.doctype == "Purchase Invoice":
			row.update({"debit": inv.base_grand_total, "credit": 0.0})
		else:
			row.update({"debit": 0.0, "credit": inv.base_grand_total})
		data.append(row)

	res += sorted(data, key=lambda x: x["posting_date"])

	if include_payments:
		running_balance = flt(opening_row.balance)
		for row in range(1, len(res)):
			running_balance += res[row]["debit"] - res[row]["credit"]
			res[row].update({"balance": running_balance})

	return columns, res, None, None, None, include_payments


def get_columns(invoice_list, additional_table_columns, include_payments=False):
	"""return columns based on filters"""
	columns = [
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 120,
		},
		{
			"label": _("Voucher"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 120,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 80},
		{
			"label": _("Supplier"),
			"fieldname": "supplier_id",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 120,
		},
		{"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 120},
	]

	if additional_table_columns and not include_payments:
		columns += additional_table_columns

	if not include_payments:
		columns += [
			{
				"label": _("Supplier Group"),
				"fieldname": "supplier_group",
				"fieldtype": "Link",
				"options": "Supplier Group",
				"width": 120,
			},
			{"label": _("Tax Id"), "fieldname": "tax_id", "fieldtype": "Data", "width": 80},
			{
				"label": _("Payable Account"),
				"fieldname": "payable_account",
				"fieldtype": "Link",
				"options": "Account",
				"width": 100,
			},
			{
				"label": _("Mode Of Payment"),
				"fieldname": "mode_of_payment",
				"fieldtype": "Data",
				"width": 120,
			},
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 80,
			},
			{"label": _("Bill No"), "fieldname": "bill_no", "fieldtype": "Data", "width": 120},
			{"label": _("Bill Date"), "fieldname": "bill_date", "fieldtype": "Date", "width": 80},
			{
				"label": _("Purchase Order"),
				"fieldname": "purchase_order",
				"fieldtype": "Link",
				"options": "Purchase Order",
				"width": 100,
			},
			{
				"label": _("Purchase Receipt"),
				"fieldname": "purchase_receipt",
				"fieldtype": "Link",
				"options": "Purchase Receipt",
				"width": 100,
			},
			{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Data", "width": 80},
		]
	else:
		columns += [
			{
				"fieldname": "payable_account",
				"label": _("Payable Account"),
				"fieldtype": "Link",
				"options": "Account",
				"width": 120,
			},
			{"fieldname": "debit", "label": _("Debit"), "fieldtype": "Currency", "width": 120},
			{"fieldname": "credit", "label": _("Credit"), "fieldtype": "Currency", "width": 120},
			{"fieldname": "balance", "label": _("Balance"), "fieldtype": "Currency", "width": 120},
		]

	account_columns, accounts = get_account_columns(invoice_list, include_payments)

	columns = (
		columns
		+ account_columns[0]
		+ account_columns[1]
		+ [
			{
				"label": _("Net Total"),
				"fieldname": "net_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		]
		+ account_columns[2]
		+ [
			{
				"label": _("Total Tax"),
				"fieldname": "total_tax",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		]
	)

	if not include_payments:
		columns += [
			{
				"label": _("Grand Total"),
				"fieldname": "grand_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Rounded Total"),
				"fieldname": "rounded_total",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Outstanding Amount"),
				"fieldname": "outstanding_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
		]
	columns += [{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 120}]
	return columns, accounts[0], accounts[2], accounts[1]


def get_account_columns(invoice_list, include_payments):
	expense_accounts = []
	tax_accounts = []
	unrealized_profit_loss_accounts = []

	expense_columns = []
	tax_columns = []
	unrealized_profit_loss_account_columns = []

	if invoice_list:
		expense_accounts = frappe.db.sql_list(
			"""select distinct expense_account
			from `tabPurchase Invoice Item` where docstatus = 1
			and (expense_account is not null and expense_account != '')
			and parent in (%s) order by expense_account"""
			% ", ".join(["%s"] * len(invoice_list)),
			tuple([inv.name for inv in invoice_list]),
		)

		purchase_taxes_query = get_taxes_query(invoice_list, "Purchase Taxes and Charges", "Purchase Invoice")
		purchase_tax_accounts = purchase_taxes_query.run(as_dict=True, pluck="account_head")
		tax_accounts = purchase_tax_accounts

		if include_payments:
			advance_taxes_query = get_taxes_query(invoice_list, "Advance Taxes and Charges", "Payment Entry")
			advance_tax_accounts = advance_taxes_query.run(as_dict=True, pluck="account_head")
			tax_accounts = set(tax_accounts + advance_tax_accounts)

		unrealized_profit_loss_accounts = frappe.db.sql_list(
			"""SELECT distinct unrealized_profit_loss_account
			from `tabPurchase Invoice` where docstatus = 1 and name in (%s)
			and ifnull(unrealized_profit_loss_account, '') != ''
			order by unrealized_profit_loss_account"""
			% ", ".join(["%s"] * len(invoice_list)),
			tuple(inv.name for inv in invoice_list),
		)

	for account in expense_accounts:
		expense_columns.append(
			{
				"label": account,
				"fieldname": frappe.scrub(account),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		)

	for account in tax_accounts:
		if account not in expense_accounts:
			tax_columns.append(
				{
					"label": account,
					"fieldname": frappe.scrub(account),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120,
				}
			)

	for account in unrealized_profit_loss_accounts:
		unrealized_profit_loss_account_columns.append(
			{
				"label": account,
				"fieldname": frappe.scrub(account),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		)

	columns = [expense_columns, unrealized_profit_loss_account_columns, tax_columns]
	accounts = [expense_accounts, unrealized_profit_loss_accounts, tax_accounts]

	return columns, accounts


def get_invoices(filters, additional_query_columns):
	pi = frappe.qb.DocType("Purchase Invoice")
	query = (
		frappe.qb.from_(pi)
		.select(
			ConstantColumn("Purchase Invoice").as_("doctype"),
			pi.name,
			pi.posting_date,
			pi.credit_to,
			pi.supplier,
			pi.supplier_name,
			pi.tax_id,
			pi.bill_no,
			pi.bill_date,
			pi.remarks,
			pi.base_net_total,
			pi.base_grand_total,
			pi.base_rounded_total,
			pi.outstanding_amount,
			pi.mode_of_payment,
		)
		.where(pi.docstatus == 1)
		.orderby(pi.posting_date, pi.name, order=Order.desc)
	)

	if additional_query_columns:
		for col in additional_query_columns:
			query = query.select(col)

	if filters.get("supplier"):
		query = query.where(pi.supplier == filters.supplier)
	if filters.get("supplier_group"):
		query = query.where(pi.supplier_group == filters.supplier_group)

	query = get_conditions(filters, query, "Purchase Invoice")

	query = apply_common_conditions(
		filters, query, doctype="Purchase Invoice", child_doctype="Purchase Invoice Item"
	)

	if filters.get("include_payments"):
		party_account = get_party_account(
			"Supplier", filters.get("supplier"), filters.get("company"), include_advance=True
		)
		query = query.where(pi.credit_to.isin(party_account))

	invoices = query.run(as_dict=True)
	return invoices


def get_conditions(filters, query, doctype):
	parent_doc = frappe.qb.DocType(doctype)

	if filters.get("mode_of_payment"):
		query = query.where(parent_doc.mode_of_payment == filters.mode_of_payment)

	return query


def get_payments(filters):
	args = frappe._dict(
		account="credit_to",
		account_fieldname="paid_to",
		party="supplier",
		party_name="supplier_name",
		party_account=get_party_account("Supplier", filters.supplier, filters.company, include_advance=True),
	)
	payment_entries = get_payment_entries(filters, args)
	journal_entries = get_journal_entries(filters, args)
	return payment_entries + journal_entries


def get_invoice_expense_map(invoice_list):
	expense_details = frappe.db.sql(
		"""
		select parent, expense_account, sum(base_net_amount) as amount
		from `tabPurchase Invoice Item`
		where parent in (%s)
		group by parent, expense_account
	"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	invoice_expense_map = {}
	for d in expense_details:
		invoice_expense_map.setdefault(d.parent, frappe._dict()).setdefault(d.expense_account, [])
		invoice_expense_map[d.parent][d.expense_account] = flt(d.amount)

	return invoice_expense_map


def get_internal_invoice_map(invoice_list):
	unrealized_amount_details = frappe.db.sql(
		"""SELECT name, unrealized_profit_loss_account,
		base_net_total as amount from `tabPurchase Invoice` where name in (%s)
		and is_internal_supplier = 1 and company = represents_company"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	internal_invoice_map = {}
	for d in unrealized_amount_details:
		if d.unrealized_profit_loss_account:
			internal_invoice_map.setdefault((d.name, d.unrealized_profit_loss_account), d.amount)

	return internal_invoice_map


def get_invoice_tax_map(invoice_list, invoice_expense_map, expense_accounts, include_payments=False):
	tax_details = frappe.db.sql(
		"""
		select parent, account_head, case add_deduct_tax when "Add" then sum(base_tax_amount_after_discount_amount)
		else sum(base_tax_amount_after_discount_amount) * -1 end as tax_amount
		from `tabPurchase Taxes and Charges`
		where parent in (%s) and category in ('Total', 'Valuation and Total')
			and base_tax_amount_after_discount_amount != 0
		group by parent, account_head, add_deduct_tax
	"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	if include_payments:
		tax_details += get_advance_taxes_and_charges(invoice_list)

	invoice_tax_map = {}
	for d in tax_details:
		if d.account_head in expense_accounts:
			if d.account_head in invoice_expense_map[d.parent]:
				invoice_expense_map[d.parent][d.account_head] += flt(d.tax_amount)
			else:
				invoice_expense_map[d.parent][d.account_head] = flt(d.tax_amount)
		else:
			invoice_tax_map.setdefault(d.parent, frappe._dict()).setdefault(d.account_head, [])
			invoice_tax_map[d.parent][d.account_head] = flt(d.tax_amount)

	return invoice_expense_map, invoice_tax_map


def get_invoice_po_pr_map(invoice_list):
	pi_items = frappe.db.sql(
		"""
		select parent, purchase_order, purchase_receipt, po_detail, project
		from `tabPurchase Invoice Item`
		where parent in (%s)
	"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	invoice_po_pr_map = {}
	for d in pi_items:
		if d.purchase_order:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault("purchase_order", []).append(
				d.purchase_order
			)

		pr_list = None
		if d.purchase_receipt:
			pr_list = [d.purchase_receipt]
		elif d.po_detail:
			pr_list = frappe.db.sql_list(
				"""select distinct parent from `tabPurchase Receipt Item`
				where docstatus=1 and purchase_order_item=%s""",
				d.po_detail,
			)

		if pr_list:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault("purchase_receipt", pr_list)

		if d.project:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault("project", []).append(d.project)

	return invoice_po_pr_map


def get_account_details(invoice_list):
	account_map = {}
	accounts = list(set([inv.credit_to for inv in invoice_list]))
	for acc in frappe.db.sql(
		"""select name, parent_account from tabAccount
		where name in (%s)"""
		% ", ".join(["%s"] * len(accounts)),
		tuple(accounts),
		as_dict=1,
	):
		account_map[acc.name] = acc.parent_account

	return account_map
