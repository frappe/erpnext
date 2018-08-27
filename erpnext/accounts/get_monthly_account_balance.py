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
        fiscal_year = data.get('fiscal_year')
        frappe.set_user("Administrator")
        filters = dict(
            from_date=from_date,
            to_date=to_date,
            company=company,
            show_zero_values=1,
	    fiscal_year=fiscal_year
        )
	validate_filters(filters)
        account_info = get_balance(account, filters)
      	openings = get_rootwise_opening_balances(account, filters)
    except Exception as e:
        return dict(status=False, message=str(e))
    return dict(status=True, message="Success", account_info=account_info, openings=openings)


def validate_filters(filters):
    if not filters.get("fiscal_year"):
        frappe.throw(_("Fiscal Year {0} is required").format(filters.get("fiscal_year")))

    fiscal_year = frappe.db.get_value(
        "Fiscal Year",
        filters.get("fiscal_year"),
        ["year_start_date", "year_end_date"],
        as_dict=True
    )
    if not fiscal_year:
        frappe.throw(_("Fiscal Year {0} does not exist").format(filters.get("fiscal_year")))
    else:
        filters["year_start_date"] = getdate(fiscal_year.year_start_date)
        filters["year_end_date"] = getdate(fiscal_year.year_end_date)

    if not filters.get("from_date"):
        filters["from_date"] = filters.get("year_start_date")

    if not filters.get("to_date"):
        filters["to_date"] = filters.get("year_end_date")

    filters["from_date"] = getdate(filters.get("from_date"))
    filters["to_date"] = getdate(filters.get("to_date"))

    if filters.get("from_date") > filters.get("to_date"):
        frappe.throw(_("From Date cannot be greater than To Date"))

    if (filters.get("from_date") < filters.get("year_start_date")) or (
        filters.get("from_date") > filters.get("year_end_date")):
        frappe.msgprint(_("From Date should be within the Fiscal Year. Assuming From Date = {0}") \
                        .format(formatdate(filters.year_start_date)))

        filters["from_date"] = filters.get("year_start_date")

    if (filters.get("to_date") < filters.get("year_start_date")) or (
        filters.get("to_date") > filters.get("year_end_date")):
        frappe.msgprint(_("To Date should be within the Fiscal Year. Assuming To Date = {0}") \
                        .format(formatdate(filters.get("year_end_date"))))
        filters["to_date"] = filters.get("year_end_date")

  
def get_balance(account, filters):
    accounts = frappe.db.sql("""select name, company, parent_account, account_name, root_type, report_type, lft, rgt
		from `tabAccount` where name= %s and company = %s;""", (account, filters.get("company")), as_dict=True)
    
    if len(accounts) == 0:
      frappe.throw("There is no such account")
      
    company_currency = erpnext.get_company_currency(filters.get("company"))
    
    gle = frappe.db.sql("""
select
	monthname(posting_date) as `month`, account, sum(debit) as opening_debit, sum(credit) as opening_credit
from `tabGL Entry`
where
	company=%(company)s
	and (posting_date < %(from_date)s or ifnull(is_opening, 'No') = 'Yes')
	and account in = %(account)s
group by year(posting_date), month(posting_date);""",
	{
	    "company": filters.get("company"),
	    "from_date": filters.get("from_date"),
	    "account": account,
	    "year_start_date": filters.get("year_start_date")
	},
	as_dict=True)

    return gle


def get_rootwise_opening_balances(account, filters):

    gle = frappe.db.sql("""
select
	monthname(posting_date) as `month`, account, sum(debit) as opening_debit, sum(credit) as opening_credit
from `tabGL Entry`
where
	company=%(company)s
	and (posting_date < %(from_date)s or ifnull(is_opening, 'No') = 'Yes')
	and account = %(account)s
group by year(posting_date), month(posting_date);""",
                        {
                            "company": filters.get("company"),
                            "from_date": filters.get("from_date"),
                            "account": account,
                            "year_start_date": filters.get("year_start_date")
                        },
                        as_dict=True)

    opening = frappe._dict()
    for d in gle:
        opening.setdefault(d.month, d)

    return opening

