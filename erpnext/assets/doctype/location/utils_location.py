# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

@frappe.whitelist()
def get_total_location():
    no_data = [[0]]
    try:
        # Get the total of all locations in square meters
        total_location = frappe.db.sql('''SELECT sum(round(area, 3)) FROM `tabLocation` WHERE is_group = 0''')

        return total_location
    except:
        return no_data
