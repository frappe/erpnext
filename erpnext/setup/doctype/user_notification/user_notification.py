# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class UserNotification(Document):
    pass

def hr_notifications(doc, method):
    if frappe.modules.utils.get_doctype_module(doc.doctype) == 'HR':
    
        if hasattr(doc, 'handled_by'):
            
            if doc.handled_by != "--":
                
                if doc.handled_by in ["Line Manager", "Manager", "Director"]:
                    user = check_departement_roles(doc)

                    if user:
                        save_user_notification(doc, user[0][0])
                        add_message(doc, user[0][0])
                else:
                    users = get_role_users(doc.handled_by)
                    for usr in users:
                        save_user_notification(doc, usr[0])
                        add_message(doc, usr[0])

# def leave_application_notification_count(as_list=False):
#     notification_count = frappe.db.sql("""
#         select count(*) from `tabUser Notification` where target_doctype = 'Leave Application'
#         and status = 'Active' and user = '{0}'
#         """.format(frappe.session.user))

#     if notification_count:
#         return notification_count[0][0]

def check_departement_roles(doc):

    if doc.department:
        user = frappe.db.sql("""
            select tabUserRole.parent from tabUserRole inner join `tabUser Permission` on 
            `tabUser Permission`.user = tabUserRole.parent where tabUserRole.role ='{0}'
            and `tabUser Permission`.for_value = '{1}'
            """.format(doc.handled_by, doc.department))

        return user

def get_role_users(role):
 
    users = frappe.db.sql("""
        select parent from tabUserRole where role = '{0}'
        """.format(role))

    return users

def save_user_notification(doc, user, status="Active", message="An Action should be taken"):

    frappe.get_doc({
        "doctype": "User Notification",
        "target_doctype": doc.doctype,
        "target_docname": doc.name,
        "status": status,
        "user": user,
        "message": message
    }).save(ignore_permissions = True)

def add_message(doc, user, message="An Action should be taken by "):
    meta = frappe.get_meta(doc.doctype)
    if not meta.get_field('notification_message'):
            # create custom field
        frappe.get_doc({
            "doctype":"Custom Field",
            "dt": doc.doctype,
            "__islocal": 1,
            "fieldname": "notification_message",
            "bold": 1,
            "label": "Message",
            "read_only": 1,
            "allow_on_submit": 1,
            "fieldtype": "Text",
        }).save(ignore_permissions = True)
        frappe.db.commit()

    doc.notification_message = message