import frappe
from frappe import _
from frappe import utils as frappe_utils


@frappe.whitelist()
def get_salaries_and_wages_amount():
    from_date = frappe_utils.get_first_day(frappe_utils.today())
    to_date = frappe_utils.get_last_day(frappe_utils.today())

    result = frappe.db.sql(
        """
        SELECT SUM(debit)
        FROM `tabGL Entry`
        WHERE account = 'Salaries & Wages Payable - U2'
        AND posting_date BETWEEN %s AND %s
        """,
        (from_date, to_date),
    )
    return {
        "value": result[0][0] or 0,
        "fieldtype": "Currency",
        "route": ["query-report", "General Ledger"],
        "route_options": {
            "account": "Salaries & Wages Payable - U2",
            "from_date": from_date,
            "to_date": to_date,
        }
    }


@frappe.whitelist()
def get_weekly_emi_and_bank_charges_due():
    from_date = frappe_utils.get_first_day_of_week(frappe_utils.today())
    to_date = frappe_utils.get_last_day_of_week(frappe_utils.today())

    result = frappe.db.sql(
        """
        SELECT SUM(debit)
        FROM `tabGL Entry`
        WHERE account = 'Interest & Bank Charges - U2'
        AND posting_date BETWEEN %s AND %s
        """,
        (from_date, to_date),
    )
    return {
        "value": result[0][0] or 0,
        "fieldtype": "Currency",
        "route": ["query-report", "General Ledger"],
        "route_options": {
            "account": "Interest & Bank Charges - U2",
            "from_date": from_date,
            "to_date": to_date,
        }
    }

@frappe.whitelist()
def get_overall_emi_and_bank_charges_due():
    from_date = frappe_utils.get_first_day(frappe_utils.today())
    to_date = frappe_utils.get_last_day(frappe_utils.today())

    result = frappe.db.sql(
        """
        SELECT SUM(debit)
        FROM `tabGL Entry`
        WHERE account = 'Interest & Bank Charges - U2'
        AND posting_date BETWEEN %s AND %s
        """,
        (from_date, to_date),
    )
    return {
        "value": result[0][0] or 0,
        "fieldtype": "Currency",
        "route": ["query-report", "General Ledger"],
        "route_options": {
            "account": "Interest & Bank Charges - U2",
            "from_date": from_date,
            "to_date": to_date,
        }
    }