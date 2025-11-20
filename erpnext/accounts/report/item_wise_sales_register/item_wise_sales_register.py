# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder import functions as fn
from frappe.utils import cstr, flt
from frappe.utils.nestedset import get_descendants_of
from frappe.utils.xlsxutils import handle_html

from erpnext.accounts.report.sales_register.sales_register import get_mode_of_payments
from erpnext.accounts.report.utils import get_values_for_columns
from erpnext.selling.report.item_wise_sales_history.item_wise_sales_history import (
	get_customer_details,
)


def execute(filters=None):
	return _execute(filters)


def _execute(filters=None, additional_table_columns=None, additional_conditions=None):
	if not filters:
		filters = {}
	columns = get_columns(additional_table_columns, filters)

	company_currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")

	item_list = get_items(filters, additional_table_columns, additional_conditions)
	if not item_list:
		return columns, [], None, None, None, 0

	itemised_tax, tax_columns = get_tax_accounts(item_list, columns, company_currency)
	scrubbed_tax_fields = {}

	for tax in tax_columns:
		scrubbed_tax_fields.update(
			{
				tax + " Rate": frappe.scrub(tax + " Rate"),
				tax + " Amount": frappe.scrub(tax + " Amount"),
			}
		)

	mode_of_payments = get_mode_of_payments(set(d.parent for d in item_list))
	so_dn_map = get_delivery_notes_against_sales_order(item_list)

	data = []
	total_row_map = {}
	skip_total_row = 0
	prev_group_by_value = ""

	if filters.get("group_by"):
		grand_total = get_grand_total(filters, "Sales Invoice")

	customer_details = get_customer_details()

	for d in item_list:
		customer_record = customer_details.get(d.customer)

		delivery_note = None
		if d.delivery_note:
			delivery_note = d.delivery_note
		elif d.so_detail:
			delivery_note = ", ".join(so_dn_map.get(d.so_detail, []))

		if not delivery_note and d.update_stock:
			delivery_note = d.parent

		row = {
			"item_code": d.item_code,
			"item_name": d.si_item_name if d.si_item_name else d.i_item_name,
			"item_group": d.si_item_group if d.si_item_group else d.i_item_group,
			"description": d.description,
			"invoice": d.parent,
			"posting_date": d.posting_date,
			"customer": d.customer,
			"customer_name": customer_record.customer_name,
			"customer_group": customer_record.customer_group,
			**get_values_for_columns(additional_table_columns, d),
			"debit_to": d.debit_to,
			"mode_of_payment": ", ".join(mode_of_payments.get(d.parent, [])),
			"territory": d.territory,
			"project": d.project,
			"company": d.company,
			"sales_order": d.sales_order,
			"delivery_note": d.delivery_note,
			"income_account": get_income_account(d),
			"cost_center": d.cost_center,
			"stock_qty": d.stock_qty,
			"stock_uom": d.stock_uom,
		}

		if d.stock_uom != d.uom and d.stock_qty:
			row.update({"rate": (d.base_net_rate * d.qty) / d.stock_qty, "amount": d.base_net_amount})
		else:
			row.update({"rate": d.base_net_rate, "amount": d.base_net_amount})

		total_tax = 0
		total_other_charges = 0
		for tax, details in itemised_tax.get(d.name, {}).items():
			row.update(
				{
					scrubbed_tax_fields[tax + " Rate"]: details.get("tax_rate", 0),
					scrubbed_tax_fields[tax + " Amount"]: details.get("tax_amount", 0),
				}
			)
			if details.get("is_other_charges"):
				total_other_charges += flt(details.get("tax_amount"))
			else:
				total_tax += flt(details.get("tax_amount"))

		row.update(
			{
				"total_tax": total_tax,
				"total_other_charges": total_other_charges,
				"total": d.base_net_amount + total_tax,
				"currency": company_currency,
			}
		)

		if filters.get("group_by"):
			row.update({"percent_gt": flt(row["total"] / grand_total) * 100})
			group_by_field, subtotal_display_field = get_group_by_and_display_fields(filters)
			data, prev_group_by_value = add_total_row(
				data,
				filters,
				prev_group_by_value,
				d,
				total_row_map,
				group_by_field,
				subtotal_display_field,
				grand_total,
				tax_columns,
			)
			add_sub_total_row(row, total_row_map, d.get(group_by_field, ""), tax_columns)

		data.append(row)

	if filters.get("group_by") and item_list:
		total_row = total_row_map.get(prev_group_by_value or d.get("item_name"))
		total_row["percent_gt"] = flt(total_row["total"] / grand_total * 100)
		data.append(total_row)
		data.append({})
		add_sub_total_row(total_row, total_row_map, "total_row", tax_columns)
		data.append(total_row_map.get("total_row"))
		skip_total_row = 1

	return columns, data, None, None, None, skip_total_row


def get_income_account(row):
	if row.enable_deferred_revenue:
		return row.deferred_revenue_account
	elif row.is_internal_customer == 1:
		return row.unrealized_profit_loss_account
	else:
		return row.income_account


def get_columns(additional_table_columns, filters):
	columns = []

	if filters.get("group_by") != ("Item"):
		columns.extend(
			[
				{
					"label": _("Item Code"),
					"fieldname": "item_code",
					"fieldtype": "Link",
					"options": "Item",
					"width": 120,
				},
				{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 120},
			]
		)

	if filters.get("group_by") not in ("Item", "Item Group"):
		columns.extend(
			[
				{
					"label": _("Item Group"),
					"fieldname": "item_group",
					"fieldtype": "Link",
					"options": "Item Group",
					"width": 120,
				}
			]
		)

	columns.extend(
		[
			{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 150},
			{
				"label": _("Invoice"),
				"fieldname": "invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 150,
			},
			{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		]
	)

	if filters.get("group_by") != "Customer":
		columns.extend(
			[
				{
					"label": _("Customer Group"),
					"fieldname": "customer_group",
					"fieldtype": "Link",
					"options": "Customer Group",
					"width": 120,
				}
			]
		)

	if filters.get("group_by") not in ("Customer", "Customer Group"):
		columns.extend(
			[
				{
					"label": _("Customer"),
					"fieldname": "customer",
					"fieldtype": "Link",
					"options": "Customer",
					"width": 120,
				},
				{
					"label": _("Customer Name"),
					"fieldname": "customer_name",
					"fieldtype": "Data",
					"width": 120,
				},
			]
		)

	if additional_table_columns:
		columns += additional_table_columns

	columns += [
		{
			"label": _("Receivable Account"),
			"fieldname": "debit_to",
			"fieldtype": "Link",
			"options": "Account",
			"width": 80,
		},
		{
			"label": _("Mode Of Payment"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Data",
			"width": 120,
		},
	]

	if filters.get("group_by") != "Territory":
		columns.extend(
			[
				{
					"label": _("Territory"),
					"fieldname": "territory",
					"fieldtype": "Link",
					"options": "Territory",
					"width": 80,
				}
			]
		)

	columns += [
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 80,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 80,
		},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 100,
		},
		{
			"label": _("Delivery Note"),
			"fieldname": "delivery_note",
			"fieldtype": "Link",
			"options": "Delivery Note",
			"width": 100,
		},
		{
			"label": _("Income Account"),
			"fieldname": "income_account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 100,
		},
		{
			"label": _("Cost Center"),
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 100,
		},
		{"label": _("Stock Qty"), "fieldname": "stock_qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Float",
			"options": "currency",
			"width": 100,
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
	]

	if filters.get("group_by"):
		columns.append(
			{"label": _("% Of Grand Total"), "fieldname": "percent_gt", "fieldtype": "Float", "width": 80}
		)

	return columns


def apply_conditions(query, si, sii, sip, filters, additional_conditions=None):
	for opts in ("company", "customer"):
		if filters.get(opts):
			query = query.where(si[opts] == filters[opts])

	if filters.get("from_date"):
		query = query.where(si.posting_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(si.posting_date <= filters.get("to_date"))

	if filters.get("mode_of_payment"):
		subquery = (
			frappe.qb.from_(sip)
			.select(sip.parent)
			.where(sip.mode_of_payment == filters.get("mode_of_payment"))
			.groupby(sip.parent)
		)
		query = query.where(si.name.isin(subquery))

	if filters.get("warehouse"):
		if frappe.db.get_value("Warehouse", filters.get("warehouse"), "is_group"):
			lft, rgt = frappe.db.get_all(
				"Warehouse", filters={"name": filters.get("warehouse")}, fields=["lft", "rgt"], as_list=True
			)[0]
			warehouses = frappe.db.get_all("Warehouse", {"lft": (">", lft), "rgt": ("<", rgt)}, pluck="name")
			query = query.where(sii.warehouse.isin(warehouses))
		else:
			query = query.where(sii.warehouse == filters.get("warehouse"))

	if filters.get("brand"):
		query = query.where(sii.brand == filters.get("brand"))

	if filters.get("item_code"):
		query = query.where(sii.item_code == filters.get("item_code"))

	if filters.get("item_group"):
		if frappe.db.get_value("Item Group", filters.get("item_group"), "is_group"):
			item_groups = get_descendants_of("Item Group", filters.get("item_group"))
			item_groups.append(filters.get("item_group"))
			query = query.where(sii.item_group.isin(item_groups))
		else:
			query = query.where(sii.item_group == filters.get("item_group"))

	if filters.get("income_account"):
		query = query.where(
			(sii.income_account == filters.get("income_account"))
			| (sii.deferred_revenue_account == filters.get("income_account"))
			| (si.unrealized_profit_loss_account == filters.get("income_account"))
		)

	for key, value in (additional_conditions or {}).items():
		query = query.where(si[key] == value)

	return query


def apply_order_by_conditions(doctype, query, filters):
	invoice = f"`tab{doctype}`"
	invoice_item = f"`tab{doctype} Item`"

	if not filters.get("group_by"):
		query += f" order by {invoice}.posting_date desc, {invoice_item}.item_group desc"
	elif filters.get("group_by") == "Invoice":
		query += f" order by {invoice_item}.parent desc"
	elif filters.get("group_by") == "Item":
		query += f" order by {invoice_item}.item_code"
	elif filters.get("group_by") == "Item Group":
		query += f" order by {invoice_item}.item_group"
	elif filters.get("group_by") in ("Customer", "Customer Group", "Territory", "Supplier"):
		filter_field = frappe.scrub(filters.get("group_by"))
		query += f" order by {filter_field} desc"

	return query


def get_items(filters, additional_query_columns, additional_conditions=None):
	doctype = "Sales Invoice"
	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	sip = frappe.qb.DocType("Sales Invoice Payment")
	item = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(si)
		.join(sii)
		.on(si.name == sii.parent)
		.left_join(item)
		.on(sii.item_code == item.name)
		.select(
			sii.name,
			sii.parent,
			si.posting_date,
			si.debit_to,
			si.unrealized_profit_loss_account,
			si.is_internal_customer,
			si.customer,
			si.remarks,
			fn.IfNull(si.territory, "Not Specified").as_("territory"),
			si.company,
			si.base_net_total,
			sii.project,
			sii.item_code,
			sii.description,
			sii.item_name,
			sii.item_group,
			sii.item_name.as_("si_item_name"),
			sii.item_group.as_("si_item_group"),
			item.item_name.as_("i_item_name"),
			item.item_group.as_("i_item_group"),
			sii.sales_order,
			sii.delivery_note,
			sii.income_account,
			sii.cost_center,
			sii.enable_deferred_revenue,
			sii.deferred_revenue_account,
			sii.stock_qty,
			sii.stock_uom,
			sii.base_net_rate,
			sii.base_net_amount,
			si.customer_name,
			fn.IfNull(si.customer_group, "Not Specified").as_("customer_group"),
			sii.so_detail,
			si.update_stock,
			sii.uom,
			sii.qty,
		)
		.where(si.docstatus == 1)
		.where(sii.parenttype == doctype)
	)

	if additional_query_columns:
		for column in additional_query_columns:
			if column.get("_doctype"):
				table = frappe.qb.DocType(column.get("_doctype"))
				query = query.select(table[column.get("fieldname")])
			else:
				query = query.select(si[column.get("fieldname")])

	if filters.get("customer"):
		query = query.where(si.customer == filters["customer"])

	if filters.get("customer_group"):
		query = query.where(si.customer_group == filters["customer_group"])

	query = apply_conditions(query, si, sii, sip, filters, additional_conditions)

	from frappe.desk.reportview import build_match_conditions

	query, params = query.walk()
	match_conditions = build_match_conditions(doctype)

	if match_conditions:
		query += " and " + match_conditions

	query = apply_order_by_conditions(doctype, query, filters)

	return frappe.db.sql(query, params, as_dict=True)


def get_delivery_notes_against_sales_order(item_list):
	so_dn_map = frappe._dict()
	so_item_rows = list(set([d.so_detail for d in item_list]))

	if so_item_rows:
		dn_item = frappe.qb.DocType("Delivery Note Item")
		delivery_notes = (
			frappe.qb.from_(dn_item)
			.select(dn_item.parent, dn_item.so_detail)
			.where(dn_item.docstatus == 1)
			.where(dn_item.so_detail.isin(so_item_rows))
			.groupby(dn_item.so_detail, dn_item.parent)
			.run(as_dict=True)
		)

		for dn in delivery_notes:
			so_dn_map.setdefault(dn.so_detail, []).append(dn.parent)

	return so_dn_map


def get_grand_total(filters, doctype):
	return flt(
		frappe.db.get_value(
			doctype,
			{
				"docstatus": 1,
				"posting_date": ("between", [filters.get("from_date"), filters.get("to_date")]),
			},
			[{"SUM": "base_grand_total"}],
		)
	)


def get_tax_accounts(
	item_list,
	columns,
	company_currency,
	doctype="Sales Invoice",
	tax_doctype="Sales Taxes and Charges",
):
	invoice_item_row = [d.name for d in item_list]
	tax = frappe.qb.DocType("Item Wise Tax Detail")
	taxes_and_charges = frappe.qb.DocType(tax_doctype)
	account = frappe.qb.DocType("Account")

	query = (
		get_tax_details_query(
			doctype,
			tax_doctype,
		)
		.left_join(account)
		.on(taxes_and_charges.account_head == account.name)
		.select(account.account_type)
		.where(tax.item_row.isin(invoice_item_row))
	)

	if doctype == "Purchase Invoice":
		query = query.where(
			(taxes_and_charges.category.isin(["Total", "Valuation and Total"]))
			& (taxes_and_charges.base_tax_amount_after_discount_amount != 0)
		)

	tax_details = query.run(as_dict=True)

	precision = frappe.get_precision(tax_doctype, "tax_amount", currency=company_currency) or 2
	tax_columns = set()
	itemised_tax = {}

	for row in tax_details:
		description = handle_html(row.description) or row.account_head
		rate = "NA" if row.rate == 0 else row.rate
		tax_columns.add(description)
		itemised_tax.setdefault(row.item_row, {}).setdefault(
			description,
			frappe._dict(
				{
					"tax_rate": rate,
					"tax_amount": 0,
					"is_other_charges": 0 if row.account_type == "Tax" else 1,
				}
			),
		)

		itemised_tax[row.item_row][description].tax_amount += flt(row.amount, precision)

	tax_columns = sorted(tax_columns)
	for desc in tax_columns:
		columns.append(
			{
				"label": _(desc + " Rate"),
				"fieldname": frappe.scrub(desc + " Rate"),
				"fieldtype": "Float",
				"width": 100,
			}
		)

		columns.append(
			{
				"label": _(desc + " Amount"),
				"fieldname": frappe.scrub(desc + " Amount"),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100,
			}
		)

	columns += [
		{
			"label": _("Total Tax"),
			"fieldname": "total_tax",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"label": _("Total Other Charges"),
			"fieldname": "total_other_charges",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Currency",
			"width": 80,
			"hidden": 1,
		},
	]

	return itemised_tax, tax_columns


def get_tax_details_query(doctype, tax_doctype):
	tax = frappe.qb.DocType("Item Wise Tax Detail")
	taxes_and_charges = frappe.qb.DocType(tax_doctype)

	query = (
		frappe.qb.from_(tax)
		.left_join(taxes_and_charges)
		.on(tax.tax_row == taxes_and_charges.name)
		.select(
			tax.parent,
			tax.item_row,
			tax.rate,
			tax.amount,
			tax.taxable_amount,
			taxes_and_charges.charge_type,
			taxes_and_charges.account_head,
			taxes_and_charges.description,
		)
		.where(tax.parenttype == doctype)
	)

	return query


def add_total_row(
	data,
	filters,
	prev_group_by_value,
	item,
	total_row_map,
	group_by_field,
	subtotal_display_field,
	grand_total,
	tax_columns,
):
	if prev_group_by_value != item.get(group_by_field, ""):
		if prev_group_by_value:
			total_row = total_row_map.get(prev_group_by_value)
			data.append(total_row)
			data.append({})
			add_sub_total_row(total_row, total_row_map, "total_row", tax_columns)

		prev_group_by_value = item.get(group_by_field, "")

		total_row_map.setdefault(
			item.get(group_by_field, ""),
			{
				subtotal_display_field: get_display_value(filters, group_by_field, item),
				"stock_qty": 0.0,
				"amount": 0.0,
				"bold": 1,
				"total_tax": 0.0,
				"total": 0.0,
				"percent_gt": 0.0,
			},
		)

		total_row_map.setdefault(
			"total_row",
			{
				subtotal_display_field: "Total",
				"stock_qty": 0.0,
				"amount": 0.0,
				"bold": 1,
				"total_tax": 0.0,
				"total": 0.0,
				"percent_gt": 0.0,
			},
		)

	return data, prev_group_by_value


def get_display_value(filters, group_by_field, item):
	if filters.get("group_by") == "Item":
		if item.get("item_code") != item.get("item_name"):
			value = f"{item.get('item_code')}: {item.get('item_name')}"
		else:
			value = item.get("item_code", "")
	elif filters.get("group_by") in ("Customer", "Supplier"):
		party = frappe.scrub(filters.get("group_by"))
		if item.get(party) != item.get(party + "_name"):
			value = f"{item.get(party)}: {item.get(party + '_name')}"
		else:
			value = item.get(party)
	else:
		value = item.get(group_by_field)

	return value


def get_group_by_and_display_fields(filters):
	if filters.get("group_by") == "Item":
		group_by_field = "item_code"
		subtotal_display_field = "invoice"
	elif filters.get("group_by") == "Invoice":
		group_by_field = "parent"
		subtotal_display_field = "item_code"
	else:
		group_by_field = frappe.scrub(filters.get("group_by"))
		subtotal_display_field = "item_code"

	return group_by_field, subtotal_display_field


def add_sub_total_row(item, total_row_map, group_by_value, tax_columns):
	total_row = total_row_map.get(group_by_value)
	total_row["stock_qty"] += item["stock_qty"]
	total_row["amount"] += item["amount"]
	total_row["total_tax"] += item["total_tax"]
	total_row["total"] += item["total"]
	total_row["percent_gt"] += item["percent_gt"]

	for tax in tax_columns:
		total_row.setdefault(frappe.scrub(tax + " Amount"), 0.0)
		total_row[frappe.scrub(tax + " Amount")] += flt(item[frappe.scrub(tax + " Amount")])
