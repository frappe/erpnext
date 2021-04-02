# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	print_format_mapper = {
		'India': ['GST POS Invoice', 'GST Tax Invoice'],
		'Saudi Arabia': ['Simplified Tax Invoice', 'Detailed Tax Invoice', 'Tax Invoice'],
		'United Arab Emirates': ['Simplified Tax Invoice', 'Detailed Tax Invoice', 'Tax Invoice']
	}

	frappe.db.sql(""" update `tabPrint Format` set disabled = 1 where name
		in ('GST POS Invoice', 'GST Tax Invoice', 'Simplified Tax Invoice', 'Detailed Tax Invoice')""")

	for d in frappe.get_all('Company', fields = ["country"],
		filters={'country': ('in', ['India', 'Saudi Arabia', 'United Arab Emirates'])}):
		if print_format_mapper.get(d.country):
			print_formats = print_format_mapper.get(d.country)
			frappe.db.sql(""" update `tabPrint Format` set disabled = 0
				where name in (%s)""" % ", ".join(["%s"]*len(print_formats)), tuple(print_formats))