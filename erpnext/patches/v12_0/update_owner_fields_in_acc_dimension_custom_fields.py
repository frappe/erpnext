from __future__ import unicode_literals

import frappe

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_doctypes_with_dimensions,
)


def execute():
	accounting_dimensions = frappe.db.sql("""select fieldname from
		`tabAccounting Dimension`""", as_dict=1)

	doclist = get_doctypes_with_dimensions()

	for dimension in accounting_dimensions:
		frappe.db.sql("""
			UPDATE `tabCustom Field`
			SET owner = 'Administrator'
			WHERE fieldname = %s
			AND dt IN (%s)""" %			#nosec
			('%s', ', '.join(['%s']* len(doclist))), tuple([dimension.fieldname] + doclist))
