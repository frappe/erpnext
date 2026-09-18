# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""
Cash Basis Financial Statements Engine.

Under cash accounting:
- Revenue is recognized when payment is received
- Expenses are recognized when payment is made
- Partial payments proportionally recognize income/expense based on the
  original account distribution of the invoice

For P&L:  GL entries from invoices are replaced by payment-date virtual entries
          scaled by (allocated_payment / invoice_grand_total).
For Balance Sheet: Invoice GL entries are scaled by settlement_ratio computed
                   as of the report date; non-invoice entries pass through unchanged.
"""

import frappe
from frappe import _
from frappe.utils import cstr, flt

from erpnext.accounts.report.financial_statements import (
    accumulate_values_into_parents,
    add_total_row,
    calculate_values,
    filter_accounts,
    filter_out_zero_value_rows,
    get_accounts,
    get_appropriate_currency,
    get_cost_centers_with_children,
    prepare_data,
)


def get_cash_basis_data(
    company,
    root_type,
    balance_must_be,
    period_list,
    filters=None,
    accumulated_values=1,
    only_current_fiscal_year=True,
    total=True,
):
    """
    Drop-in replacement for financial_statements.get_data() that uses cash basis GL entries.

    For Income/Expense (P&L):  income/expense recognised at payment date.
    For Asset/Liability/Equity (Balance Sheet): invoice entries scaled by settlement ratio.
    """
    accounts = get_accounts(company, root_type)
    if not accounts:
        return None

    accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)
    company_currency = get_appropriate_currency(company, filters)

    # For P&L: fetch from fiscal-year start.  For Balance Sheet: all time (None).
    from_date = period_list[0]["year_start_date"] if only_current_fiscal_year else None
    to_date = period_list[-1]["to_date"]

    gl_entries_by_account = _set_cash_basis_gl_entries_by_account(
        company=company,
        from_date=from_date,
        to_date=to_date,
        filters=filters or frappe._dict(),
        root_type=root_type,
        accounts_by_name=accounts_by_name,
    )

    calculate_values(
        accounts_by_name,
        gl_entries_by_account,
        period_list,
        accumulated_values,
        ignore_accumulated_values_for_fy=False,
    )
    accumulate_values_into_parents(accounts, accounts_by_name, period_list)

    show_zero = getattr(filters, "show_zero_values", False) if filters else False
    acc_values = getattr(filters, "accumulated_values", accumulated_values) if filters else accumulated_values

    out = prepare_data(accounts, balance_must_be, period_list, company_currency, accumulated_values=acc_values)
    out = filter_out_zero_value_rows(out, parent_children_map, show_zero)

    if out and total:
        add_total_row(out, root_type, balance_must_be, period_list, company_currency)

    return out


# ---------------------------------------------------------------------------
# Internal routing
# ---------------------------------------------------------------------------


def _set_cash_basis_gl_entries_by_account(company, from_date, to_date, filters, root_type, accounts_by_name):
    """Build {account: [gl-entry-like dicts]} using cash basis logic."""
    gl_entries_by_account = {}

    if root_type in ("Income", "Expense"):
        invoice_type = "Sales Invoice" if root_type == "Income" else "Purchase Invoice"

        # 1. Direct (non-invoice) GL entries – recognised on posting date as-is
        for entry in _get_non_invoice_gl_entries(
            company, from_date, to_date, filters, accounts_by_name, invoice_type
        ):
            gl_entries_by_account.setdefault(entry.account, []).append(entry)

        # 2. Payment-proportional entries – recognised on payment date
        for entry in _get_payment_based_gl_entries(
            company, from_date, to_date, filters, root_type, accounts_by_name
        ):
            gl_entries_by_account.setdefault(entry.account, []).append(entry)

        # 3. Self-paid invoices: is_paid=1 PI and is_pos=1 SI – no separate PE, recognised at invoice date
        for entry in _get_self_paid_invoice_gl_entries(
            company, from_date, to_date, filters, root_type, accounts_by_name
        ):
            gl_entries_by_account.setdefault(entry.account, []).append(entry)

        # 4. Credit JEs (DR Expense/CR Supplier Payable  OR  DR Customer Receivable/CR Income)
        #    – recognised only when the AR/AP is settled, mirroring SI/PI treatment
        for entry in _get_je_credit_payment_entries(
            company, from_date, to_date, filters, root_type, accounts_by_name
        ):
            gl_entries_by_account.setdefault(entry.account, []).append(entry)

    else:
        # Balance Sheet: scale invoice GL entries by settlement ratio
        for entry in _get_balance_sheet_cash_basis_entries(
            company, from_date, to_date, filters, accounts_by_name
        ):
            gl_entries_by_account.setdefault(entry.account, []).append(entry)

    return gl_entries_by_account


# ---------------------------------------------------------------------------
# P&L helpers
# ---------------------------------------------------------------------------


def _get_non_invoice_gl_entries(company, from_date, to_date, filters, accounts_by_name, exclude_voucher_type):
    """
    Standard GL entries for the given accounts excluding the specified invoice voucher type
    (Sales Invoice or Purchase Invoice) and Period Closing Vouchers.

    For the Expense path (exclude_voucher_type='Purchase Invoice'), Journal Entries that credit
    a Supplier Payable account are also excluded — they are credit purchases equivalent to a PI
    and should only be recognised when the payable is settled (handled by path 4).
    """
    account_names = list(accounts_by_name.keys())
    if not account_names:
        return []

    conditions = [
        "gl.company = %(company)s",
        "gl.is_cancelled = 0",
        "gl.posting_date <= %(to_date)s",
        "gl.voucher_type != %(exclude_voucher_type)s",
        "gl.voucher_type != 'Period Closing Voucher'",
        "gl.account IN %(accounts)s",
    ]
    params = {
        "company": company,
        "to_date": to_date,
        "exclude_voucher_type": exclude_voucher_type,
        "accounts": tuple(account_names),
    }

    if from_date:
        conditions.append("gl.posting_date >= %(from_date)s")
        params["from_date"] = from_date

    # Exclude credit JEs that should only be recognised when AR/AP is settled:
    # - Expense path: JEs that credit a Supplier Payable (credit purchase via JE)
    # - Income path: JEs that debit a Customer Receivable (credit sale via JE)
    # These are handled by _get_je_credit_payment_entries (path 4).
    if exclude_voucher_type == "Purchase Invoice":
        conditions.append(
            """NOT (
                gl.voucher_type = 'Journal Entry'
                AND EXISTS (
                    SELECT 1
                    FROM `tabGL Entry` je_par
                    INNER JOIN tabAccount ar_ap_acc
                        ON ar_ap_acc.name = je_par.account
                        AND ar_ap_acc.account_type = 'Payable'
                    WHERE je_par.voucher_no = gl.voucher_no
                      AND je_par.is_cancelled = 0
                      AND je_par.party_type = 'Supplier'
                      AND je_par.party IS NOT NULL
                      AND je_par.party != ''
                      AND (je_par.credit - je_par.debit) > 0
                )
            )"""
        )
    elif exclude_voucher_type == "Sales Invoice":
        conditions.append(
            """NOT (
                gl.voucher_type = 'Journal Entry'
                AND EXISTS (
                    SELECT 1
                    FROM `tabGL Entry` je_par
                    INNER JOIN tabAccount ar_ap_acc
                        ON ar_ap_acc.name = je_par.account
                        AND ar_ap_acc.account_type = 'Receivable'
                    WHERE je_par.voucher_no = gl.voucher_no
                      AND je_par.is_cancelled = 0
                      AND je_par.party_type = 'Customer'
                      AND je_par.party IS NOT NULL
                      AND je_par.party != ''
                      AND (je_par.debit - je_par.credit) > 0
                )
            )"""
        )

    _apply_gl_filter_conditions(conditions, params, filters)

    return frappe.db.sql(
        """
        SELECT
            gl.account, gl.debit, gl.credit,
            gl.posting_date, gl.fiscal_year,
            gl.account_currency,
            gl.debit_in_account_currency, gl.credit_in_account_currency,
            gl.is_opening
        FROM `tabGL Entry` gl
        WHERE {where}
        """.format(where=" AND ".join(conditions)),
        params,
        as_dict=True,
    )


def _get_payment_based_gl_entries(company, from_date, to_date, filters, root_type, accounts_by_name):
    """
    Generate virtual GL entries dated at payment date with proportional income/expense amounts.

    Handles:
    - Payment Entry References (standard payments, advance application)
    - Journal Entry settlements (against_voucher_type = SI/PI)
    """
    is_income = root_type == "Income"
    invoice_type = "Sales Invoice" if is_income else "Purchase Invoice"
    invoice_table = "tabSales Invoice" if is_income else "tabPurchase Invoice"

    account_names = list(accounts_by_name.keys())
    if not account_names:
        return []

    entries = []

    # --- Payment Entry Reference path ---
    pe_conditions = [
        "pe.company = %(company)s",
        "pe.docstatus = 1",
        "pe.posting_date <= %(to_date)s",
        "per.reference_doctype = %(invoice_type)s",
        "inv_gl.account IN %(accounts)s",
        "inv_gl.voucher_type = %(invoice_type)s",
        "inv_gl.is_cancelled = 0",
    ]
    pe_params = {
        "company": company,
        "to_date": to_date,
        "invoice_type": invoice_type,
        "accounts": tuple(account_names),
    }
    if from_date:
        pe_conditions.append("pe.posting_date >= %(from_date)s")
        pe_params["from_date"] = from_date

    _apply_payment_filter_conditions(pe_conditions, pe_params, filters)

    pe_entries = frappe.db.sql(
        """
        SELECT
            inv_gl.account,
            pe.posting_date,
            '' AS fiscal_year,
            (inv_gl.debit  * per.allocated_amount / NULLIF(inv.grand_total, 0)) AS debit,
            (inv_gl.credit * per.allocated_amount / NULLIF(inv.grand_total, 0)) AS credit,
            (inv_gl.debit_in_account_currency  * per.allocated_amount / NULLIF(inv.grand_total, 0)) AS debit_in_account_currency,
            (inv_gl.credit_in_account_currency * per.allocated_amount / NULLIF(inv.grand_total, 0)) AS credit_in_account_currency,
            inv_gl.account_currency
        FROM `tabPayment Entry Reference` per
        INNER JOIN `tabPayment Entry` pe  ON pe.name = per.parent
        INNER JOIN `{invoice_table}` inv  ON inv.name = per.reference_name
        INNER JOIN `tabGL Entry` inv_gl   ON inv_gl.voucher_no = per.reference_name
        WHERE {where}
        """.format(
            invoice_table=invoice_table,
            where=" AND ".join(pe_conditions),
        ),
        pe_params,
        as_dict=True,
    )
    entries.extend(pe_entries)

    # --- Journal Entry settlement path (via Payment Ledger Entry) ---
    # PLE captures JE settlements from both direct GL against_voucher tagging and the
    # Payment Reconciliation tool (which writes PLE but does not set GL against_voucher).
    je_params = {
        "company": company,
        "to_date": to_date,
        "invoice_type": invoice_type,
        "accounts": tuple(account_names),
    }
    if from_date:
        je_params["from_date"] = from_date

    je_entries = frappe.db.sql(
        """
        SELECT
            inv_gl.account,
            ple.posting_date,
            '' AS fiscal_year,
            (inv_gl.debit  * ABS(ple.amount) / NULLIF(inv.grand_total, 0)) AS debit,
            (inv_gl.credit * ABS(ple.amount) / NULLIF(inv.grand_total, 0)) AS credit,
            (inv_gl.debit_in_account_currency  * ABS(ple.amount) / NULLIF(inv.grand_total, 0)) AS debit_in_account_currency,
            (inv_gl.credit_in_account_currency * ABS(ple.amount) / NULLIF(inv.grand_total, 0)) AS credit_in_account_currency,
            inv_gl.account_currency
        FROM `tabPayment Ledger Entry` ple
        INNER JOIN `{invoice_table}` inv
            ON inv.name = ple.against_voucher_no AND inv.docstatus = 1
        INNER JOIN `tabGL Entry` inv_gl
            ON inv_gl.voucher_no = ple.against_voucher_no
           AND inv_gl.account IN %(accounts)s
           AND inv_gl.voucher_type = %(invoice_type)s
           AND inv_gl.is_cancelled = 0
        WHERE ple.voucher_type = 'Journal Entry'
          AND ple.against_voucher_type = %(invoice_type)s
          AND ple.delinked = 0
          AND ple.amount < 0
          AND ple.company = %(company)s
          AND ple.posting_date <= %(to_date)s
          {from_date_cond}
        """.format(
            invoice_table=invoice_table,
            from_date_cond="AND ple.posting_date >= %(from_date)s" if from_date else "",
        ),
        je_params,
        as_dict=True,
    )
    entries.extend(je_entries)

    return entries


def _get_self_paid_invoice_gl_entries(company, from_date, to_date, filters, root_type, accounts_by_name):
    """
    GL entries from invoices where payment is embedded — no separate Payment Entry exists.

    - Purchase Invoice with is_paid=1: fully paid at invoice posting date (ratio 1.0)
    - Sales Invoice with is_pos=1 and paid_amount>0: POS payment portion recognised at
      invoice posting date, scaled by paid_amount / grand_total.  Any outstanding amount
      is handled by the regular PE path when a Payment Entry is created later.
    """
    is_income = root_type == "Income"
    account_names = list(accounts_by_name.keys())
    if not account_names:
        return []

    entries = []

    if is_income:
        conditions = [
            "gl.company = %(company)s",
            "gl.is_cancelled = 0",
            "gl.voucher_type = 'Sales Invoice'",
            "gl.posting_date <= %(to_date)s",
            "gl.account IN %(accounts)s",
            "si.is_pos = 1",
            "si.paid_amount > 0",
            "si.docstatus = 1",
        ]
        params = {"company": company, "to_date": to_date, "accounts": tuple(account_names)}
        if from_date:
            conditions.append("gl.posting_date >= %(from_date)s")
            params["from_date"] = from_date
        _apply_gl_filter_conditions(conditions, params, filters)

        entries.extend(
            frappe.db.sql(
                """
                SELECT
                    gl.account, gl.posting_date, gl.fiscal_year,
                    gl.account_currency, gl.is_opening,
                    (gl.debit  * si.paid_amount / NULLIF(si.grand_total, 0)) AS debit,
                    (gl.credit * si.paid_amount / NULLIF(si.grand_total, 0)) AS credit,
                    (gl.debit_in_account_currency  * si.paid_amount / NULLIF(si.grand_total, 0)) AS debit_in_account_currency,
                    (gl.credit_in_account_currency * si.paid_amount / NULLIF(si.grand_total, 0)) AS credit_in_account_currency
                FROM `tabGL Entry` gl
                INNER JOIN `tabSales Invoice` si ON si.name = gl.voucher_no
                WHERE {where}
                """.format(where=" AND ".join(conditions)),
                params,
                as_dict=True,
            )
        )

    else:
        conditions = [
            "gl.company = %(company)s",
            "gl.is_cancelled = 0",
            "gl.voucher_type = 'Purchase Invoice'",
            "gl.posting_date <= %(to_date)s",
            "gl.account IN %(accounts)s",
            "pi.is_paid = 1",
            "pi.docstatus = 1",
        ]
        params = {"company": company, "to_date": to_date, "accounts": tuple(account_names)}
        if from_date:
            conditions.append("gl.posting_date >= %(from_date)s")
            params["from_date"] = from_date
        _apply_gl_filter_conditions(conditions, params, filters)

        entries.extend(
            frappe.db.sql(
                """
                SELECT
                    gl.account, gl.posting_date, gl.fiscal_year,
                    gl.account_currency, gl.is_opening,
                    gl.debit, gl.credit,
                    gl.debit_in_account_currency, gl.credit_in_account_currency
                FROM `tabGL Entry` gl
                INNER JOIN `tabPurchase Invoice` pi ON pi.name = gl.voucher_no
                WHERE {where}
                """.format(where=" AND ".join(conditions)),
                params,
                as_dict=True,
            )
        )

    return entries


def _get_je_credit_payment_entries(company, from_date, to_date, filters, root_type, accounts_by_name):
    """
    Recognise P&L amounts from credit JEs only when the associated AR/AP is settled.

    Credit-expense JE (DR Expense, CR Supplier Payable) — mirrors Purchase Invoice treatment:
      recognised when the payable is paid (PE Reference or JE against_voucher).

    Credit-income JE (DR Customer Receivable, CR Income) — mirrors Sales Invoice treatment:
      recognised when the receivable is collected (PE Reference or JE against_voucher).
    """
    is_income = root_type == "Income"
    account_names = list(accounts_by_name.keys())
    if not account_names:
        return []

    party_type = "Customer" if is_income else "Supplier"
    ar_ap_type = "Receivable" if is_income else "Payable"

    # Fully-qualified column expressions (avoids "Column 'debit' is ambiguous" in multi-join SQL)
    # AR/AP direction in the credit JE: Income → AR debited; Expense → AP credited
    if is_income:
        je_par_net = "je_par.debit - je_par.credit"   # AR debit > credit
        je_pl_net = "je_pl.credit - je_pl.debit"      # Income credit > debit
    else:
        je_par_net = "je_par.credit - je_par.debit"   # AP credit > debit
        je_pl_net = "je_pl.debit - je_pl.credit"      # Expense debit > credit

    # Sub-query: total AR/AP amount per credit JE
    ar_ap_subquery = f"""
        SELECT je_par.voucher_no, SUM({je_par_net}) AS total_amount
        FROM `tabGL Entry` je_par
        INNER JOIN tabAccount ar_ap_acc
            ON ar_ap_acc.name = je_par.account AND ar_ap_acc.account_type = %(ar_ap_type)s
        WHERE je_par.voucher_type = 'Journal Entry'
          AND je_par.is_cancelled = 0
          AND je_par.party_type = %(party_type)s
          AND je_par.party IS NOT NULL
          AND je_par.party != ''
          AND ({je_par_net}) > 0
        GROUP BY je_par.voucher_no
    """

    entries = []
    base_params = {
        "company": company, "to_date": to_date, "accounts": tuple(account_names),
        "party_type": party_type, "ar_ap_type": ar_ap_type,
    }

    # --- Path A: PE Reference pointing to the credit JE ---
    pe_conditions = [
        "pe.company = %(company)s",
        "pe.docstatus = 1",
        "pe.posting_date <= %(to_date)s",
        "per.reference_doctype = 'Journal Entry'",
        "je_pl.account IN %(accounts)s",
        "je_pl.voucher_type = 'Journal Entry'",
        "je_pl.is_cancelled = 0",
        f"({je_pl_net}) > 0",
    ]
    pe_params = dict(base_params)
    if from_date:
        pe_conditions.append("pe.posting_date >= %(from_date)s")
        pe_params["from_date"] = from_date
    _apply_payment_filter_conditions(pe_conditions, pe_params, filters)

    entries.extend(
        frappe.db.sql(
            """
            SELECT
                je_pl.account,
                pe.posting_date,
                '' AS fiscal_year,
                je_pl.account_currency,
                0 AS is_opening,
                (je_pl.debit  * per.allocated_amount / NULLIF(ar_ap.total_amount, 0)) AS debit,
                (je_pl.credit * per.allocated_amount / NULLIF(ar_ap.total_amount, 0)) AS credit,
                (je_pl.debit_in_account_currency  * per.allocated_amount / NULLIF(ar_ap.total_amount, 0)) AS debit_in_account_currency,
                (je_pl.credit_in_account_currency * per.allocated_amount / NULLIF(ar_ap.total_amount, 0)) AS credit_in_account_currency
            FROM `tabPayment Entry Reference` per
            INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
            INNER JOIN ({ar_ap_subquery}) ar_ap ON ar_ap.voucher_no = per.reference_name
            INNER JOIN `tabGL Entry` je_pl ON je_pl.voucher_no = per.reference_name
            WHERE {where}
            """.format(ar_ap_subquery=ar_ap_subquery, where=" AND ".join(pe_conditions)),
            pe_params,
            as_dict=True,
        )
    )

    # --- Path B: Settlement JE for the credit JE (via Payment Ledger Entry) ---
    # PLE captures both directly-tagged settlement JEs (GL against_voucher set) and
    # those linked only via the Payment Reconciliation tool (PLE only, no GL against_voucher).
    je_params = dict(base_params)
    if from_date:
        je_params["from_date"] = from_date

    entries.extend(
        frappe.db.sql(
            """
            SELECT
                je_pl.account,
                ple.posting_date,
                '' AS fiscal_year,
                je_pl.account_currency,
                0 AS is_opening,
                (je_pl.debit  * ABS(ple.amount) / NULLIF(ar_ap.total_amount, 0)) AS debit,
                (je_pl.credit * ABS(ple.amount) / NULLIF(ar_ap.total_amount, 0)) AS credit,
                (je_pl.debit_in_account_currency  * ABS(ple.amount) / NULLIF(ar_ap.total_amount, 0)) AS debit_in_account_currency,
                (je_pl.credit_in_account_currency * ABS(ple.amount) / NULLIF(ar_ap.total_amount, 0)) AS credit_in_account_currency
            FROM `tabPayment Ledger Entry` ple
            INNER JOIN ({ar_ap_subquery}) ar_ap ON ar_ap.voucher_no = ple.against_voucher_no
            INNER JOIN `tabGL Entry` je_pl ON je_pl.voucher_no = ple.against_voucher_no
            WHERE ple.voucher_type = 'Journal Entry'
              AND ple.against_voucher_type = 'Journal Entry'
              AND ple.delinked = 0
              AND ple.amount < 0
              AND ple.company = %(company)s
              AND ple.posting_date <= %(to_date)s
              {from_date_cond}
              AND je_pl.account IN %(accounts)s
              AND je_pl.voucher_type = 'Journal Entry'
              AND je_pl.is_cancelled = 0
              AND ({je_pl_net}) > 0
            """.format(
                ar_ap_subquery=ar_ap_subquery,
                from_date_cond="AND ple.posting_date >= %(from_date)s" if from_date else "",
                je_pl_net=je_pl_net,
            ),
            je_params,
            as_dict=True,
        )
    )

    return entries


# ---------------------------------------------------------------------------
# Balance Sheet helpers
# ---------------------------------------------------------------------------


def _get_balance_sheet_cash_basis_entries(company, from_date, to_date, filters, accounts_by_name):
    """
    Get GL entries for balance sheet accounts with invoice entries scaled by
    the settlement ratio as of to_date.

    - Sales Invoice GL entries → scaled by (payments received / grand_total as of to_date)
    - Purchase Invoice GL entries → scaled by (payments made / grand_total as of to_date)
    - Credit-expense JE payable entries → scaled by JE settlement ratio (mirrors PI treatment)
    - All other GL entries → passed through unchanged (ratio = 1.0)
    """
    si_ratios = _get_invoice_settlement_ratios(company, to_date, "Sales Invoice")
    pi_ratios = _get_invoice_settlement_ratios(company, to_date, "Purchase Invoice")
    # Credit-expense JEs (DR Expense, CR Supplier Payable): scale the AP entry by settlement ratio
    je_expense_ratios = _get_je_credit_settlement_ratios(company, to_date, is_income=False)
    # Credit-income JEs (DR Customer Receivable, CR Income): scale the AR entry by collection ratio
    je_income_ratios = _get_je_credit_settlement_ratios(company, to_date, is_income=True)
    payable_accounts = frozenset(
        frappe.db.get_all("Account", filters={"company": company, "account_type": "Payable", "is_group": 0}, pluck="name")
    )
    receivable_accounts = frozenset(
        frappe.db.get_all("Account", filters={"company": company, "account_type": "Receivable", "is_group": 0}, pluck="name")
    )

    account_names = list(accounts_by_name.keys())
    if not account_names:
        return []

    conditions = [
        "gl.company = %(company)s",
        "gl.is_cancelled = 0",
        "gl.posting_date <= %(to_date)s",
        "gl.account IN %(accounts)s",
    ]
    params = {
        "company": company,
        "to_date": to_date,
        "accounts": tuple(account_names),
    }

    if from_date:
        conditions.append("gl.posting_date >= %(from_date)s")
        params["from_date"] = from_date

    _apply_gl_filter_conditions(conditions, params, filters)

    raw_entries = frappe.db.sql(
        """
        SELECT
            gl.account, gl.debit, gl.credit,
            gl.posting_date, gl.fiscal_year,
            gl.account_currency,
            gl.debit_in_account_currency, gl.credit_in_account_currency,
            gl.is_opening, gl.voucher_type, gl.voucher_no
        FROM `tabGL Entry` gl
        WHERE {where}
        """.format(where=" AND ".join(conditions)),
        params,
        as_dict=True,
    )

    result = []
    for gl in raw_entries:
        ratio = 1.0
        if gl.voucher_type == "Sales Invoice":
            ratio = si_ratios.get(gl.voucher_no, 0.0)
        elif gl.voucher_type == "Purchase Invoice":
            ratio = pi_ratios.get(gl.voucher_no, 0.0)
        elif gl.voucher_type == "Journal Entry":
            # Scale ALL entries in a credit JE (e.g. DR Office Equipment / CR Creditors)
            # by the payment ratio — not just the AP/AR leg — so unpaid asset purchases
            # don't appear on the balance sheet prematurely.
            if gl.voucher_no in je_expense_ratios:
                ratio = je_expense_ratios[gl.voucher_no]
            elif gl.voucher_no in je_income_ratios:
                ratio = je_income_ratios[gl.voucher_no]

        if ratio != 1.0:
            gl = frappe._dict(gl)
            gl.debit = flt(gl.debit) * ratio
            gl.credit = flt(gl.credit) * ratio
            gl.debit_in_account_currency = flt(gl.debit_in_account_currency) * ratio
            gl.credit_in_account_currency = flt(gl.credit_in_account_currency) * ratio

        result.append(gl)

    return result


def _get_je_credit_settlement_ratios(company, as_of_date, is_income=False):
    """
    Return {je_voucher_no: settled_ratio} for credit JEs.

    is_income=False → credit-expense JEs (DR Expense, CR Supplier Payable)
    is_income=True  → credit-income JEs  (DR Customer Receivable, CR Income)

    settled_ratio = total settled amount / total AR/AP amount in the original JE.
    Sources: PE References and JE against_voucher settlements.
    """
    party_type = "Customer" if is_income else "Supplier"
    ar_ap_type = "Receivable" if is_income else "Payable"

    # Fully-qualified column expressions (avoids "Column 'debit' is ambiguous" in multi-join SQL)
    if is_income:
        je_par_net = "je_par.debit - je_par.credit"    # AR debited in income credit JE
        je_gl_settle = "je_gl.credit - je_gl.debit"    # AR credited when collected
    else:
        je_par_net = "je_par.credit - je_par.debit"    # AP credited in expense credit JE
        je_gl_settle = "je_gl.debit - je_gl.credit"    # AP debited when paid

    ar_ap_rows = frappe.db.sql(
        f"""
        SELECT je_par.voucher_no, SUM({je_par_net}) AS total_amount
        FROM `tabGL Entry` je_par
        INNER JOIN tabAccount ar_ap_acc
            ON ar_ap_acc.name = je_par.account AND ar_ap_acc.account_type = %(ar_ap_type)s
        WHERE je_par.voucher_type = 'Journal Entry'
          AND je_par.is_cancelled = 0
          AND je_par.company = %(company)s
          AND je_par.party_type = %(party_type)s
          AND je_par.party IS NOT NULL
          AND je_par.party != ''
          AND ({je_par_net}) > 0
        GROUP BY je_par.voucher_no
        """,
        {"company": company, "ar_ap_type": ar_ap_type, "party_type": party_type},
        as_dict=True,
    )
    if not ar_ap_rows:
        return {}

    je_names = tuple(r.voucher_no for r in ar_ap_rows)

    # Use Payment Ledger Entry as the authoritative settlement source.
    # PLE captures all settlement types (PE, JE with direct GL tag, JE via
    # Payment Reconciliation) so a single query replaces the separate
    # PE-Reference and GL against_voucher queries that would miss
    # Payment-Reconciliation-only links.
    ple_rows = frappe.db.sql(
        """
        SELECT ple.against_voucher_no, SUM(ABS(ple.amount)) AS settled
        FROM `tabPayment Ledger Entry` ple
        WHERE ple.against_voucher_type = 'Journal Entry'
          AND ple.against_voucher_no IN %(je_names)s
          AND ple.delinked = 0
          AND ple.posting_date <= %(as_of_date)s
          AND ple.amount < 0
        GROUP BY ple.against_voucher_no
        """,
        {"as_of_date": as_of_date, "je_names": je_names},
        as_dict=True,
    )

    total_amount = {r.voucher_no: flt(r.total_amount) for r in ar_ap_rows}
    ple_settled = {r.against_voucher_no: flt(r.settled) for r in ple_rows}

    ratios = {}
    for je_name, amount in total_amount.items():
        if not amount:
            ratios[je_name] = 1.0
            continue
        ratios[je_name] = min(ple_settled.get(je_name, 0.0) / amount, 1.0)

    return ratios


def _get_invoice_settlement_ratios(company, as_of_date, invoice_doctype):
    """
    Return {invoice_name: settled_ratio} where settled_ratio is in [0, 1].

    settled_ratio = total cash received/paid / invoice grand_total as of as_of_date.
    Sources:
    - Payment Entry Reference allocations
    - Journal Entry against_voucher settlements
    - is_paid=1 Purchase Invoices (paid at invoice time, ratio = 1.0)
    - is_pos=1 Sales Invoices with embedded POS payment (paid_amount / grand_total)
    """
    invoice_table = "tabSales Invoice" if invoice_doctype == "Sales Invoice" else "tabPurchase Invoice"
    ar_ap_type = "Receivable" if invoice_doctype == "Sales Invoice" else "Payable"
    is_si = invoice_doctype == "Sales Invoice"

    # Payment Entry Reference allocations; also fetch self-payment fields
    extra_fields = "inv.paid_amount, inv.is_pos," if is_si else "inv.is_paid,"
    extra_group = "inv.paid_amount, inv.is_pos," if is_si else "inv.is_paid,"

    per_rows = frappe.db.sql(
        f"""
        SELECT inv.name, inv.grand_total, {extra_fields}
               COALESCE(pe_sum.total_pe_paid, 0) AS total_pe_paid
        FROM `{invoice_table}` inv
        LEFT JOIN (
            SELECT per.reference_name, SUM(per.allocated_amount) AS total_pe_paid
            FROM `tabPayment Entry Reference` per
            INNER JOIN `tabPayment Entry` pe
                ON pe.name = per.parent
                AND pe.posting_date <= %(as_of_date)s
                AND pe.docstatus = 1
            WHERE per.reference_doctype = %(invoice_doctype)s
            GROUP BY per.reference_name
        ) pe_sum ON pe_sum.reference_name = inv.name
        WHERE inv.docstatus = 1
          AND inv.company = %(company)s
        """,
        {"company": company, "as_of_date": as_of_date, "invoice_doctype": invoice_doctype},
        as_dict=True,
    )

    # Journal Entry settlements via Payment Ledger Entry (PLE).
    # PLE is the authoritative source in ERPNext v15 for all reconciliation links —
    # it captures both JEs with GL against_voucher set directly AND JEs reconciled
    # via the Payment Reconciliation tool (which creates PLE but does not tag GL against_voucher).
    inv_names = tuple(row.name for row in per_rows)
    je_rows = []
    if inv_names:
        je_rows = frappe.db.sql(
            """
            SELECT ple.against_voucher_no AS name, SUM(ABS(ple.amount)) AS total_paid
            FROM `tabPayment Ledger Entry` ple
            WHERE ple.voucher_type = 'Journal Entry'
              AND ple.against_voucher_type = %(invoice_doctype)s
              AND ple.against_voucher_no IN %(inv_names)s
              AND ple.delinked = 0
              AND ple.posting_date <= %(as_of_date)s
              AND ple.amount < 0
            GROUP BY ple.against_voucher_no
            """,
            {"as_of_date": as_of_date, "inv_names": inv_names, "invoice_doctype": invoice_doctype},
            as_dict=True,
        )

    je_paid = {row.name: flt(row.total_paid) for row in je_rows}

    ratios = {}
    for row in per_rows:
        grand_total = flt(row.grand_total)
        if not grand_total:
            ratios[row.name] = 1.0
            continue

        # is_paid=1 PI: fully paid at invoice time
        if not is_si and row.get("is_paid"):
            ratios[row.name] = 1.0
            continue

        pe_total = flt(row.total_pe_paid)
        je_total = je_paid.get(row.name, 0.0)

        # is_pos=1 SI: add embedded POS payment; subsequent PE handles the outstanding
        pos_total = flt(row.get("paid_amount", 0)) if is_si and row.get("is_pos") else 0.0

        total = pe_total + je_total + pos_total
        ratios[row.name] = min(total / abs(grand_total), 1.0)

    return ratios


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------


def _apply_gl_filter_conditions(conditions, params, filters):
    """Apply standard dimension and finance book filters to GL entry WHERE conditions."""
    if not filters:
        return

    if filters.get("cost_center"):
        cost_centers = get_cost_centers_with_children(filters.cost_center)
        conditions.append("gl.cost_center IN %(cost_centers)s")
        params["cost_centers"] = tuple(cost_centers)

    if filters.get("project"):
        projects = (
            filters.project if isinstance(filters.project, list) else frappe.parse_json(filters.project)
        )
        conditions.append("gl.project IN %(projects)s")
        params["projects"] = tuple(projects)

    _apply_finance_book_condition("gl", conditions, params, filters)


def _apply_payment_filter_conditions(conditions, params, filters):
    """Apply cost_center / project filters against the Payment Entry table."""
    if not filters:
        return

    if filters.get("cost_center"):
        cost_centers = get_cost_centers_with_children(filters.cost_center)
        conditions.append("pe.cost_center IN %(pe_cost_centers)s")
        params["pe_cost_centers"] = tuple(cost_centers)

    if filters.get("project"):
        projects = (
            filters.project if isinstance(filters.project, list) else frappe.parse_json(filters.project)
        )
        conditions.append("pe.project IN %(pe_projects)s")
        params["pe_projects"] = tuple(projects)


def _apply_finance_book_condition(table_alias, conditions, params, filters):
    """Add finance book filter to conditions list."""
    if not filters:
        return

    if filters.get("include_default_book_entries"):
        company_fb = frappe.get_cached_value("Company", filters.get("company"), "default_finance_book")
        finance_books = {cstr(filters.get("finance_book", "")), cstr(company_fb), ""}
        conditions.append(f"({table_alias}.finance_book IN %(finance_books)s OR {table_alias}.finance_book IS NULL)")
        params["finance_books"] = tuple(finance_books)
    else:
        finance_books = {cstr(filters.get("finance_book", "")), ""}
        conditions.append(f"({table_alias}.finance_book IN %(finance_books)s OR {table_alias}.finance_book IS NULL)")
        params["finance_books"] = tuple(finance_books)
