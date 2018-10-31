# What this patch attempts to do is to make sure that offline_pos_name is
# unique. If it finds any offline_pos_name that isn't unique, it will append
# a number to it to make it unique i.e it will turn 1234, 1234, 1234 to 1234,
# 1234-1, 1234-2.
#
# This is required so that the next action (adding a unique constraint to the
# offline_pos_name column) can be done without problems. This next step
# strengthens the syncing logic by taking the responsibilty for keeping out
# duplicates to the database layer and attain greater immunity from the race
# conditions experienced in the python code.
#
# see:
# 1. https://discuss.erpnext.com/t/pos-duplicated-sales-invoice-under-the-same-offline-pos-name/28956
# 2. https://discuss.erpnext.com/t/duplicated-sales-invoice-when-using-pos/41736
# 3. https://discuss.erpnext.com/t/erpnext-freezing-pos-sales-auto-submission-duplicate-sales/33556/
# and more for reports of duplicate invoices with the same offline_pos_name.
#
# it can also happen if you create a return invoice for a POS invoice because
# the offline pos name gets copied from the original invoice to the return
# invoice.
#

import frappe


def execute():
    duplicates = frappe.db.sql(
        """
        SELECT name, offline_pos_name FROM `tabSales Invoice`
        WHERE offline_pos_name IS NOT NULL
        GROUP BY offline_pos_name having count(*) > 1
        """
    )

    for duplicate in duplicates:
        keep, offline_pos_name = duplicate
        duplicate_list = frappe.db.sql(
            """
            SELECT name FROM `tabSales Invoice` WHERE
            offline_pos_name=%s
            """,
            offline_pos_name
        )

        counter = 0
        for item in duplicate_list:
            name, = item
            if name != keep:
                si = frappe.get_doc('Sales Invoice', name)
                counter += 1
                new_name = '{0}-{1}'.format(si.offline_pos_name, counter)
                si.db_set('offline_pos_name', new_name)
