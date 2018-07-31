from __future__ import unicode_literals

import frappe
from frappe import msgprint, _


def execute(filters=None):
    return _execute(filters)


def _execute(filters):
    if not filters: filters = frappe._dict({})

    data = get_data(filters)
    columns = get_columns()

    if not data:
        msgprint(_("No record found"))

    return columns, data


def get_columns():
    # return columns
    columns = [
        _("Invoice") + ":Link/Sales Invoice:120", _("Posting Date") + ":Date:80",
        _("Customer") + ":Link/Customer:120", _("Customer Name") + "::120"
    ]

    columns = [
        {
            "fieldname": "title",
            "label": " ",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "title",
            "label": _("Balance"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "modification",
            "label": _("Modification"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "vat",
            "label": _("VAT"),
            "fieldtype": "Data",
            "width": 100
        },
    ]

    return columns


def get_data(filters):
    conditions = get_conditions(filters)

    result = [
        _("Tax"), _("Sales"), _("Modification"), _("Tax")
    ]

    currency = frappe.get_value("Company", filters.get("company"), "default_currency")
    sales_amounts = frappe.db.sql("""SELECT 
    COALESCE(SUM(base_net_amount), 0) AS amount
FROM
    `tabSales Invoice Item`
WHERE
    parent IN (SELECT 
            name
        FROM
            `tabSales Invoice`
        WHERE
            docstatus = 1 {conditions}) 
UNION SELECT 
    COALESCE(SUM(base_tax_amount_after_discount_amount), 0) AS amount
FROM
    `tabSales Taxes and Charges`
WHERE
    parent IN (SELECT 
            name
        FROM
            `tabSales Invoice`
        WHERE
            docstatus = 1 {conditions});""".format(
        conditions=conditions
    ), as_dict=True)

    result += [
        "VAT", sales_amounts[0][0], "-0.0", sales_amounts[1][0]
    ]

    result += [
        "Zero VAT", "0.0", "-0.0", "0.0"
    ]

    result += [
        "Free VAT", "0.0", "-0.0", "0.0"
    ]

    result += [
        "Total", "{0} {1}".format(
            sales_amounts[0][0], currency or "SAR"),
        "-0.0",
        "{0} {1}".format(sales_amounts[1][0], currency or "SAR")
    ]

    result += [
        " ", " ", " ", " "
    ]

    purchases_amounts = frappe.db.sql("""SELECT 
    COALESCE(SUM(base_net_amount), 0) AS amount
FROM
    `tabPurchase Invoice Item`
WHERE
    parent IN (SELECT 
            name
        FROM
            `tabPurchase Invoice`
        WHERE
            docstatus = 1 {conditions}) 
UNION SELECT 
    COALESCE(CASE add_deduct_tax
                WHEN 'Add' THEN SUM(base_tax_amount_after_discount_amount)
                ELSE SUM(base_tax_amount_after_discount_amount) * - 1
            END,
            0) AS tax_amount
FROM
    `tabPurchase Taxes and Charges`
WHERE
    parent IN (SELECT 
            name
        FROM
            `tabPurchase Invoice`
        WHERE
            docstatus = 1 {conditions})
        AND category IN ('Total' , 'Valuation and Total')
        AND base_tax_amount_after_discount_amount != 0;""".format(
        conditions=conditions
    ), as_dict=True)

    result += [
        _("Tax"), _("Purchases"), _("Modification"), _("Paid Tax")
    ]

    result += [
        "VAT", purchases_amounts[0][0], "-0.0", purchases_amounts[1][0]
    ]

    result += [
        "Zero VAT", "0.0", "-0.0", "0.0"
    ]

    result += [
        "Free VAT", "0.0", "-0.0", "0.0"
    ]

    result += [
        "Total", "{0} {1}".format(
            purchases_amounts[0][0], currency or "SAR"),
        "-0.0",
        "{0} {1}".format(purchases_amounts[1][0], currency or "SAR")
    ]

    return result


def get_conditions(filters):
    conditions = ""

    if filters.get("company"): conditions += " and company=%(company)s"

    if filters.get("from_date"): conditions += " and posting_date >= %(from_date)s"
    if filters.get("to_date"): conditions += " and posting_date <= %(to_date)s"

    return conditions
