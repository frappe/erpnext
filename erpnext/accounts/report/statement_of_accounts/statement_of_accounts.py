# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, cstr
from frappe import _
from erpnext.accounts.utils import get_account_currency
from datetime import datetime

# from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
from erpnext.accounts.report.statement_of_accounts_receivable.statement_of_accounts_receivable import StatementOfAccountsReceivable


def execute(filters=None):
    account_details = {}
    for acc in frappe.db.sql("""select name, is_group from tabAccount""", as_dict=1):
        account_details.setdefault(acc.name, acc)

    validate_filters(filters, account_details)

    validate_party(filters)

    filters = set_account_currency(filters)

    columns = get_columns(filters)

    res = get_result(filters, account_details)

    args = {
        "party_type": "Customer",
        "naming_by": ["Selling Settings", "cust_master_name"],
    }
    # columns, data, None, chart
    column2, res2, x, y = StatementOfAccountsReceivable(filters).run(args)

    for x in res2:
        count = 0
        for y in range(0, 15):  # 16 + 1, 1 for break
            # x.append("")
            if count == 0:
                x.insert(0, "br")
            else:
                x.insert(0, "")
            count += 1
            # pass

    for x in res:
        for y in range(0, 17):
            x.append("")
    columns_combine = columns + ["**BREAK**"] + column2
    columns_combine += ["**CUSTOMER INFO**"]  # CUSTOMER INFO
    customer_columns = [
        _("#Customer Name") + ":Data",
        _("#Customer Address") + ":Short Text",
        _("#Date") + ":Data",
        _("#Currency") + ":Data",
        _("#Credit Days Based On") + ":Data",
        _("#Tax ID") + ":Data"
    ]
    columns_combine += customer_columns

    # customer_doc = frappe.get_doc("Customer",filters.get("party"))

    customer_data = []
    customer_row = []

    for x in range(0, 30):
        customer_row.append("")

    customer_sql = frappe.db.sql("""SELECT * FROM `tabCustomer` WHERE customer_name=%s LIMIT 1""",
                                 filters.get("party"),as_dict=True)
    print "CUSTOMER SQL"
    print customer_sql

    # customer_row.append(frappe.utils.nowdate())  # #DATE
    #dt = frappe.utils.nowdate()
    dt = datetime.strptime(frappe.utils.nowdate(), '%Y-%m-%d').strftime('%d-%m-%Y')
    # print '{0}/{1}/{2:02}'.format(dt.month, dt.day, dt.year % 100)
    #customer_row.append(dt)

    if customer_sql:

        customer_row.append("br")
        # get_dynamic_link_for_address = frappe.db.sql("SELECT parent FROM `tabDynamic Link` where link_name =  ")
        if customer_sql[0].customer_primary_address:
            address_doc = frappe.get_doc("Address", customer_sql[0].customer_primary_address)

        customer_row.append(filters.get("party"))  # #Customer Name
        # customer_row.append(customer_doc.address)

        customer_full_address = ""

        if customer_sql[0].customer_primary_address and address_doc.address_line1:
            customer_full_address += address_doc.address_line1 + "<br>"

        if customer_sql[0].customer_primary_address and address_doc.address_line2:
            customer_full_address += address_doc.address_line2 + "<br>"

        if customer_sql[0].customer_primary_address and not address_doc.city:
            address_doc.city = " "

        if customer_sql[0].customer_primary_address and not address_doc.country:
            address_doc.country = " "

        if customer_sql[0].customer_primary_address and not address_doc.phone:
            address_doc.phone = " "

        if customer_sql[0].customer_primary_address and not address_doc.fax:
            address_doc.fax = " "
        if customer_sql[0].customer_primary_address:
            customer_row.append(customer_full_address +
                                address_doc.city + "<br>" + address_doc.country + "<br>" + "Phone: " + address_doc.phone +
                                "<br>" + "Fax: " + address_doc.fax)
        else:
            customer_row.append("")
        customer_row.append(dt)  # #DATE

        # customer_row.append(filters.get("currency")) # #CURRENCY
        customer_row.append(frappe.db.get_value("Customer", filters.party, "default_currency"))

        if filters.get("party"):
            customer_doc = frappe.get_doc("Customer",filters.party)

            if customer_doc.credits_based_on == "Fixed Days":
                customer_row.append(str(customer_doc.credit_days) + " Days" if customer_doc.credit_days else "")
                customer_row.append(customer_doc.tax_id)
            else:
                customer_row.append(customer_doc.credits_based_on)
                customer_row.append(customer_doc.tax_id)

        else:
            customer_row.append("")

        customer_data.append(customer_row)  # ADD ROW TO BE RETURNED
    else:
        print("BEEEEEEEEEEEEEEEEEEEEEEEEEEEE")
        if filters.get("party"):
            customer_row.append("br")

            customer_row.append(filters.get("party"))  # #Customer Name

            # customer_row.append(filters.get("currency")) # #CURRENCY

            print("MAO LAGEEEEH")
            if filters.get("party"):
                customer_doc = frappe.get_doc("Customer" if filters.get("party_type") == "Customer" else "Supplier", filters.party)
                if customer_doc.primary_address:
                    address_doc = frappe.get_doc("Address", customer_doc.primary_address)
                customer_full_address = ""

                if customer_doc.primary_address and address_doc.address_line1:
                    customer_full_address += address_doc.address_line1 + "<br>"

                if customer_doc.primary_address and address_doc.address_line2:
                    customer_full_address += address_doc.address_line2 + "<br>"

                if customer_doc.primary_address and not address_doc.city:
                    address_doc.city = " "

                if customer_doc.primary_address and not address_doc.country:
                    address_doc.country = " "

                if customer_doc.primary_address and not address_doc.phone:
                    address_doc.phone = " "

                if customer_doc.primary_address and not address_doc.fax:
                    address_doc.fax = " "
                if customer_doc.primary_address:
                    customer_row.append(customer_full_address +
                                        address_doc.city + "<br>" + address_doc.country + "<br>" + "Phone: " + address_doc.phone +
                                        "<br>" + "Fax: " + address_doc.fax)
                elif not customer_doc.primary_address:
                    customer_row.append("")
                customer_row.append(dt)
                customer_row.append(frappe.db.get_value("Customer", filters.party, "default_currency"))
                if customer_doc.credits_based_on == "Fixed Days":
                    customer_row.append(str(customer_doc.credit_days) + " Days" if customer_doc.credit_days else "")
                    customer_row.append(customer_doc.tax_id)
                else:
                    customer_row.append(customer_doc.credits_based_on)
                    customer_row.append(customer_doc.tax_id)

            else:
                customer_row.append(dt)
                customer_row.append(frappe.db.get_value("Customer", filters.party, "default_currency"))
                customer_row.append("")

            customer_data.append(customer_row)  # ADD ROW TO BE RETURNED

    data_combine = res + res2 + customer_data
    # column_details = [
    #     {"label": "0-30**", 'width': 120, "fieldname": "30", "fieldtype": "float"},
    # ]
    # test = []
    #data_combine.append({'30': 259541.68})
    print("WHAAAAAAAAAAAAAAAAAT")
    return columns_combine, data_combine


def validate_filters(filters, account_details):
    if not filters.get('company'):
        frappe.throw(_('{0} is mandatory').format(_('Company')))

    if filters.get("account") and not account_details.get(filters.account):
        frappe.throw(_("Account {0} does not exists").format(filters.account))

    if filters.get("account") and filters.get("group_by_account") \
            and account_details[filters.account].is_group == 0:
        frappe.throw(_("Can not filter based on Account, if grouped by Account"))

    if filters.get("voucher_no") and filters.get("group_by_voucher"):
        frappe.throw(_("Can not filter based on Voucher No, if grouped by Voucher"))

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
                                                            "party": filters.party, "company": filters.company},
                                               "account_currency")
            if gle_currency:
                account_currency = gle_currency
            else:
                account_currency = frappe.db.get_value(filters.party_type, filters.party, "default_currency")

        filters["account_currency"] = account_currency or filters.company_currency

        if filters.account_currency != filters.company_currency:
            filters["show_in_account_currency"] = 1

        return filters


def get_columns(filters):
    columns = [
        _("Posting Date") + ":Date:90",
        _("Account") + ":Link/Account:200",
        _("Debit") + ":Float:100",
        _("Credit") + ":Float:100"
    ]
    #columns = []

    print "GET COLUMNS"
    print filters

    """if filters.get("show_in_account_currency"):
        columns += [
            _("Debit") + ":Float:100",
            _("Credit") + ":Float:100"
        ]"""

    columns += [
        _("Voucher Type") + "::120", _("Voucher No") + ":Dynamic Link/" + _("Voucher Type") + ":160",
        _("Against Account") + "::120", _("Party Type") + "::80", _("Party") + "::150",
        _("Project") + ":Link/Project:100", _("Cost Center") + ":Link/Cost Center:100",
        _("Against Voucher Type") + "::120",
        _("Against Voucher") + ":Dynamic Link/" + _("Against Voucher Type") + ":160",
        _("Remarks") + "::400"
    ]

    return columns


def get_result(filters, account_details):
    gl_entries = get_gl_entries(filters)

    data = get_data_with_opening_closing(filters, account_details, gl_entries)

    result = get_result_as_list(data, filters)

    return result


def get_gl_entries(filters):
    select_fields = """sum(debit_in_account_currency) as debit_in_account_currency,
    	sum(credit_in_account_currency) as credit_in_account_currency""" \
        if filters.get("show_in_account_currency") else """sum(debit) as debit, sum(credit) as credit"""

    group_by_condition = "group by voucher_type, voucher_no, account, cost_center" \
        if filters.get("group_by_voucher") else "group by name"

    gl_entries = frappe.db.sql("""
    	select
    		posting_date, account, party_type, party,
    		{select_fields},
    		voucher_type, voucher_no, cost_center, project,
    		against_voucher_type, against_voucher,
    		remarks, against, is_opening
    	from `tabGL Entry`
    	where company=%(company)s {conditions}
    	{group_by_condition}
    	order by posting_date, account""" \
                               .format(select_fields=select_fields, conditions=get_conditions(filters),
                                       group_by_condition=group_by_condition), filters, as_dict=1)

    return gl_entries


def get_conditions(filters):
    conditions = []
    if filters.get("account"):
        lft, rgt = frappe.db.get_value("Account", filters["account"], ["lft", "rgt"])
        conditions.append("""account in (select name from tabAccount
			where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

    if filters.get("voucher_no"):
        conditions.append("voucher_no=%(voucher_no)s")

    if filters.get("party_type"):
        conditions.append("party_type=%(party_type)s")

    if filters.get("party"):
        conditions.append("party=%(party)s")

    if not (filters.get("account") or filters.get("party") or filters.get("group_by_account")):
        conditions.append("posting_date >=%(from_date)s")

    from frappe.desk.reportview import build_match_conditions
    match_conditions = build_match_conditions("GL Entry")
    if match_conditions: conditions.append(match_conditions)

    return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_data_with_opening_closing(filters, account_details, gl_entries):
    data = []
    gle_map = initialize_gle_map(gl_entries)

    opening, total_debit, total_credit, opening_in_account_currency, total_debit_in_account_currency, \
    total_credit_in_account_currency, gle_map = get_accountwise_gle(filters, gl_entries, gle_map)

    # Opening for filtered account
    if filters.get("account") or filters.get("party"):
        data += [get_balance_row(_("Opening"), opening, opening_in_account_currency), {}]

    if filters.get("group_by_account"):
        for acc, acc_dict in gle_map.items():
            if acc_dict.entries:
                # Opening for individual ledger, if grouped by account
                data.append(get_balance_row(_("Opening"), acc_dict.opening,
                                            acc_dict.opening_in_account_currency))

                data += acc_dict.entries

                # Totals and closing for individual ledger, if grouped by account
                account_closing = acc_dict.opening + acc_dict.total_debit - acc_dict.total_credit
                account_closing_in_account_currency = acc_dict.opening_in_account_currency \
                                                      + acc_dict.total_debit_in_account_currency - acc_dict.total_credit_in_account_currency

                data += [{"account": "'" + _("Totals") + "'", "debit": acc_dict.total_debit,
                          "credit": acc_dict.total_credit},
                         get_balance_row(_("Closing (Opening + Totals)"),
                                         account_closing, account_closing_in_account_currency), {}]

    else:
        for gl in gl_entries:
            if gl.posting_date >= getdate(filters.from_date) and gl.posting_date <= getdate(filters.to_date) \
                    and gl.is_opening == "No":
                data.append(gl)

    # Total debit and credit between from and to date
    if total_debit or total_credit:
        data.append({
            "account": "'" + _("Totals") + "'",
            "debit": total_debit,
            "credit": total_credit,
            "debit_in_account_currency": total_debit_in_account_currency,
            "credit_in_account_currency": total_credit_in_account_currency
        })

    # Closing for filtered account
    if filters.get("account") or filters.get("party"):
        closing = opening + total_debit - total_credit
        closing_in_account_currency = opening_in_account_currency + \
                                      total_debit_in_account_currency - total_credit_in_account_currency

        data.append(get_balance_row(_("Closing (Opening + Totals)"),
                                    closing, closing_in_account_currency))

    return data


def initialize_gle_map(gl_entries):
    gle_map = frappe._dict()
    for gle in gl_entries:
        gle_map.setdefault(gle.account, frappe._dict({
            "opening": 0,
            "opening_in_account_currency": 0,
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
    opening, total_debit, total_credit = 0, 0, 0
    opening_in_account_currency, total_debit_in_account_currency, total_credit_in_account_currency = 0, 0, 0

    from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
    for gle in gl_entries:
        amount = flt(gle.debit, 3) - flt(gle.credit, 3)
        amount_in_account_currency = flt(gle.debit_in_account_currency, 3) - flt(gle.credit_in_account_currency, 3)

        if (filters.get("account") or filters.get("party") or filters.get("group_by_account")) \
                and (gle.posting_date < from_date or cstr(gle.is_opening) == "Yes"):

            gle_map[gle.account].opening += amount
            if filters.get("show_in_account_currency"):
                gle_map[gle.account].opening_in_account_currency += amount_in_account_currency

            if filters.get("account") or filters.get("party"):
                opening += amount
                if filters.get("show_in_account_currency"):
                    opening_in_account_currency += amount_in_account_currency

        elif gle.posting_date <= to_date:
            gle_map[gle.account].entries.append(gle)
            gle_map[gle.account].total_debit += flt(gle.debit, 3)
            gle_map[gle.account].total_credit += flt(gle.credit, 3)

            total_debit += flt(gle.debit, 3)
            total_credit += flt(gle.credit, 3)

            if filters.get("show_in_account_currency"):
                gle_map[gle.account].total_debit_in_account_currency += flt(gle.debit_in_account_currency, 3)
                gle_map[gle.account].total_credit_in_account_currency += flt(gle.credit_in_account_currency, 3)

                total_debit_in_account_currency += flt(gle.debit_in_account_currency, 3)
                total_credit_in_account_currency += flt(gle.credit_in_account_currency, 3)

    return opening, total_debit, total_credit, opening_in_account_currency, \
           total_debit_in_account_currency, total_credit_in_account_currency, gle_map


def get_balance_row(label, balance, balance_in_account_currency=None):
    balance_row = {
        "account": "'" + label + "'",
        "debit": balance if balance > 0 else 0,
        "credit": -1 * balance if balance < 0 else 0
    }

    if balance_in_account_currency != None:
        balance_row.update({
            "debit_in_account_currency": balance_in_account_currency if balance_in_account_currency > 0 else 0,
            "credit_in_account_currency": -1 * balance_in_account_currency if balance_in_account_currency < 0 else 0
        })

    return balance_row


def get_result_as_list(data, filters):
    result = []
    for d in data:
        row = [d.get("posting_date"), d.get("account")
               # , d.get("debit"), d.get("credit")
               ]

        if filters.get("show_in_account_currency"):
            row += [d.get("debit_in_account_currency"), d.get("credit_in_account_currency")]
        else:
            row += [d.get("debit"), d.get("credit")]

        row += [d.get("voucher_type"), d.get("voucher_no"), d.get("against"),
                d.get("party_type"), d.get("party"), d.get("project"), d.get("cost_center"),
                d.get("against_voucher_type"), d.get("against_voucher"), d.get("remarks")
                ]

        result.append(row)

    return result
