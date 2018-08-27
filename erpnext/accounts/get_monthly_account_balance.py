# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import frappe


@frappe.whitelist(allow_guest=True)
def get_monthly_account_balance():
    # 'account',
    try:
        data = frappe.form_dict

        account = data.get('account')
        company = data.get('company')
        from_date = data.get('from_date')
        end_time = data.get('end_time')
        frappe.set_user("Administrator")
        
        account_info = get_balance(account, dict(
            from_date=from_date,
            to_date=to_date,
            company=company,
            show_zero_values=1
        ))
      
    except Exception as e:
        return dict(status=False, message=str(e))
    return dict(status=True, message="Success", account_info=account_info[0])

value_fields = ("opening_debit", "opening_credit", "debit", "credit", "closing_debit", "closing_credit")
  
  
def get_balance(account, filters):
    accounts = frappe.db.sql("""select name, company, parent_account, account_name, root_type, report_type, lft, rgt
		from `tabAccount` where name= %s and company = %s order by lft""", (account, filters.get("company")), as_dict=True)
    
    if len(accounts) == 0:
      frappe.throw("There is no such account")
      
    company_currency = erpnext.get_company_currency(company)

    accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

    min_lft, max_rgt = frappe.db.sql("""select min(lft), max(rgt) from `tabAccount`
		where company=%s""", (filters.get("company"),))[0]

    gl_entries_by_account = {}

    set_gl_entries_by_account(filters.get("company"), filters.get("from_date"),
                              filters.get("to_date"), min_lft, max_rgt, filters, gl_entries_by_account,
                              ignore_closing_entries=False)

    opening_balances = get_opening_balances(filters)

    total_row = calculate_values(accounts, gl_entries_by_account, opening_balances, filters, company_currency)
    accumulate_values_into_parents(accounts, accounts_by_name)

    data = prepare_data(accounts, filters, total_row, parent_children_map, company_currency)
    data = filter_out_zero_value_rows(data, parent_children_map,
                                      show_zero_values=filters.get("show_zero_values", False))

    return data


def get_opening_balances(filters):
    balance_sheet_opening = get_rootwise_opening_balances(filters, "Balance Sheet")
    pl_opening = get_rootwise_opening_balances(filters, "Profit and Loss")

    balance_sheet_opening.update(pl_opening)
    return balance_sheet_opening


def get_rootwise_opening_balances(filters, report_type):
    additional_conditions = ""
    if not filters.get("show_unclosed_fy_pl_balances", 0):
        additional_conditions = " and posting_date >= %(year_start_date)s" \
            if report_type == "Profit and Loss" else ""

    if not flt(filters.get("with_period_closing_entry", 0)):
        additional_conditions += " and ifnull(voucher_type, '')!='Period Closing Voucher'"

    gle = frappe.db.sql("""
		select
			account, sum(debit) as opening_debit, sum(credit) as opening_credit
		from `tabGL Entry`
		where
			company=%(company)s
			{additional_conditions}
			and (posting_date < %(from_date)s or ifnull(is_opening, 'No') = 'Yes')
			and account in (select name from `tabAccount` where report_type=%(report_type)s)
		group by account""".format(additional_conditions=additional_conditions),
                        {
                            "company": filters.get("company"),
                            "from_date": filters.get("from_date"),
                            "report_type": report_type,
                            "year_start_date": filters.get("year_start_date")
                        },
                        as_dict=True)

    opening = frappe._dict()
    for d in gle:
        opening.setdefault(d.account, d)

    return opening


def calculate_values(accounts, gl_entries_by_account, opening_balances, filters, company_currency):
    init = {
        "opening_debit": 0.0,
        "opening_credit": 0.0,
        "debit": 0.0,
        "credit": 0.0,
        "closing_debit": 0.0,
        "closing_credit": 0.0
    }

    total_row = {
        "account": "Total",
        "account_name": "Total",
        "warn_if_negative": True,
        "opening_debit": 0.0,
        "opening_credit": 0.0,
        "debit": 0.0,
        "credit": 0.0,
        "closing_debit": 0.0,
        "closing_credit": 0.0,
        "parent_account": None,
        "indent": 0,
        "has_value": True,
        "currency": company_currency
    }

    for d in accounts:
        d.update(init.copy())

        # add opening
        d["opening_debit"] = opening_balances.get(d.name, {}).get("opening_debit", 0)
        d["opening_credit"] = opening_balances.get(d.name, {}).get("opening_credit", 0)

        for entry in gl_entries_by_account.get(d.name, []):
            if cstr(entry.is_opening) != "Yes":
                d["debit"] += flt(entry.debit)
                d["credit"] += flt(entry.credit)

        total_row["debit"] += d["debit"]
        total_row["credit"] += d["credit"]
        total_row["opening_debit"] += d["opening_debit"]
        total_row["opening_credit"] += d["opening_credit"]

        total_row["closing_debit"] += (d["debit"] - d["credit"]) if (d["debit"] - d["credit"]) > 0 else 0
        total_row["closing_credit"] += abs(d["debit"] - d["credit"]) if (d["debit"] - d["credit"]) < 0 else 0

    return total_row


def accumulate_values_into_parents(accounts, accounts_by_name):
    for d in reversed(accounts):
        if d.parent_account:
            for key in value_fields:
                accounts_by_name[d.parent_account][key] += d[key]


def prepare_data(accounts, filters, total_row, parent_children_map, company_currency):
    data = []
    total_row["closing_debit"] = 0
    total_row["closing_credit"] = 0
    for d in accounts:
        has_value = False
        row = {
            "account_name": d.account_name,
            "account": d.name,
            "parent_account": d.parent_account,
            "indent": d.indent,
            "from_date": filters.get("from_date"),
            "to_date": filters.get("to_date"),
            "currency": company_currency
        }

        prepare_opening_and_closing(d)

        for key in value_fields:
            row[key] = flt(d.get(key, 0.0), 3)

            if abs(row[key]) >= 0.005:
                # ignore zero values
                has_value = True

        row["has_value"] = has_value
        data.append(row)

        if not d.parent_account:
            total_row["closing_debit"] += (d["debit"] - d["credit"]) if (d["debit"] - d["credit"]) > 0 else 0
            total_row["closing_credit"] += abs(d["debit"] - d["credit"]) if (d["debit"] - d["credit"]) < 0 else 0

    data.extend([{}, total_row])

    return data


def prepare_opening_and_closing(d):
    d["closing_debit"] = d["opening_debit"] + d["debit"]
    d["closing_credit"] = d["opening_credit"] + d["credit"]

    if d["closing_debit"] > d["closing_credit"]:
        d["closing_debit"] -= d["closing_credit"]
        d["closing_credit"] = 0.0

    else:
        d["closing_credit"] -= d["closing_debit"]
        d["closing_debit"] = 0.0

    if d["opening_debit"] > d["opening_credit"]:
        d["opening_debit"] -= d["opening_credit"]
        d["opening_credit"] = 0.0

    else:
        d["opening_credit"] -= d["opening_debit"]
        d["opening_debit"] = 0.0
