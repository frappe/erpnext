# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import getdate

def execute():
    if has_deleted_company_transactions():
        child_doctypes = frappe.get_all('DocType', filters = {'istable': 1}, pluck = 'name')

        for doctype in child_doctypes:
            docs = frappe.get_all(doctype, fields=['name', 'parent', 'parenttype'])

            for doc in docs:
                if not frappe.db.exists(doc['parenttype'], doc['parent']):
                    frappe.db.delete(doctype, {'name': doc['name']})

                elif check_for_new_doc_with_same_name_as_deleted_parent(doc, doctype):
                    frappe.db.delete(doctype, {'name': doc['name']})

def has_deleted_company_transactions():
    return frappe.get_all('Transaction Deletion Record')

def check_for_new_doc_with_same_name_as_deleted_parent(doc, doctype):
    """
        Compares creation times of parent and child docs.
        Since Transaction Deletion Record resets the naming series after deletion,
        it allows the creation of new docs with the same names as the deleted ones.
    """

    parent_creation_time = frappe.db.get_value(doc['parenttype'], doc['parent'], 'creation')
    child_creation_time = frappe.db.get_value(doctype, doc, 'creation')

    if getdate(parent_creation_time) > getdate(child_creation_time):
        return True
    return False