# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.utils import get_fiscal_year
from erpnext.accounts.doctype.fixed_asset_account.depreciation_report import get_report_data

def execute(filters=None):
    data = []
    columns = []
    finyrfrom, finyrto = get_fiscal_year(fiscal_year = filters["fiscal_year"])[1:]
    data = get_report_data(financial_year_from = str(finyrfrom), financial_year_to = str(finyrto), company = filters["company"])


    columns = ["FIXED ASSET NAME",
               "FIXED ASSET ACCOUNT",
               "RATE OF DEPRECIATION",
               "COST AS ON "+str(finyrfrom),
               "PURCHASES",
               "SALES",
               "CLOSING COST "+str(finyrto),
               "DEPRECIATION AS ON "+str(finyrfrom),
               "DEPRECIATION PROVIDED ON OPENING FOR CUR YR",
               "DEPRECIATION PROVIDED ON PURCHASE FOR CUR YR",
               "TOTAL DEPRECIATION FOR CUR YR",
               "WRITTEN_BACK",
               "TOTAL ACCUMULATED DEPRECIATION AS ON "+str(finyrto)]

    return columns, data
