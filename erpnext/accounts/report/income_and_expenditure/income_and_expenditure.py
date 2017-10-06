# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from erpnext.accounts.utils import get_account_currency


def execute(filters=None):
    account_details = {}
    for acc in frappe.db.sql("""select name, is_group from tabAccount""", as_dict=1):
        account_details.setdefault(acc.name, acc)

    validate_filters(filters, account_details)

    validate_party(filters)

    filters = set_account_currency(filters)

    columns = get_columns(filters)

    res = get_result(filters, account_details)

    return columns, res


def validate_filters(filters, account_details):
    if not filters.get('company'):
        frappe.throw(_('{0} is mandatory').format(_('Company')))

    if filters.get("account") and not account_details.get(filters.account):
        frappe.throw(_("Account {0} does not exists").format(filters.account))

    if filters.get("account") and filters.get("group_by_account") \
            and account_details[filters.account].is_group == 0:
        frappe.throw(_("Can not filter based on Account, if grouped by Account"))

    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date must be before To Date"))


def validate_party(filters):
    party_type, party = filters.get("party_type"), filters.get("party")

    if party:
        if not party_type:
            frappe.throw(_("To filter based on Party, select Party Type first"))
        elif not frappe.db.exists(party_type, party):
            frappe.throw(_("Invalid {0}: {1}").format(party_type, party))

def set_account_currency(filters):
    if not (filters.get("account") or filters.get("party")):
        return filters
    else:
        filters["company_currency"] = frappe.db.get_value("Company", filters.company, "default_currency")
        account_currency = None

        if filters.get("account"):
            account_currency = get_account_currency(filters.account)
        elif filters.get("party"):
            gle_currency = frappe.db.get_value("GL Entry", {"party_type": filters.party_type,
                "party": filters.party, "company": filters.company}, "account_currency")
            if gle_currency:
                account_currency = gle_currency
            else:
                account_currency = None if filters.party_type == "Employee" else \
                    frappe.db.get_value(filters.party_type, filters.party, "default_currency")

        filters["account_currency"] = account_currency or filters.company_currency

        if filters.account_currency != filters.company_currency:
            filters["show_in_account_currency"] = 1

        return filters

def get_columns(filters):
    columns = [
        _("Posting Date") + ":Date:90", _("Account") + ":Link/Account:160",
        _("Debit") + ":Float:100", _("Credit") + ":Float:100", _("Balance") + ":Float:100"
    ]

    if filters.get("show_in_account_currency"):
        columns += [
            _("Debit") + " (" + filters.account_currency + ")" + ":Float:100",
            _("Credit") + " (" + filters.account_currency + ")" + ":Float:100",
            _("Balance") + " (" + filters.account_currency + ")" + ":Float:100"
        ]

    columns += [
        _("Remarks") + "::220", _("Voucher No") + ":Dynamic Link/"+_("Voucher Type")+":160",
        _("Against Account") + "::120"
    ]

    return columns


def get_result(filters, account_details):
    gl_entries = get_gl_entries(filters)

    data = get_data_with_opening_closing(filters, account_details, gl_entries)

    result = get_result_as_list(data, filters)

    return result


def get_gl_entries(filters):
    select_fields = """, sum(debit_in_account_currency) as debit_in_account_currency,
        sum(credit_in_account_currency) as credit_in_account_currency""" \
        if filters.get("show_in_account_currency") else ""

    group_by_condition = "group by name"

    gl_entries = frappe.db.sql("""
        select
            posting_date, account, party_type, party,
            sum(debit) as debit, sum(credit) as credit,
            voucher_type, voucher_no, cost_center, project,
            against_voucher_type, against_voucher,
            remarks, against, is_opening {select_fields}
        from `tabGL Entry`
        where company=%(company)s {conditions}
        {group_by_condition}
        order by posting_date, account"""\
        .format(select_fields=select_fields, conditions=get_conditions(filters),
            group_by_condition=group_by_condition), filters, as_dict=1)

    return gl_entries

def get_conditions(filters):
    conditions = []
    if filters.get("account"):
        conditions.append("""account=%(account)s""")
    else:
        # filter accounts whose type is Bank or Cash
        conditions.append("""account in (select name from tabAccount
            where account_type='Bank' or account_type='Cash')""")

    from frappe.desk.reportview import build_match_conditions
    match_conditions = build_match_conditions("GL Entry")
    if match_conditions: conditions.append(match_conditions)

    return "and {}".format(" and ".join(conditions)) if conditions else ""

def get_data_with_opening_closing(filters, account_details, gl_entries):
    data = []
    gle_map = initialize_gle_map(gl_entries)

    opening_credit, opening_debit, total_debit, total_credit, opening_debit_in_account_currency, opening_credit_in_account_currency, total_debit_in_account_currency, \
        total_credit_in_account_currency, gle_map = get_accountwise_gle(filters, gl_entries, gle_map)

    for acc, acc_dict in gle_map.items():
        if acc_dict.entries:
            # Opening for individual ledger, if grouped by account
            data.append(get_balance_row(_("Opening"), acc_dict.opening_credit, acc_dict.opening_debit,
                    acc_dict.opening_credit_in_account_currency, acc_dict.opening_debit_in_account_currency))

            data += acc_dict.entries

            # Totals and closing for individual ledger, if grouped by account
            account_closing_credit = acc_dict.opening_credit + acc_dict.total_credit
            account_closing_debit = acc_dict.opening_debit + acc_dict.total_debit

            account_closing_credit_in_account_currency = acc_dict.opening_credit_in_account_currency + acc_dict.total_credit_in_account_currency
            account_closing_debit_in_account_currency = acc_dict.opening_debit_in_account_currency + acc_dict.total_debit_in_account_currency

            data += [get_balance_row(_("Closing (Opening + Totals)"),
                        account_closing_credit, account_closing_debit, account_closing_credit_in_account_currency,
                                    account_closing_debit_in_account_currency), {}]

    # Total debit and credit between from and to date
    if total_debit or total_credit:
        data.append({
            "account": "'" + _("Totals") + "'",
            "debit": total_debit,
            "credit": total_credit,
            "balance": total_debit - total_credit,
            "debit_in_account_currency": total_debit_in_account_currency,
            "credit_in_account_currency": total_credit_in_account_currency
        })

    return data

def initialize_gle_map(gl_entries):
    gle_map = frappe._dict()
    for gle in gl_entries:
        gle_map.setdefault(gle.account, frappe._dict({
            "opening_credit": 0,
            "opening_debit": 0,
            "opening_credit_in_account_currency": 0,
            "opening_debit_in_account_currency": 0,
            "entries": [],
            "total_debit": 0,
            "total_debit_in_account_currency": 0,
            "total_credit": 0,
            "total_credit_in_account_currency": 0,
            "closing": 0,
            "closing_in_account_currency": 0
        }))
    return gle_map

def get_accountwise_gle(filters, gl_entries, gle_map):
    opening_credit, opening_debit, total_debit, total_credit = 0, 0, 0, 0
    opening_credit_in_account_currency, opening_debit_in_account_currency, total_debit_in_account_currency, total_credit_in_account_currency = 0, 0, 0, 0

    from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
    for gle in gl_entries:

        if gle.posting_date < from_date or cstr(gle.is_opening) == "Yes":

            gle_map[gle.account].opening_debit += flt(gle.debit, 3)
            gle_map[gle.account].opening_credit += flt(gle.credit, 3)
            if filters.get("show_in_account_currency"):
                gle_map[gle.account].opening_credit_in_account_currency += flt(gle.credit_in_account_currency, 3)
                gle_map[gle.account].opening_debit_in_account_currency += flt(gle.debit_in_account_currency, 3)

            if filters.get("account"):
                opening_credit += flt(gle.credit, 3)
                opening_debit += flt(gle.debit, 3)
                if filters.get("show_in_account_currency"):
                    opening_credit_in_account_currency += flt(gle.credit_in_account_currency, 3)
                    opening_debit_in_account_currency += flt(gle.debit_in_account_currency, 3)

        elif gle.posting_date <= to_date:
            gle_map[gle.account].total_debit += flt(gle.debit, 3)
            gle_map[gle.account].total_credit += flt(gle.credit, 3)

            # calculates current balance of the account
            balance = (gle_map[gle.account].total_debit + gle_map[gle.account].opening_debit) - (gle_map[gle.account].total_credit + gle_map[gle.account].opening_credit)
            balance_in_account_currency = (gle_map[gle.account].total_debit_in_account_currency + gle_map[gle.account].opening_debit_in_account_currency) \
                                          - (gle_map[gle.account].total_credit_in_account_currency + gle_map[gle.account].opening_credit_in_account_currency)

            gle.update({"balance": balance, "balance_in_account_currency": balance_in_account_currency})
            gle_map[gle.account].entries.append(gle)

            total_debit += flt(gle.debit, 3)
            total_credit += flt(gle.credit, 3)

            if filters.get("show_in_account_currency"):
                gle_map[gle.account].total_debit_in_account_currency += flt(gle.debit_in_account_currency, 3)
                gle_map[gle.account].total_credit_in_account_currency += flt(gle.credit_in_account_currency, 3)

                total_debit_in_account_currency += flt(gle.debit_in_account_currency, 3)
                total_credit_in_account_currency += flt(gle.credit_in_account_currency, 3)

    return opening_debit, opening_credit, total_debit, total_credit, opening_debit_in_account_currency, \
           opening_credit_in_account_currency, total_debit_in_account_currency, total_credit_in_account_currency, gle_map


def get_balance_row(label, credit, debit, credit_in_account_currency=None, debit_in_account_currency=None):
    balance_row = {
        "account": "'" + label + "'",
        "debit": debit,
        "credit": credit,
        "balance": debit - credit
    }

    if credit_in_account_currency and debit_in_account_currency:
        balance_row.update({
            "debit_in_account_currency": debit_in_account_currency,
            "credit_in_account_currency": credit_in_account_currency,
            "balance_in_account_currency": debit_in_account_currency - credit_in_account_currency
        })

    return balance_row


def get_result_as_list(data, filters):
    result = []
    for d in data:
        row = [d.get("posting_date"), d.get("account"), d.get("debit"), d.get("credit"), d.get("balance")]

        if filters.get("show_in_account_currency"):
            row += [d.get("debit_in_account_currency"), d.get("credit_in_account_currency"), d.get("balance_in_account_currency")]

        row += [d.get("remarks"), d.get("voucher_no"), d.get("against")]

        result.append(row)

    return result



