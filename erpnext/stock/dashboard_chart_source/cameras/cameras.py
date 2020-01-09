from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import add_to_date, date_diff, getdate, nowdate, get_last_day, formatdate
from erpnext.accounts.report.general_ledger.general_ledger import execute
from frappe.core.page.dashboard.dashboard import cache_source, get_from_date_from_timespan
from frappe.desk.doctype.dashboard_chart.dashboard_chart import get_period_ending

from frappe.utils.nestedset import get_descendants_of

@frappe.whitelist()
@cache_source
def get(chart_name = None, chart = None, no_cache = None, from_date = None, to_date = None):
        if chart_name:
                chart = frappe.get_doc('Dashboard Chart', chart_name)
        else:
                chart = frappe._dict(frappe.parse_json(chart))
        timespan = chart.timespan

        if chart.timespan == 'Select Date Range':
                from_date = chart.from_date
                to_date = chart.to_date

        timegrain = chart.time_interval
        filters = frappe.parse_json(chart.filters_json)

        account = filters.get("serial_no")
        company = filters.get("company")

        if not serial_no and chart:
                frappe.throw(_("Account is not set for the dashboard chart {0}").format(chart))

        if not to_date:
                to_date = nowdate()
        if not from_date:
                if timegrain in ('Monthly', 'Quarterly'):
                        from_date = get_from_date_from_timespan(to_date, timespan)

        # fetch dates to plot
        dates = get_dates_from_timegrain(from_date, to_date, timegrain)

        # get all the entries for this account and its descendants
        gl_entries = get_gl_entries(serial_no, get_period_ending(to_date, timegrain))

        # compile balance values
        result = build_result(serial_no, dates, gl_entries)

        return {
                "labels": [formatdate(r[0].strftime('%Y-%m-%d')) for r in result],
                "datasets": [{
                        "name": serial_no,
                        "values": [r[1] for r in result]
                }]
        }

