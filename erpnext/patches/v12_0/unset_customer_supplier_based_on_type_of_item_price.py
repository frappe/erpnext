from __future__ import unicode_literals
import frappe


def execute():
    """
    set proper customer and supplier details for item price
    based on selling and buying values
    """

    # update for selling
    frappe.db.sql(
        """UPDATE `tabItem Price`
        SET `reference` = `customer`, `supplier` = NULL
        WHERE `selling` = 1
        AND `buying` = 0
        AND (`supplier` IS NOT NULL OR `supplier` = '')
        AND `price_list` = `tabPrice List`.`name`
        AND `tabPrice List`.`enabled` = 1""")

    # update for buying
    frappe.db.sql(
        """UPDATE `tabItem Price`
        SET `reference` = `supplier`, `customer` = NULL
        WHERE `selling` = 0
        AND `buying` = 1
        AND (`supplier` IS NOT NULL OR `supplier` = '')
        AND `price_list` = `tabPrice List`.`name`
        AND `tabPrice List`.`enabled` = 1""")
