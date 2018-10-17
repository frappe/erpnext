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
