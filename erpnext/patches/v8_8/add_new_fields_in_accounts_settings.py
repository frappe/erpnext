from __future__ import unicode_literals
import frappe


def execute():
	frappe.db.sql(
		"INSERT INTO `tabSingles` (`doctype`, `field`, `value`) VALUES ('Accounts Settings', 'allow_stale', '1'), "
		"('Accounts Settings', 'stale_days', '1')"
	)
