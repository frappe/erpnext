from __future__ import unicode_literals

import frappe


def execute():
    """
    set proper customer and supplier details for item price
    based on selling and buying values
    """

    # update for selling
    frappe.db.sql(
        """UPDATE `tabItem Price` ip, `tabPrice List` pl
        SET ip.`reference` = ip.`customer`, ip.`supplier` = NULL
        WHERE ip.`selling` = 1
        AND ip.`buying` = 0
        AND (ip.`supplier` IS NOT NULL OR ip.`supplier` = '')
        AND ip.`price_list` = pl.`name`
        AND pl.`enabled` = 1""")

    # update for buying
    frappe.db.sql(
        """UPDATE `tabItem Price` ip, `tabPrice List` pl
        SET ip.`reference` = ip.`supplier`, ip.`customer` = NULL
        WHERE ip.`selling` = 0
        AND ip.`buying` = 1
        AND (ip.`customer` IS NOT NULL OR ip.`customer` = '')
        AND ip.`price_list` = pl.`name`
        AND pl.`enabled` = 1""")
