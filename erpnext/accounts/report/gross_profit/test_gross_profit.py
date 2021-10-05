from __future__ import unicode_literals
from random import uniform

import unittest

import frappe
from frappe.utils import today, flt, cint

from erpnext.accounts.utils import get_balance_on
from erpnext.selling.doctype.sales_order.test_sales_order import (
    make_sales_order as make_so,
    make_delivery_note as make_dn_from_so,
    make_sales_invoice as make_si_from_so
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note as make_dn_from_si
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice as make_si_from_dn
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.accounts.report.gross_profit.gross_profit import execute

test_company = "_Test Company with perpetual inventory"

class TestGrossProfit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.db.sql("delete from `tabSales Invoice` where company=%s", test_company)
        frappe.db.sql("delete from `tabGL Entry` where company=%s", test_company)
        frappe.db.sql("delete from `tabStock Ledger Entry` where company=%s", test_company)
        
        filters = frappe._dict({
            "company": test_company,
            "from_date": today(),
            "to_date": today(),
            "group_by": "Item Code"
        })

        generate_expected_data()
        cls.income = flt(abs(get_balance_on(account=frappe.get_cached_value("Company", test_company, "default_income_account"))), 2)
        cls.cogs = flt(get_balance_on(account=frappe.get_cached_value("Company", test_company, "default_expense_account")), 2)
        cls.gross_profit = flt(cls.income - cls.cogs, 2)
        cls.gross_profit_percentage = flt(100 * (cls.gross_profit / cls.income), 3)
        report = execute(filters)
        cls.totals = report[-1][-1]

    def test_gross_profit_selling_amount(self):
        self.assertEqual(self.income, self.totals[-5], "Incorrect selling amount got {0} but expected {1}".format(frappe.format(self.totals[-5], "Currency"), frappe.format(self.income, "Currency")))
    
    def test_gross_profit_buying_amount(self):
        self.assertEqual(self.cogs, self.totals[-4], "Incorrect buying amount got {0} but expected {1}".format(frappe.format(self.totals[-4], "Currency"), frappe.format(self.cogs, "Currency")))
    
    def test_gross_profit(self):
        self.assertEqual(self.gross_profit, self.totals[-3], "Incorrect gross profit amount got {0} but expected {1}".format(frappe.format(self.totals[-3], "Currency"), frappe.format(self.gross_profit, "Currency")))
    
    def test_gross_profit_percentage(self):
        self.assertEqual(self.gross_profit_percentage, self.totals[-2], "Incorrect gross profit percentage got {0} but expected {1}".format(frappe.format(self.totals[-2], "Percentage"), frappe.format(self.gross_profit_percentage, "Percentage")))


def generate_expected_data():
    def make_so_against_dn_and_si():
        so = make_so(qty = 5, company=test_company, warehouse="Stores - TCP1")
        make_dn_from_so(so.name).submit()
        make_si_from_so(so.name).submit()
        
    def make_so_against_dn_against_si():
        so = make_so(qty = 5, company=test_company, warehouse="Stores - TCP1")
        dn = make_dn_from_so(so.name)
        dn.submit()
        make_si_from_dn(dn.name).submit()

    def make_so_against_si_against_dn():
        so = make_so(qty = 5, company=test_company, warehouse="Stores - TCP1")
        si = make_si_from_so(so.name)
        si.submit()
        make_dn_from_si(si.name).submit()

    
    for i in range(6):
        make_stock_entry(qty=6 * (i + 1), rate=uniform(1.5, 99.5), to_warehouse="Stores - TCP1", purpose="Material Receipt", company=test_company)

        if i == 0 or i == 3:
            make_so_against_dn_and_si()
        elif i == 1 or i == 4:
            make_so_against_si_against_dn()
        else:
            make_so_against_dn_against_si()
        
