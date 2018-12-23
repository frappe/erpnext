from __future__ import unicode_literals

import frappe

from erpnext.accounting.doctype.gl_entry.gl_entry import update_against_account

def execute():
    from_date = "2015-05-01"

    for doc in frappe.get_all("Journal Entry",
        filters={"creation": (">", from_date), "docstatus": "1"}):

        # update in gl_entry
        update_against_account("Journal Entry", doc.name)

        # update in jv
        doc = frappe.get_doc("Journal Entry", doc.name)
        doc.set_against_account()
        doc.db_update()

    for doc in frappe.get_all("Sales Invoice",
        filters={"creation": (">", from_date), "docstatus": "1"},
        fields=["name", "customer"]):

        frappe.db.sql("""update `tabGL Entry` set against=%s
            where voucher_type='Sales Invoice' and voucher_no=%s
            and credit > 0 and ifnull(party, '')=''""",
            (doc.customer, doc.name))

    for doc in frappe.get_all("Purchase Invoice",
        filters={"creation": (">", from_date), "docstatus": "1"},
        fields=["name", "supplier"]):

        frappe.db.sql("""update `tabGL Entry` set against=%s
            where voucher_type='Purchase Invoice' and voucher_no=%s
            and debit > 0 and ifnull(party, '')=''""",
            (doc.supplier, doc.name))
