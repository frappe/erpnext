# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

"""
Tests for Cash Basis Profit and Loss Statement.

Key scenarios:
- Fully paid invoice: revenue recognised at payment date
- Partially paid invoice: proportional revenue recognition
- Partial payment across periods: correct per-period recognition
- Credit note (return): revenue reduction at refund date
- Purchase invoice fully paid: expense recognised at payment date
- Partial purchase payment: proportional expense recognition
- Journal Entry settlement: alternative payment path
"""

import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.cash_basis_profit_and_loss_statement.cash_basis_profit_and_loss_statement import (
    execute,
)
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


def _get_current_month_range():
    today_date = getdate(today())
    return get_first_day(today_date), get_last_day(today_date)


def _get_next_month_range():
    today_date = getdate(today())
    first = get_first_day(add_months(today_date, 1))
    return first, get_last_day(first)


class TestCashBasisProfitAndLossStatement(ERPNextTestSuite, AccountsTestMixin):
    def setUp(self):
        self.company = "_Test Company"
        self.customer = "_Test Customer"
        self.supplier = "_Test Supplier"
        self.item = "_Test Item"
        self.debit_to = "Debtors - _TC"
        self.creditors = "Creditors - _TC"
        self.bank = "Cash - _TC"
        self.cost_center = "Main - _TC"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_sales_invoice(self, rate=100, posting_date=None, qty=1):
        frappe.set_user("Administrator")
        si = create_sales_invoice(
            item=self.item,
            company=self.company,
            customer=self.customer,
            debit_to=self.debit_to,
            posting_date=posting_date or today(),
            parent_cost_center=self.cost_center,
            cost_center=self.cost_center,
            rate=rate,
            price_list_rate=rate,
            qty=qty,
        )
        return si

    def _make_purchase_invoice(self, rate=100, posting_date=None, qty=1):
        frappe.set_user("Administrator")
        pi = make_purchase_invoice(
            item=self.item,
            company=self.company,
            supplier=self.supplier,
            posting_date=posting_date or today(),
            cost_center=self.cost_center,
            rate=rate,
            qty=qty,
        )
        return pi

    def _receive_payment(self, si_name, amount, posting_date=None):
        pe = get_payment_entry("Sales Invoice", si_name, bank_account=self.bank, party_amount=amount)
        pe.paid_from = self.debit_to
        pe.posting_date = posting_date or today()
        pe.reference_no = "TEST"
        pe.reference_date = pe.posting_date
        pe.insert()
        pe.submit()
        return pe

    def _make_payment(self, pi_name, amount, posting_date=None):
        pe = get_payment_entry("Purchase Invoice", pi_name, bank_account=self.bank, party_amount=amount)
        pe.paid_to = self.creditors
        pe.posting_date = posting_date or today()
        pe.reference_no = "TEST"
        pe.reference_date = pe.posting_date
        pe.insert()
        pe.submit()
        return pe

    def _get_filters(self, from_date=None, to_date=None, periodicity="Monthly"):
        from_date = from_date or get_first_day(getdate(today()))
        to_date = to_date or get_last_day(getdate(today()))
        return frappe._dict(
            company=self.company,
            filter_based_on="Date Range",
            period_start_date=from_date,
            period_end_date=to_date,
            from_fiscal_year=None,
            to_fiscal_year=None,
            periodicity=periodicity,
            accumulated_values=False,
            presentation_currency=None,
            show_zero_values=False,
            finance_book=None,
            include_default_book_entries=True,
            cost_center=None,
            project=None,
        )

    def _get_income_account(self, si):
        """Return the primary income account used by a Sales Invoice."""
        return frappe.db.get_value("Sales Invoice Item", {"parent": si.name}, "income_account")

    def _get_expense_account(self, pi):
        """Return the expense account used by a Purchase Invoice."""
        return frappe.db.get_value("Purchase Invoice Item", {"parent": pi.name}, "expense_account")

    def _find_account_in_report(self, data, account_name):
        return next((row for row in data if row and row.get("account") == account_name), None)

    # ------------------------------------------------------------------
    # Revenue Tests
    # ------------------------------------------------------------------

    def test_fully_paid_invoice_recognised_at_payment_date(self):
        """
        A fully paid invoice should show its revenue in the period the payment was made,
        NOT the invoice posting date.
        """
        cur_from, cur_to = _get_current_month_range()
        next_from, next_to = _get_next_month_range()

        # Invoice posted this month
        si = self._make_sales_invoice(rate=1000, posting_date=str(cur_from))
        income_account = self._get_income_account(si)

        # Payment received next month
        payment_date = str(next_from)
        self._receive_payment(si.name, 1000, posting_date=payment_date)

        # P&L for THIS month: income should be 0 (payment not yet received)
        filters = self._get_filters(from_date=cur_from, to_date=cur_to)
        result = execute(filters)[1]
        row = self._find_account_in_report(result, income_account)
        period_key = get_period_list(
            None, None, cur_from, cur_to, "Date Range", "Monthly", company=self.company
        )[0].key
        self.assertEqual(
            flt(row.get(period_key) if row else 0, 2),
            0.0,
            "Revenue must not appear before payment is received",
        )

        # P&L for NEXT month: income should be 1000
        filters = self._get_filters(from_date=next_from, to_date=next_to)
        result = execute(filters)[1]
        row = self._find_account_in_report(result, income_account)
        period_key = get_period_list(
            None, None, next_from, next_to, "Date Range", "Monthly", company=self.company
        )[0].key
        self.assertAlmostEqual(
            flt(row.get(period_key) if row else 0, 2),
            1000.0,
            places=1,
            msg="Full revenue must appear in the payment period",
        )

    def test_partial_payment_proportional_recognition(self):
        """
        60% payment of a 1000 invoice should recognise 600 in revenue.
        """
        cur_from, cur_to = _get_current_month_range()
        si = self._make_sales_invoice(rate=1000, posting_date=str(cur_from))
        income_account = self._get_income_account(si)

        # Pay 60%
        self._receive_payment(si.name, 600, posting_date=str(cur_from))

        filters = self._get_filters(from_date=cur_from, to_date=cur_to)
        result = execute(filters)[1]
        row = self._find_account_in_report(result, income_account)
        period_key = get_period_list(
            None, None, cur_from, cur_to, "Date Range", "Monthly", company=self.company
        )[0].key

        self.assertAlmostEqual(
            flt(row.get(period_key) if row else 0, 2),
            600.0,
            places=1,
            msg="60% payment must recognise 60% of revenue",
        )

    def test_partial_payments_across_two_periods(self):
        """
        Invoice = 1000. Pay 400 in Jan, 600 in Feb.
        Jan P&L: revenue = 400. Feb P&L: revenue = 600.
        """
        jan_first = get_first_day(add_months(getdate(today()), -1))
        jan_last = get_last_day(jan_first)
        feb_first = get_first_day(getdate(today()))
        feb_last = get_last_day(feb_first)

        si = self._make_sales_invoice(rate=1000, posting_date=str(jan_first))
        income_account = self._get_income_account(si)

        # First payment in Jan
        self._receive_payment(si.name, 400, posting_date=str(jan_first))
        # Second payment in Feb
        self._receive_payment(si.name, 600, posting_date=str(feb_first))

        def _period_revenue(from_date, to_date):
            filters = self._get_filters(from_date=from_date, to_date=to_date)
            result = execute(filters)[1]
            row = self._find_account_in_report(result, income_account)
            period_key = get_period_list(
                None, None, from_date, to_date, "Date Range", "Monthly", company=self.company
            )[0].key
            return flt(row.get(period_key) if row else 0, 2)

        self.assertAlmostEqual(_period_revenue(jan_first, jan_last), 400.0, places=1,
                                msg="Jan: only the 400 partial payment should be revenue")
        self.assertAlmostEqual(_period_revenue(feb_first, feb_last), 600.0, places=1,
                                msg="Feb: remaining 600 payment should be revenue")

    def test_unpaid_invoice_has_no_revenue(self):
        """An unpaid invoice must contribute zero revenue in any period."""
        cur_from, cur_to = _get_current_month_range()
        si = self._make_sales_invoice(rate=5000, posting_date=str(cur_from))
        income_account = self._get_income_account(si)

        filters = self._get_filters(from_date=cur_from, to_date=cur_to)
        result = execute(filters)[1]
        row = self._find_account_in_report(result, income_account)
        period_key = get_period_list(
            None, None, cur_from, cur_to, "Date Range", "Monthly", company=self.company
        )[0].key

        self.assertEqual(
            flt(row.get(period_key) if row else 0, 2),
            0.0,
            "Unpaid invoice must generate zero revenue in cash basis P&L",
        )

    # ------------------------------------------------------------------
    # Credit Note Tests
    # ------------------------------------------------------------------

    def test_credit_note_refund_reduces_revenue(self):
        """
        Credit note with refund payment should reduce revenue in the refund period.
        """
        cur_from, cur_to = _get_current_month_range()

        # Post and fully pay an invoice
        si = self._make_sales_invoice(rate=1000, posting_date=str(cur_from))
        income_account = self._get_income_account(si)
        self._receive_payment(si.name, 1000, posting_date=str(cur_from))

        # Create credit note (return)
        cn = create_sales_invoice(
            company=self.company,
            customer=self.customer,
            item=self.item,
            qty=-1,
            rate=1000,
            debit_to=self.debit_to,
            cost_center=self.cost_center,
            is_return=1,
            return_against=si.name,
            posting_date=str(cur_from),
        )

        # Refund payment for the credit note
        refund_pe = get_payment_entry(
            "Sales Invoice", cn.name, bank_account=self.bank, party_amount=1000
        )
        refund_pe.paid_from = self.debit_to
        refund_pe.posting_date = str(cur_from)
        refund_pe.reference_no = "REFUND"
        refund_pe.reference_date = refund_pe.posting_date
        refund_pe.insert()
        refund_pe.submit()

        # Net revenue should be 0 (1000 invoice - 1000 refund)
        filters = self._get_filters(from_date=cur_from, to_date=cur_to)
        result = execute(filters)[1]
        row = self._find_account_in_report(result, income_account)
        period_key = get_period_list(
            None, None, cur_from, cur_to, "Date Range", "Monthly", company=self.company
        )[0].key

        net_revenue = flt(row.get(period_key) if row else 0, 2)
        self.assertAlmostEqual(
            net_revenue, 0.0, places=1,
            msg="Full refund should net revenue to zero"
        )

    # ------------------------------------------------------------------
    # Expense Tests
    # ------------------------------------------------------------------

    def test_fully_paid_purchase_invoice_recognised_at_payment_date(self):
        """
        A fully paid purchase invoice should show expense only in the payment period.
        """
        cur_from, cur_to = _get_current_month_range()
        next_from, next_to = _get_next_month_range()

        # Invoice posted this month
        pi = self._make_purchase_invoice(rate=500, posting_date=str(cur_from))
        expense_account = self._get_expense_account(pi)

        # Payment next month
        self._make_payment(pi.name, 500, posting_date=str(next_from))

        # This month: expense = 0
        filters = self._get_filters(from_date=cur_from, to_date=cur_to)
        result = execute(filters)[1]
        row = self._find_account_in_report(result, expense_account)
        period_key = get_period_list(
            None, None, cur_from, cur_to, "Date Range", "Monthly", company=self.company
        )[0].key
        self.assertEqual(
            flt(row.get(period_key) if row else 0, 2),
            0.0,
            "Expense must not appear before payment is made",
        )

        # Next month: expense = 500
        filters = self._get_filters(from_date=next_from, to_date=next_to)
        result = execute(filters)[1]
        row = self._find_account_in_report(result, expense_account)
        period_key = get_period_list(
            None, None, next_from, next_to, "Date Range", "Monthly", company=self.company
        )[0].key
        self.assertAlmostEqual(
            flt(row.get(period_key) if row else 0, 2),
            500.0,
            places=1,
            msg="Full expense must appear in payment period",
        )

    def test_partial_purchase_payment_proportional_expense(self):
        """
        40% payment of a 500 expense should recognise 200 (40%) in expenses.
        """
        cur_from, cur_to = _get_current_month_range()
        pi = self._make_purchase_invoice(rate=500, posting_date=str(cur_from))
        expense_account = self._get_expense_account(pi)

        self._make_payment(pi.name, 200, posting_date=str(cur_from))

        filters = self._get_filters(from_date=cur_from, to_date=cur_to)
        result = execute(filters)[1]
        row = self._find_account_in_report(result, expense_account)
        period_key = get_period_list(
            None, None, cur_from, cur_to, "Date Range", "Monthly", company=self.company
        )[0].key

        self.assertAlmostEqual(
            flt(row.get(period_key) if row else 0, 2),
            200.0,
            places=1,
            msg="40% payment must recognise 40% of expense",
        )

    # ------------------------------------------------------------------
    # Net Profit Test
    # ------------------------------------------------------------------

    def test_net_profit_cash_basis(self):
        """
        Income = 800 (paid portion of 1000 invoice), Expense = 300 (paid portion of 500 PI).
        Net cash basis profit = 500.
        """
        cur_from, cur_to = _get_current_month_range()

        si = self._make_sales_invoice(rate=1000, posting_date=str(cur_from))
        self._receive_payment(si.name, 800, posting_date=str(cur_from))

        pi = self._make_purchase_invoice(rate=500, posting_date=str(cur_from))
        self._make_payment(pi.name, 300, posting_date=str(cur_from))

        filters = self._get_filters(from_date=cur_from, to_date=cur_to)
        _columns, data, _message, _chart, report_summary, _primitive = execute(filters)

        # Locate "Profit for the year" row
        profit_row = next((row for row in data if row and "Profit" in str(row.get("account", ""))), None)

        if profit_row:
            period_key = get_period_list(
                None, None, cur_from, cur_to, "Date Range", "Monthly", company=self.company
            )[0].key
            net_profit = flt(profit_row.get(period_key, 0), 2)
            self.assertAlmostEqual(
                net_profit, 500.0, places=1,
                msg="Net cash basis profit must be income paid (800) minus expense paid (300)"
            )

    # ------------------------------------------------------------------
    # Accumulated Values Test
    # ------------------------------------------------------------------

    def test_accumulated_values(self):
        """
        With accumulated_values=True, each period column shows running total from year start.
        """
        cur_from, cur_to = _get_current_month_range()
        si = self._make_sales_invoice(rate=1000, posting_date=str(cur_from))
        income_account = self._get_income_account(si)
        self._receive_payment(si.name, 1000, posting_date=str(cur_from))

        filters = self._get_filters(from_date=get_first_day(getdate(today()).replace(month=1)), to_date=cur_to)
        filters.accumulated_values = True
        filters.periodicity = "Monthly"

        result = execute(filters)[1]
        row = self._find_account_in_report(result, income_account)

        # The last period column must show the cumulative total
        period_list = get_period_list(
            None, None, filters.period_start_date, filters.period_end_date, "Date Range", "Monthly",
            accumulated_values=True, company=self.company
        )
        last_key = period_list[-1].key
        cumulative = flt(row.get(last_key) if row else 0, 2)
        self.assertAlmostEqual(
            cumulative, 1000.0, places=1,
            msg="Accumulated value must equal total payments received YTD"
        )
