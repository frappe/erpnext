# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("setup", "doctype", "target_detail")
	frappe.reload_doc("core", "doctype", "prepared_report")

	for d in ["Sales Person", "Sales Partner", "Territory"]:
		frappe.db.sql(
			"""
            UPDATE `tab{child_doc}`, `tab{parent_doc}`
            SET
                `tab{child_doc}`.distribution_id = `tab{parent_doc}`.distribution_id
            WHERE
                `tab{child_doc}`.parent = `tab{parent_doc}`.name
                and `tab{parent_doc}`.distribution_id is not null and `tab{parent_doc}`.distribution_id != ''
        """.format(
				parent_doc=d, child_doc="Target Detail"
			)
		)

	frappe.delete_doc("Report", "Sales Partner-wise Transaction Summary")
	frappe.delete_doc("Report", "Sales Person Target Variance Item Group-Wise")
	frappe.delete_doc("Report", "Territory Target Variance Item Group-Wise")
