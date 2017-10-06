# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
import frappe
from erpnext.accounts.utils import get_last_daily_movement_balance


def execute(filters=None):
    data = []

    columns = [_("Date") + ":Date:100", _("Concept") + ":Select:300", _("Income") + ":Currency/currency:150", _("Expenditures") + ":Currency/currency:150", _("Balance") + ":Currency/currency:150", _("Mode of Payment") + "::150"]

    total_income = 0
    total_expenditure = 0
    balance = 0
    current_payment_mode = ""

    result = frappe.db.sql("""select posting_date, title, party_type, payment_type, paid_amount, 
    mode_of_payment as payment_mode from `tabPayment Entry` where payment_type <> 'Internal Transfer' 
    and posting_date >= %(start_date)s and posting_date <= %(end_date)s {conditions} 
    order by mode_of_payment,posting_date asc""".format(conditions=get_conditions(filters)), filters, as_dict=1)

    for row in result:
        if current_payment_mode != row.payment_mode:
            if current_payment_mode != "":
                data.append(["", _("Total"), total_income, total_expenditure,
                             total_income - total_expenditure, current_payment_mode])
                data.append([])
                data.append([])


            start_balance = get_last_daily_movement_balance(row.posting_date, row.payment_mode)
            if start_balance is None:
                balance = 0
                data.append([row.posting_date, _("Initial Balance"), 0, 0, balance, row.payment_mode])
                total_income = 0
                total_expenditure = 0
            else:
                balance = start_balance.income - start_balance.expenditures
                total_income = start_balance.income
                total_expenditure = start_balance.expenditures
                data.append([row.posting_date, _("Initial Balance"), start_balance.income,
                             start_balance.expenditures, balance, row.payment_mode])

            current_payment_mode = row.payment_mode
        income = 0
        expenditure = 0
        concept = ""
        if row.payment_type == "Receive":
            concept = _("Receive") + " "
            income = row.paid_amount
            total_income += income
        if row.payment_type == "Pay":
            concept = _("Payment ") + " "
            expenditure = row.paid_amount
            total_expenditure+= expenditure
        if row.party_type == "Customer":
            concept+= _("Customer") + " " + row.title
        if row.party_type == "Supplier":
            concept+= _("Supplier") + " " + row.title
        balance = balance + income - expenditure
        d = [row.posting_date, concept, income, expenditure, balance, row.payment_mode]
        data.append(d)
    if result:
        data.append([filters.get("target_date"), _("Total"), total_income, total_expenditure,
                     balance, current_payment_mode])
    return columns, data


def get_conditions(filters):
    conditions = []
    if filters.get("mode_of_payment"):
        conditions.append("mode_of_payment=%(mode_of_payment)s")
    return "and {}".format(" and ".join(conditions)) if conditions else ""