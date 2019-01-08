# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from itertools import groupby
from operator import itemgetter
import frappe
from erpnext.accounts.report.general_ledger.general_ledger import execute


def get():
    filters = frappe._dict({
        "company": "Gadget Technologies Pvt. Ltd.",
        "from_date": "2000-01-01",
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

    return {
        "labels": [result[0] for result in results],
        "datasets": [{
            "name": "Cash - GTPL",
            "values": [result[1] for result in results]
        }]
    }
