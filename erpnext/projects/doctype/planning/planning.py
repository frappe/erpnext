# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

# class Planning(Document):
# 	pass




# @frappe.whitelist()
# def get_events(start, end, filters=None):
# 	"""Returns events for Gantt / Calendar view rendering.

# 	:param start: Start date-time.
# 	:param end: End date-time.
# 	:param filters: Filters (JSON).
# 	"""
# 	from frappe.desk.calendar import get_event_conditions
# 	conditions = get_event_conditions("Planning", filters)

# 	data = frappe.db.sql("""select name, start_date, end_date,
# 		subject, status, project from `tabPlanning`
# 		where ((ifnull(start_date, '0000-00-00')!= '0000-00-00') \
# 				and (start_date <= %(end)s) \
# 			or ((ifnull(end_date, '0000-00-00')!= '0000-00-00') \
# 				and end_date >= %(start)s))
# 		{conditions}""".format(conditions=conditions), {
# 			"start": start,
# 			"end": end
# 		}, as_dict=True, update={"allDay": 0})

# 	return data


class Planning(Document):
    def get_events(start, end, filters=None):
        frappe.msgprint('tst')
        """Returns events for Gantt / Calendar view rendering.

        :param start: Start date-time.
        :param end: End date-time.
        :param filters: Filters (JSON).
        """

        data = frappe.db.sql("""select name, start_date, end_date,
            subject, status, project from `tabPlanning`
            """, as_dict=True, update={"allDay": 0})

        return data
