# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from itertools import groupby
from operator import itemgetter
import frappe
from frappe.utils import add_to_date, date_diff, getdate, nowdate
from erpnext.accounts.report.general_ledger.general_ledger import execute


def get(filters=None):
    filters = frappe._dict({
        "company": "Gadget Technologies Pvt. Ltd.",
        "from_date": get_from_date_from_timespan(filters.get("timespan")),
        "to_date": "2020-12-12",
        "account": "Cash - GTPL",
        "group_by": "Group by Voucher (Consolidated)"
    })
    report_columns, report_results = execute(filters=filters)

    interesting_fields = ["posting_date", "balance"]

    columns = [column for column in report_columns if column["fieldname"] in interesting_fields]

    _results = []
    for row in report_results[1:-2]:
        _results.append([row[key] for key in interesting_fields])

    grouped_results = groupby(_results, key=itemgetter(0))

    results = [list(values)[-1] for key, values in grouped_results]

    results = add_missing_dates(results, from_date, to_date)

    return {
        "labels": [result[0] for result in results],
        "datasets": [{
            "name": "Cash - GTPL",
            "values": [result[1] for result in results]
        }]
    }

def get_from_date_from_timespan(timespan):
    days = months = years = 0
    if "Last Week" == timespan:
        days = -7
    if "Last Month" == timespan:
        months = -1
    elif "Last Quarter" == timespan:
        months = -3
    elif "Last Year" == timespan:
        years = -1
    return add_to_date(None, years=years, months=months, days=days,
        as_string=True, as_datetime=True)

def add_missing_dates(incomplete_results, from_date, to_date):
    dates = [r[0] for r in incomplete_results]
    day_count = date_diff(to_date, from_date)

    results_dict = dict(incomplete_results)
    last_date, last_balance = incomplete_results[0]
    results = []
    for date in (add_to_date(getdate(from_date), days=n) for n in range(day_count + 1)):
        if date in results_dict:
            last_date = date
            last_balance = results_dict[date]
        results.append([date, last_balance])
    return results
