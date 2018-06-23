# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	item_numeric_attributes = frappe.db.sql("""
		select name, numeric_values, from_range, to_range, increment
		from `tabItem Attribute`
		where numeric_values = 1
	""", as_dict=1)

	for d in item_numeric_attributes:
		frappe.db.sql("""
			update `tabItem Variant Attribute`
			set
				from_range = CASE
					WHEN from_range = 0 THEN %(from_range)s
					ELSE from_range
					END,
				to_range = CASE
					WHEN to_range = 0 THEN %(to_range)s
					ELSE to_range
					END,
				increment = CASE
					WHEN increment = 0 THEN %(increment)s
					ELSE increment
					END,
				numeric_values = %(numeric_values)s
			where
				attribute = %(name)s
				and exists(select name from tabItem 
					where name=`tabItem Variant Attribute`.parent and has_variants=1)
		""", d)