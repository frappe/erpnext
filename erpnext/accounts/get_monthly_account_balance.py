# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
import erpnext
from erpnext.accounts.report.financial_statements \
    import filter_accounts, set_gl_entries_by_account, filter_out_zero_value_rows
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr
import frappe


@frappe.whitelist(allow_guest=True)
def get_monthly_account_balance():
    # 'account',
    try:
        data = frappe.form_dict

        account = data.get('account')
        company = data.get('company_name')
        from_date = data.get('from_date')
        to_date = data.get('end_time')
        frappe.set_user("Administrator")
        
        account_info = get_balance(account, dict(
            from_date=from_date,
            to_date=to_date,
            company=company,
            show_zero_values=1
        ))
      
    except Exception as e:
        return dict(status=False, message=str(e))
    return dict(status=True, message="Success", account_info=account_info)

value_fields = ("opening_debit", "opening_credit", "debit", "credit", "closing_debit", "closing_credit")
  
  
def get_balance(account, filters):
    accounts = frappe.db.sql("""select name, company, parent_account, account_name, root_type, report_type, lft, rgt
		from `tabAccount` where name= %s and company = %s;""", (account, filters.get("company")), as_dict=True)
    
    if len(accounts) == 0:
      frappe.throw("There is no such account")
      
    company_currency = erpnext.get_company_currency(filters.get("company"))

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
group by year(posting_date), month(posting_date);""".format(additional_conditions=additional_conditions),
	{
	    "company": filters.get("company"),
	    "from_date": filters.get("from_date"),
	    "report_type": report_type,
	    "year_start_date": filters.get("year_start_date")
	},
	as_dict=True)

    return data


def get_rootwise_opening_balances(filters, report_type):
    additional_conditions = ""
    if not filters.get("show_unclosed_fy_pl_balances", 0):
        additional_conditions = " and posting_date >= %(year_start_date)s" \
            if report_type == "Profit and Loss" else ""

    if not flt(filters.get("with_period_closing_entry", 0)):
        additional_conditions += " and ifnull(voucher_type, '')!='Period Closing Voucher'"

    gle = frappe.db.sql("""
select
	monthname(posting_date) as `month`, account, sum(debit) as opening_debit, sum(credit) as opening_credit
from `tabGL Entry`
where
	company=%(company)s
	{additional_conditions}
	and (posting_date < %(from_date)s or ifnull(is_opening, 'No') = 'Yes')
	and account in (select name from `tabAccount` where report_type=%(report_type)s)
group by year(posting_date), month(posting_date);""".format(additional_conditions=additional_conditions),
                        {
                            "company": filters.get("company"),
                            "from_date": filters.get("from_date"),
                            "report_type": report_type,
                            "year_start_date": filters.get("year_start_date")
                        },
                        as_dict=True)

    opening = frappe._dict()
    for d in gle:
        opening.setdefault(d.month, d)

    return opening


def prepare_data(accounts, filters, company_currency):
    data = []

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

        data.append(row)

    return data

