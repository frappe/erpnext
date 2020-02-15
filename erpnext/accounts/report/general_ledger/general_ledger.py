# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.report.utils import get_currency, convert_to_presentation_currency
from frappe.utils import getdate, cstr, flt
from frappe import _, _dict
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from frappe.desk.query_report import group_report_data, hide_columns_if_filtered
from six import iteritems
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from collections import OrderedDict

def execute(filters=None):
	if not filters:
		return [], []

	account_details = {}

	if filters and filters.get('print_in_account_currency') and \
		not filters.get('account'):
		frappe.throw(_("Select an account to print in account currency"))

	for acc in frappe.db.sql("""select name, is_group from tabAccount""", as_dict=1):
		account_details.setdefault(acc.name, acc)

	if filters.get('party'):
		filters.party = frappe.parse_json(filters.get("party"))

	validate_filters(filters, account_details)

	validate_party(filters)

	filters = set_account_currency(filters)

	res = get_result(filters, account_details)

	columns = get_columns(filters)

	return columns, res


def validate_filters(filters, account_details):
	if not filters.get('company'):
		frappe.throw(_('{0} is mandatory').format(_('Company')))

	if filters.get("account") and not account_details.get(filters.account):
		frappe.throw(_("Account {0} does not exists").format(filters.account))

	if (filters.get("account") and filters.get("group_by") == _('Group by Account')
		and account_details[filters.account].is_group == 0):
		frappe.throw(_("Can not filter based on Account, if grouped by Account"))

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	if filters.get('project'):
		filters.project = frappe.parse_json(filters.get('project'))

	if filters.get('cost_center'):
		filters.cost_center = frappe.parse_json(filters.get('cost_center'))


def validate_party(filters):
	party_type, party = filters.get("party_type"), filters.get("party")

	if party:
		if not party_type:
			frappe.throw(_("To filter based on Party, select Party Type first"))
		else:
			for d in party:
				if not frappe.db.exists(party_type, d):
					frappe.throw(_("Invalid {0}: {1}").format(party_type, d))

def set_account_currency(filters):
	filters["company_currency"] = frappe.get_cached_value('Company',  filters.company,  "default_currency")
	if filters.get("account") or filters.get('party') and len(filters.party) == 1:
		account_currency = None

		if filters.get("account"):
			account_currency = get_account_currency(filters.account)
		elif filters.get("party_type") and filters.get("party"):
			gle_currency = frappe.db.get_value(
				"GL Entry", {
					"party_type": filters.party_type, "party": filters.party[0], "company": filters.company
				},
				"account_currency"
			)

			if gle_currency:
				account_currency = gle_currency
			else:
				account_currency = (None if not frappe.get_meta(filters.party_type).has_field('default_currency') else
					frappe.db.get_value(filters.party_type, filters.party[0], "default_currency"))

		filters["account_currency"] = account_currency or filters.company_currency
		if filters.account_currency != filters.company_currency and not filters.presentation_currency:
			filters.presentation_currency = filters.account_currency

	return filters

def get_result(filters, account_details):
	gl_entries = get_gl_entries(filters)

	supplier_invoice_details = get_supplier_invoice_details()

	if not filters.get('merge_similar_entries'):
		if supplier_invoice_details:
			for gle in gl_entries:
				gle['against_bill_no'] = supplier_invoice_details.get((gle.get('against_voucher_type'), gle.get('against_voucher')), '')

	if filters.get('merge_similar_entries'):
		gl_entries = merge_similar_entries(filters, gl_entries, supplier_invoice_details)

	group_by_field = get_group_by_field(filters.get('group_by'))
	group_by = [None]
	if group_by_field:
		group_by.append(group_by_field)

	result = group_report_data(gl_entries, group_by,
		calculate_totals=lambda rows, group_field, group_value, grouped_by:
			calculate_opening_closing(filters, rows, group_field, group_value, grouped_by),
		postprocess_group=lambda group_object, grouped_by: postprocess_group(filters, group_object, grouped_by)
	)

	return result

def get_gl_entries(filters):
	currency_map = get_currency(filters)
	filters.ledger_currency = currency_map.get("presentation_currency") or currency_map.get("company_currency")

	gl_entries = frappe.db.sql("""
		select
			posting_date, account, party_type, party,
			voucher_type, voucher_no, cost_center, project, account_currency,
			debit, credit, debit_in_account_currency, credit_in_account_currency,
			remarks, against, is_opening, against_voucher_type, against_voucher, reference_no, reference_date,
			%(ledger_currency)s as currency
		from `tabGL Entry`
		where company=%(company)s {conditions}
		order by posting_date, voucher_type, voucher_no, account
		""".format(conditions=get_conditions(filters)), filters, as_dict=1)

	if filters.get('presentation_currency'):
		return convert_to_presentation_currency(gl_entries, currency_map)
	else:
		return gl_entries


def merge_similar_entries(filters, gl_entries, supplier_invoice_details):
	merged_gles = OrderedDict()

	out = []
	for gle in gl_entries:
		if gle.is_opening == "Yes" or gle.posting_date < getdate(filters.from_date):
			out.append(gle)
		else:
			key = (gle.voucher_type, gle.voucher_no, gle.account, cstr(gle.party_type), cstr(gle.party), cstr(gle.cost_center),
			cstr(gle.project), cstr(gle.remarks), cstr(gle.reference_no), cstr(gle.reference_date))

			if key not in merged_gles:
				gle.update({"dr_cr": 0, "against_voucher_set": set(), "against_voucher_list": [], "against_set": set()})
				group = merged_gles[key] = gle
			else:
				group = merged_gles[key]

			group.dr_cr += flt(gle.debit) - flt(gle.credit)

			if gle.against_voucher_type and gle.against_voucher:
				group.against_voucher_set.add((cstr(gle.against_voucher_type), cstr(gle.against_voucher)))
			if gle.against:
				for acc in cstr(gle.against).strip().split(","):
					group.against_set.add(acc.strip())

	for group in merged_gles.values():
		group.debit = group.dr_cr if group.dr_cr > 0 else 0
		group.credit = -group.dr_cr if group.dr_cr < 0 else 0

		for against_voucher_type, against_voucher in group.against_voucher_set:
			bill_no = supplier_invoice_details.get((against_voucher_type, against_voucher))
			if bill_no:
				group.against_voucher_list.append(bill_no)
			else:
				group.against_voucher_list.append(against_voucher)

		group.against_voucher = ", ".join(group.against_voucher_list or [])
		group.against = ", ".join(group.against_set or [])
		out.append(group)

	return out


def get_conditions(filters):
	conditions = []
	if filters.get("account"):
		lft, rgt = frappe.db.get_value("Account", filters["account"], ["lft", "rgt"])
		conditions.append("""account in (select name from tabAccount
			where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

	if filters.get("cost_center"):
		filters.cost_center = get_cost_centers_with_children(filters.cost_center)
		conditions.append("cost_center in %(cost_center)s")

	if filters.get("voucher_no"):
		voucher_filter_method = filters.get("voucher_filter_method")
		if voucher_filter_method == "Posted Against Voucher":
			conditions.append("against_voucher=%(voucher_no)s")
		elif voucher_filter_method == "Posted By and Against Voucher":
			conditions.append("voucher_no=%(voucher_no)s or against_voucher=%(voucher_no)s")
		else:
			conditions.append("voucher_no=%(voucher_no)s")

	if filters.get("against_voucher"):
		conditions.append("against_voucher=%(against_voucher)s")

	if filters.get("reference_no"):
		conditions.append("reference_no=%(reference_no)s")

	if filters.get("group_by") == _("Group by Party") and not filters.get("party_type"):
		conditions.append("party_type in ('Customer', 'Supplier')")

	if filters.get("party_type"):
		conditions.append("party_type=%(party_type)s")

	if filters.get("party"):
		conditions.append("party in %(party)s")

	if filters.get("account") or filters.get("party") \
			or filters.get("group_by") in [_("Group by Account"), _("Group by Party")]:
		conditions.append("(posting_date <= %(to_date)s or is_opening = 'Yes')")
	else:
		conditions.append("posting_date between %(from_date)s and %(to_date)s")
		if not filters.get('show_opening_entries'):
			conditions.append("is_opening != 'Yes'")

	if filters.get("project"):
		conditions.append("project in %(project)s")

	if filters.get("sales_person"):
		lft, rgt = frappe.db.get_value("Sales Person", filters.get("sales_person"), ["lft", "rgt"])
		conditions.append("""exists(select name from `tabSales Team` steam where
			steam.sales_person in (select name from `tabSales Person` where lft >= {0} and rgt <= {1})
			and steam.parent = party and steam.parenttype = party_type)""".format(lft, rgt))

	if filters.get("finance_book"):
		if filters.get("include_default_book_entries"):
			conditions.append("finance_book in (%(finance_book)s, %(company_fb)s)")
		else:
			conditions.append("finance_book in (%(finance_book)s)")

	from frappe.desk.reportview import build_match_conditions
	match_conditions = build_match_conditions("GL Entry")

	if match_conditions:
		conditions.append(match_conditions)

	accounting_dimensions = get_accounting_dimensions()

	if accounting_dimensions:
		for dimension in accounting_dimensions:
			if filters.get(dimension):
				conditions.append("{0} in (%({0})s)".format(dimension))

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def calculate_opening_closing(filters, gl_entries, group_field, group_value, grouped_by):
	totals = get_totals_dict()

	def update_totals_for(key, gle):
		totals[key].debit += flt(gle.debit)
		totals[key].credit += flt(gle.credit)

		totals[key].debit_in_account_currency += flt(gle.debit_in_account_currency)
		totals[key].credit_in_account_currency += flt(gle.credit_in_account_currency)

	from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
	for gle in gl_entries:
		if gle.posting_date < from_date or (cstr(gle.is_opening) == "Yes" and not filters.get("show_opening_entries")):
			update_totals_for('opening', gle)
			update_totals_for('closing', gle)
			gle.to_remove = True
		elif gle.posting_date <= to_date:
			update_totals_for('total', gle)
			update_totals_for('closing', gle)

	return totals

def postprocess_group(filters, group_object, grouped_by):
	if group_object.rows:
		if 'party' in grouped_by:
			if group_object.rows[0].party_type == "Customer":
				customer = frappe.get_cached_doc("Customer", grouped_by['party'])
				group_object.sales_person = ", ".join(set([d.sales_person for d in customer.sales_team]))

		group_object.rows = list(filter(lambda d: not d.get("to_remove"), group_object.rows))

		if 'voucher_no' not in grouped_by:
			group_object.rows.insert(0, group_object.totals.opening)

		# group_object.rows.append(group_object.totals.total)

		if 'voucher_no' not in grouped_by:
			group_object.rows.append(group_object.totals.closing)

		balance, balance_in_account_currency = 0, 0

		for d in group_object.rows:
			if not d.posting_date:
				balance = 0

			balance = get_balance(d, balance, 'debit', 'credit')
			d['balance'] = balance

			d['account_currency'] = filters.account_currency
			d['currency'] = filters.presentation_currency or filters.company_currency

		group_object.totals.opening.debit = 0
		group_object.totals.opening.credit = 0
		group_object.totals.closing.debit = group_object.totals.total.debit
		group_object.totals.closing.credit = group_object.totals.total.credit

	# Do not show totals as they have already been added as rows
	del group_object['totals']

def get_balance(row, balance, debit_field, credit_field):
	balance += (row.get(debit_field, 0) - row.get(credit_field, 0))
	return balance

def get_totals_dict():
	def _get_debit_credit_dict(label):
		return _dict(
			account="'{0}'".format(label),
			debit=0.0,
			credit=0.0,
			debit_in_account_currency=0.0,
			credit_in_account_currency=0.0,
			_isGroupTotal=True,
			_bold=True
		)
	return _dict(
		opening=_get_debit_credit_dict(_('Opening')),
		total=_get_debit_credit_dict(_('Total')),
		closing=_get_debit_credit_dict(_('Closing')),
		_isGroupTotal=True
	)

def get_group_by_field(group_by):
	if group_by == _('Group by Party'):
		return 'party_type', 'party'
	elif group_by == _('Group by Account'):
		return 'account'
	elif group_by == _('Group by Voucher'):
		return 'voucher_type', 'voucher_no'
	else:
		return None

def get_supplier_invoice_details():
	inv_details = {}
	for voucher_type in ['Purchase Invoice', 'Journal Entry']:
		for d in frappe.db.sql("""select name, bill_no from `tab{0}`
				where docstatus = 1 and bill_no is not null and bill_no != ''""".format(voucher_type), as_dict=1):
			inv_details[(voucher_type, d.name)] = d.bill_no

	return inv_details

def get_columns(filters):
	columns = [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 80
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 120
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 150
		},
		{
			"label": _("Ref No"),
			"fieldname": "reference_no",
			"width": 80
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 150,
			"hide_if_filtered": 1
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"width": 100,
			"hide_if_filtered": 1
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"width": 150,
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"hide_if_filtered": 1
		},
		{
			"label": _("Remarks"),
			"fieldname": "remarks",
			"width": 200
		},
		{
			"label": _("Debit ({0})".format(filters.ledger_currency)),
			"fieldname": "debit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100
		},
		{
			"label": _("Credit ({0})".format(filters.ledger_currency)),
			"fieldname": "credit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100
		},
		{
			"label": _("Balance ({0})".format(filters.ledger_currency)),
			"fieldname": "balance",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Against Account"),
			"fieldname": "against",
			"width": 120
		},
		{
			"label": _("Against Voucher Type"),
			"fieldname": "against_voucher_type",
			"width": 120,
			"hide_if_merge_similar": 1
		},
		{
			"label": _("Against Voucher"),
			"fieldname": "against_voucher",
			"fieldtype": "Dynamic Link",
			"options": "against_voucher_type",
			"width": 150
		},
		{
			"label": _("Cost Center"),
			"options": "Cost Center",
			"fieldname": "cost_center",
			"width": 100,
			"hide_if_filtered": 1
		},
		{
			"label": _("Project"),
			"options": "Project",
			"fieldname": "project",
			"width": 100,
			"hide_if_filtered": 1
		},
		{
			"label": _("Ref Date"),
			"fieldname": "reference_date",
			"fieldtype": "Date",
			"width": 90
		},
		{
			"label": _("Against Bill No"),
			"fieldname": "against_bill_no",
			"fieldtype": "Data",
			"width": 100,
			"hide_if_merge_similar": 1
		},
	]

	if filters.get('merge_similar_entries'):
		columns = [col for col in columns if not col.get('hide_if_merge_similar')]

	return columns
