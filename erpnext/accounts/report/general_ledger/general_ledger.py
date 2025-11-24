# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, _dict
from frappe.query_builder import Criterion
from frappe.utils import cstr, getdate

from erpnext import get_company_currency, get_default_company
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency
from erpnext.accounts.utils import get_account_currency

DEBIT_CREDIT_DICT = {
	"debit": 0.0,
	"credit": 0.0,
	"debit_in_account_currency": 0.0,
	"credit_in_account_currency": 0.0,
	"debit_in_transaction_currency": None,
	"credit_in_transaction_currency": None,
}


def execute(filters=None):
	if not filters:
		return [], []

	account_details = {}

	if filters and filters.get("print_in_account_currency") and not filters.get("account"):
		frappe.throw(_("Select an account to print in account currency"))

	for acc in frappe.db.sql("""select name, is_group from tabAccount""", as_dict=1):
		account_details.setdefault(acc.name, acc)

	if filters.get("party"):
		filters.party = frappe.parse_json(filters.get("party"))

	validate_filters(filters, account_details)

	validate_party(filters)

	filters = set_account_currency(filters)

	columns = get_columns(filters)

	res = get_result(filters, account_details)

	return columns, res


def validate_filters(filters, account_details):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	if not filters.get("from_date") and not filters.get("to_date"):
		frappe.throw(
			_("{0} and {1} are mandatory").format(frappe.bold(_("From Date")), frappe.bold(_("To Date")))
		)

	if filters.get("account"):
		filters.account = frappe.parse_json(filters.get("account"))
		for account in filters.account:
			if not account_details.get(account):
				frappe.throw(_("Account {0} does not exists").format(account))

	if not filters.get("categorize_by") and filters.get("group_by"):
		filters["categorize_by"] = filters["group_by"]
		filters["categorize_by"] = filters["categorize_by"].replace("Group by", "Categorize by")

	if filters.get("account") and filters.get("categorize_by") == "Categorize by Account":
		filters.account = frappe.parse_json(filters.get("account"))
		for account in filters.account:
			if account_details[account].is_group == 0:
				frappe.throw(_("Can not filter based on Child Account, if grouped by Account"))

	if filters.get("voucher_no") and filters.get("categorize_by") in ["Categorize by Voucher"]:
		frappe.throw(_("Can not filter based on Voucher No, if grouped by Voucher"))

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	if filters.get("project"):
		filters.project = frappe.parse_json(filters.get("project"))

	if filters.get("cost_center"):
		filters.cost_center = frappe.parse_json(filters.get("cost_center"))


def validate_party(filters):
	party_type, party = filters.get("party_type"), filters.get("party")

	if party and party_type:
		for d in party:
			if not frappe.db.exists(party_type, d):
				frappe.throw(_("Invalid {0}: {1}").format(party_type, d))


def set_account_currency(filters):
	if filters.get("account") or (filters.get("party") and len(filters.party) == 1):
		filters["company_currency"] = frappe.get_cached_value("Company", filters.company, "default_currency")
		account_currency = None

		if filters.get("account"):
			if len(filters.get("account")) == 1:
				account_currency = get_account_currency(filters.account[0])
			else:
				currency = get_account_currency(filters.account[0])
				is_same_account_currency = True
				for account in filters.get("account"):
					if get_account_currency(account) != currency:
						is_same_account_currency = False
						break

				if is_same_account_currency:
					account_currency = currency

		elif filters.get("party") and filters.get("party_type"):
			gle_currency = frappe.db.get_value(
				"GL Entry",
				{"party_type": filters.party_type, "party": filters.party[0], "company": filters.company},
				"account_currency",
			)

			if gle_currency:
				account_currency = gle_currency
			else:
				account_currency = (
					None
					if filters.party_type in ["Employee", "Shareholder", "Member"]
					else frappe.get_cached_value(filters.party_type, filters.party[0], "default_currency")
				)

		filters["account_currency"] = account_currency or filters.company_currency
		if filters.account_currency != filters.company_currency and not filters.presentation_currency:
			filters.presentation_currency = filters.account_currency

	return filters


def get_result(filters, account_details):
	accounting_dimensions = []
	if filters.get("include_dimensions"):
		accounting_dimensions = get_accounting_dimensions()

	gl_entries = get_gl_entries(filters, accounting_dimensions)

	data = get_data_with_opening_closing(filters, account_details, accounting_dimensions, gl_entries)

	result = get_result_as_list(data, filters)

	return result


def get_gl_entries(filters, accounting_dimensions):
	currency_map = get_currency(filters)
	select_fields = """, debit, credit, debit_in_account_currency,
		credit_in_account_currency """

	if filters.get("show_remarks"):
		if remarks_length := frappe.get_single_value("Accounts Settings", "general_ledger_remarks_length"):
			select_fields += f",substr(remarks, 1, {remarks_length}) as 'remarks'"
		else:
			select_fields += """,remarks"""

	order_by_statement = "order by posting_date, account, creation"

	if filters.get("include_dimensions"):
		order_by_statement = "order by posting_date, creation"

	if filters.get("categorize_by") == "Categorize by Voucher":
		order_by_statement = "order by posting_date, voucher_type, voucher_no"
	if filters.get("categorize_by") == "Categorize by Account":
		order_by_statement = "order by account, posting_date, creation"

	if filters.get("include_default_book_entries"):
		filters["company_fb"] = frappe.get_cached_value(
			"Company", filters.get("company"), "default_finance_book"
		)

	dimension_fields = ""
	if accounting_dimensions:
		dimension_fields = ", ".join(accounting_dimensions) + ","

	transaction_currency_fields = ""
	if filters.get("add_values_in_transaction_currency"):
		transaction_currency_fields = (
			"debit_in_transaction_currency, credit_in_transaction_currency, transaction_currency,"
		)

	gl_entries = frappe.db.sql(
		f"""
		select
			name as gl_entry, posting_date, account, party_type, party,
			voucher_type, voucher_subtype, voucher_no, {dimension_fields}
			cost_center, project, {transaction_currency_fields}
			against_voucher_type, against_voucher, account_currency,
			against, is_opening, creation {select_fields}
		from `tabGL Entry`
		where company=%(company)s {get_conditions(filters)}
		{order_by_statement}
	""",
		filters,
		as_dict=1,
	)

	party_name_map = get_party_name_map()

	for gl_entry in gl_entries:
		if gl_entry.party_type and gl_entry.party:
			gl_entry.party_name = party_name_map.get(gl_entry.party_type, {}).get(gl_entry.party)

	if filters.get("presentation_currency"):
		return convert_to_presentation_currency(gl_entries, currency_map, filters)
	else:
		return gl_entries


def get_conditions(filters):
	conditions = []

	ignore_is_opening = frappe.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting")

	if filters.get("account"):
		filters.account = get_accounts_with_children(filters.account)
		if filters.account:
			conditions.append("account in %(account)s")

	if filters.get("cost_center"):
		filters.cost_center = get_cost_centers_with_children(filters.cost_center)
		conditions.append("cost_center in %(cost_center)s")

	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")

	if filters.get("against_voucher_no"):
		conditions.append("against_voucher=%(against_voucher_no)s")

	if filters.get("ignore_err"):
		err_journals = frappe.db.get_all(
			"Journal Entry",
			filters={
				"company": filters.get("company"),
				"docstatus": 1,
				"voucher_type": ("in", ["Exchange Rate Revaluation", "Exchange Gain Or Loss"]),
			},
			as_list=True,
		)
		if err_journals:
			filters.update({"voucher_no_not_in": [x[0] for x in err_journals]})

	if filters.get("ignore_cr_dr_notes"):
		system_generated_cr_dr_journals = frappe.db.get_all(
			"Journal Entry",
			filters={
				"company": filters.get("company"),
				"docstatus": 1,
				"voucher_type": ("in", ["Credit Note", "Debit Note"]),
				"is_system_generated": 1,
			},
			as_list=True,
		)
		if system_generated_cr_dr_journals:
			vouchers_to_ignore = (filters.get("voucher_no_not_in") or []) + [
				x[0] for x in system_generated_cr_dr_journals
			]
			filters.update({"voucher_no_not_in": vouchers_to_ignore})

	if filters.get("voucher_no_not_in"):
		conditions.append("voucher_no not in %(voucher_no_not_in)s")

	if filters.get("categorize_by") == "Categorize by Party" and not filters.get("party_type"):
		conditions.append("party_type in ('Customer', 'Supplier')")

	if filters.get("party_type"):
		conditions.append("party_type=%(party_type)s")

	if filters.get("party"):
		conditions.append("party in %(party)s")

	if not (
		filters.get("account")
		or filters.get("party")
		or filters.get("categorize_by") in ["Categorize by Account", "Categorize by Party"]
	):
		if not ignore_is_opening:
			conditions.append("(posting_date >=%(from_date)s or is_opening = 'Yes')")
		else:
			conditions.append("posting_date >=%(from_date)s")

	if not ignore_is_opening:
		conditions.append("(posting_date <=%(to_date)s or is_opening = 'Yes')")
	else:
		conditions.append("posting_date <=%(to_date)s")

	if filters.get("project"):
		conditions.append("project in %(project)s")

	if filters.get("include_default_book_entries"):
		if filters.get("finance_book"):
			if filters.get("company_fb") and cstr(filters.get("finance_book")) != cstr(
				filters.get("company_fb")
			):
				frappe.throw(
					_("To use a different finance book, please uncheck 'Include Default FB Entries'")
				)
			else:
				conditions.append("(finance_book in (%(finance_book)s, '') OR finance_book IS NULL)")
		else:
			conditions.append("(finance_book in (%(company_fb)s, '') OR finance_book IS NULL)")
	else:
		if filters.get("finance_book"):
			conditions.append("(finance_book in (%(finance_book)s, '') OR finance_book IS NULL)")
		else:
			conditions.append("(finance_book in ('') OR finance_book IS NULL)")

	if not filters.get("show_cancelled_entries"):
		conditions.append("is_cancelled = 0")

	from frappe.desk.reportview import build_match_conditions

	match_conditions = build_match_conditions("GL Entry")

	if match_conditions:
		conditions.append(match_conditions)

	accounting_dimensions = get_accounting_dimensions(as_list=False)

	if accounting_dimensions:
		for dimension in accounting_dimensions:
			# Ignore 'Finance Book' set up as dimension in below logic, as it is already handled in above section
			if not dimension.disabled and dimension.document_type != "Finance Book":
				if filters.get(dimension.fieldname):
					if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
						filters[dimension.fieldname] = get_dimension_with_children(
							dimension.document_type, filters.get(dimension.fieldname)
						)
						conditions.append(f"{dimension.fieldname} in %({dimension.fieldname})s")
					else:
						conditions.append(f"{dimension.fieldname} in %({dimension.fieldname})s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_party_name_map():
	party_map = {}

	customers = frappe.get_all("Customer", fields=["name", "customer_name"])
	party_map["Customer"] = {c.name: c.customer_name for c in customers}

	suppliers = frappe.get_all("Supplier", fields=["name", "supplier_name"])
	party_map["Supplier"] = {s.name: s.supplier_name for s in suppliers}

	employees = frappe.get_all("Employee", fields=["name", "employee_name"])
	party_map["Employee"] = {e.name: e.employee_name for e in employees}
	return party_map


def get_accounts_with_children(accounts):
	if not isinstance(accounts, list):
		accounts = [d.strip() for d in accounts.strip().split(",") if d]

	if not accounts:
		return

	doctype = frappe.qb.DocType("Account")
	accounts_data = (
		frappe.qb.from_(doctype)
		.select(doctype.lft, doctype.rgt)
		.where(doctype.name.isin(accounts))
		.run(as_dict=True)
	)

	conditions = []
	for account in accounts_data:
		conditions.append((doctype.lft >= account.lft) & (doctype.rgt <= account.rgt))

	return frappe.qb.from_(doctype).select(doctype.name).where(Criterion.any(conditions)).run(pluck=True)


def set_bill_no(gl_entries):
	inv_details = get_supplier_invoice_details()
	for gl in gl_entries:
		gl["bill_no"] = inv_details.get(gl.get("against_voucher"), "")


def get_translated_labels_for_totals():
	def wrap_in_quotes(label):
		return f"'{label}'"

	return {
		"opening": wrap_in_quotes(_("Opening")),
		"total": wrap_in_quotes(_("Total")),
		"closing": wrap_in_quotes(_("Closing (Opening + Total)")),
	}


def get_data_with_opening_closing(filters, account_details, accounting_dimensions, gl_entries):
	def add_total_to_data(totals, key):
		row = totals[key]
		row["account"] = labels[key]
		data.append(row)

	labels = get_translated_labels_for_totals()

	data = []

	set_bill_no(gl_entries)

	gle_map = initialize_gle_map(gl_entries, filters)

	totals, entries = get_accountwise_gle(filters, accounting_dimensions, gl_entries, gle_map)

	# Opening for filtered account
	add_total_to_data(totals, "opening")

	if filters.get("categorize_by") != "Categorize by Voucher (Consolidated)":
		set_opening_closing = (not filters.get("categorize_by") and not filters.get("voucher_no")) or (
			filters.get("categorize_by") and filters.get("categorize_by") != "Categorize by Voucher"
		)
		set_total = filters.get("categorize_by") or not filters.voucher_no

		for acc_dict in gle_map.values():
			if not acc_dict.entries:
				continue

			# opening
			data.append({"debit_in_transaction_currency": None, "credit_in_transaction_currency": None})
			if set_opening_closing:
				add_total_to_data(acc_dict.totals, "opening")

			data += acc_dict.entries

			# totals
			if set_total:
				add_total_to_data(acc_dict.totals, "total")

			# closing
			if set_opening_closing:
				add_total_to_data(acc_dict.totals, "closing")

		data.append({"debit_in_transaction_currency": None, "credit_in_transaction_currency": None})
	else:
		data += entries

	# totals
	add_total_to_data(totals, "total")

	# closing
	add_total_to_data(totals, "closing")

	return data


def get_totals_dict():
	return _dict(
		opening=_dict(DEBIT_CREDIT_DICT),
		total=_dict(DEBIT_CREDIT_DICT),
		closing=_dict(DEBIT_CREDIT_DICT),
	)


def get_group_by_field(group_by):
	if group_by == "Categorize by Party":
		return "party"
	elif group_by in ["Categorize by Voucher (Consolidated)", "Categorize by Account"]:
		return "account"
	else:
		return "voucher_no"


def initialize_gle_map(gl_entries, filters):
	gle_map = {}
	group_by = get_group_by_field(filters.get("categorize_by"))

	for gle in gl_entries:
		group_by_value = gle.get(group_by)
		if group_by_value not in gle_map:
			gle_map[group_by_value] = _dict(
				totals=get_totals_dict(),
				entries=[],
			)

	return gle_map


def get_accountwise_gle(filters, accounting_dimensions, gl_entries, gle_map):
	entries = []
	consolidated_gle = {}
	group_by = get_group_by_field(filters.get("categorize_by"))
	group_by_voucher_consolidated = filters.get("categorize_by") == "Categorize by Voucher (Consolidated)"

	if filters.get("show_net_values_in_party_account"):
		account_type_map = get_account_type_map(filters.get("company"))

	immutable_ledger = frappe.get_single_value("Accounts Settings", "enable_immutable_ledger")

	def update_value_in_dict(data, key, gle):
		data[key].debit += gle.debit
		data[key].credit += gle.credit

		data[key].debit_in_account_currency += gle.debit_in_account_currency
		data[key].credit_in_account_currency += gle.credit_in_account_currency

		if filters.get("add_values_in_transaction_currency") and key not in ["opening", "closing", "total"]:
			data[key].debit_in_transaction_currency += gle.debit_in_transaction_currency
			data[key].credit_in_transaction_currency += gle.credit_in_transaction_currency

		if filters.get("show_net_values_in_party_account") and account_type_map.get(data[key].account) in (
			"Receivable",
			"Payable",
		):
			net_value = data[key].debit - data[key].credit
			net_value_in_account_currency = (
				data[key].debit_in_account_currency - data[key].credit_in_account_currency
			)

			if net_value < 0:
				dr_or_cr = "credit"
				rev_dr_or_cr = "debit"
			else:
				dr_or_cr = "debit"
				rev_dr_or_cr = "credit"

			data[key][dr_or_cr] = abs(net_value)
			data[key][dr_or_cr + "_in_account_currency"] = abs(net_value_in_account_currency)
			data[key][rev_dr_or_cr] = 0
			data[key][rev_dr_or_cr + "_in_account_currency"] = 0

		if data[key].against_voucher and gle.against_voucher:
			data[key].against_voucher += ", " + gle.against_voucher

	from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
	show_opening_entries = filters.get("show_opening_entries")

	totals = get_totals_dict()
	for gle in gl_entries:
		group_by_value = gle.get(group_by)
		gle.voucher_subtype = _(gle.voucher_subtype)
		gle.against_voucher_type = _(gle.against_voucher_type)
		gle.remarks = _(gle.remarks)
		gle.party_type = _(gle.party_type)

		if gle.posting_date < from_date or (cstr(gle.is_opening) == "Yes" and not show_opening_entries):
			if not group_by_voucher_consolidated:
				update_value_in_dict(gle_map[group_by_value].totals, "opening", gle)
				update_value_in_dict(gle_map[group_by_value].totals, "closing", gle)

			update_value_in_dict(totals, "opening", gle)
			update_value_in_dict(totals, "closing", gle)

		elif gle.posting_date <= to_date or (cstr(gle.is_opening) == "Yes" and show_opening_entries):
			if not group_by_voucher_consolidated:
				update_value_in_dict(gle_map[group_by_value].totals, "total", gle)
				update_value_in_dict(gle_map[group_by_value].totals, "closing", gle)
				update_value_in_dict(totals, "total", gle)
				update_value_in_dict(totals, "closing", gle)

				gle_map[group_by_value].entries.append(gle)

			elif group_by_voucher_consolidated:
				keylist = [
					gle.get("posting_date"),
					gle.get("voucher_type"),
					gle.get("voucher_no"),
					gle.get("account"),
					gle.get("party_type"),
					gle.get("party"),
				]

				if immutable_ledger:
					keylist.append(gle.get("creation"))

				if filters.get("include_dimensions"):
					for dim in accounting_dimensions:
						keylist.append(gle.get(dim))
					keylist.append(gle.get("cost_center"))
					keylist.append(gle.get("project"))

				key = tuple(keylist)
				if key not in consolidated_gle:
					consolidated_gle.setdefault(key, gle)
				else:
					update_value_in_dict(consolidated_gle, key, gle)

		if filters.get("include_dimensions"):
			dimensions = [*accounting_dimensions, "cost_center", "project"]

			for dimension in dimensions:
				if val := gle.get(dimension):
					gle[dimension] = _(val)

	for value in consolidated_gle.values():
		update_value_in_dict(totals, "total", value)
		update_value_in_dict(totals, "closing", value)
		entries.append(value)

	return totals, entries


def get_account_type_map(company):
	account_type_map = frappe._dict(
		frappe.get_all("Account", fields=["name", "account_type"], filters={"company": company}, as_list=1)
	)

	return account_type_map


def get_result_as_list(data, filters):
	balance = 0

	for d in data:
		if not d.get("posting_date"):
			balance = 0

		balance = get_balance(d, balance, "debit", "credit")

		d["balance"] = balance

		d["account_currency"] = filters.account_currency

		d["presentation_currency"] = filters.presentation_currency

	return data


def get_supplier_invoice_details():
	inv_details = {}
	for d in frappe.db.sql(
		""" select name, bill_no from `tabPurchase Invoice`
		where docstatus = 1 and bill_no is not null and bill_no != '' """,
		as_dict=1,
	):
		inv_details[d.name] = d.bill_no

	return inv_details


def get_balance(row, balance, debit_field, credit_field):
	balance += row.get(debit_field, 0) - row.get(credit_field, 0)

	return balance


def get_columns(filters):
	if filters.get("presentation_currency"):
		currency = filters["presentation_currency"]
	else:
		company = filters.get("company") or get_default_company()
		filters["presentation_currency"] = currency = get_company_currency(company)

	company_currency = get_company_currency(filters.get("company") or get_default_company())

	if (
		filters.get("show_amount_in_company_currency")
		and filters["presentation_currency"] != company_currency
	):
		frappe.throw(
			_(
				f'Presentation Currency cannot be {frappe.bold(filters["presentation_currency"])} , When {frappe.bold("Show Credit / Debit in Company Currency")} is enabled.'
			)
		)

	columns = [
		{
			"label": _("GL Entry"),
			"fieldname": "gl_entry",
			"fieldtype": "Link",
			"options": "GL Entry",
			"hidden": 1,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 180,
		},
		{
			"label": _("Debit ({0})").format(currency),
			"fieldname": "debit",
			"fieldtype": "Currency",
			"options": "presentation_currency",
			"width": 130,
		},
		{
			"label": _("Credit ({0})").format(currency),
			"fieldname": "credit",
			"fieldtype": "Currency",
			"options": "presentation_currency",
			"width": 130,
		},
		{
			"label": _("Balance ({0})").format(currency),
			"fieldname": "balance",
			"fieldtype": "Currency",
			"options": "presentation_currency",
			"width": 130,
		},
	]

	if filters.get("add_values_in_transaction_currency"):
		columns += [
			{
				"label": _("Debit (Transaction)"),
				"fieldname": "debit_in_transaction_currency",
				"fieldtype": "Currency",
				"width": 130,
				"options": "transaction_currency",
			},
			{
				"label": _("Credit (Transaction)"),
				"fieldname": "credit_in_transaction_currency",
				"fieldtype": "Currency",
				"width": 130,
				"options": "transaction_currency",
			},
			{
				"label": "Transaction Currency",
				"fieldname": "transaction_currency",
				"fieldtype": "Link",
				"options": "Currency",
				"width": 70,
			},
		]

	columns += [
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 120},
		{
			"label": _("Voucher Subtype"),
			"fieldname": "voucher_subtype",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 180,
		},
		{"label": _("Against Account"), "fieldname": "against", "width": 120},
		{"label": _("Party Type"), "fieldname": "party_type", "width": 100},
		{"label": _("Party"), "fieldname": "party", "width": 100},
	]

	supplier_master_name = frappe.db.get_single_value("Buying Settings", "supp_master_name")
	customer_master_name = frappe.db.get_single_value("Selling Settings", "cust_master_name")

	if supplier_master_name != "Supplier Name" or customer_master_name != "Customer Name":
		columns.append(
			{
				"label": _("Party Name"),
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 150,
			}
		)

	if filters.get("include_dimensions"):
		columns.append({"label": _("Project"), "options": "Project", "fieldname": "project", "width": 100})

		for dim in get_accounting_dimensions(as_list=False):
			columns.append(
				{"label": _(dim.label), "options": dim.label, "fieldname": dim.fieldname, "width": 100}
			)
		columns.append(
			{"label": _("Cost Center"), "options": "Cost Center", "fieldname": "cost_center", "width": 100}
		)

	columns.extend(
		[
			{"label": _("Against Voucher Type"), "fieldname": "against_voucher_type", "width": 100},
			{
				"label": _("Against Voucher"),
				"fieldname": "against_voucher",
				"fieldtype": "Dynamic Link",
				"options": "against_voucher_type",
				"width": 100,
			},
			{"label": _("Supplier Invoice No"), "fieldname": "bill_no", "fieldtype": "Data", "width": 100},
		]
	)

	if filters.get("show_remarks"):
		columns.extend([{"label": _("Remarks"), "fieldname": "remarks", "width": 400}])

	return columns
