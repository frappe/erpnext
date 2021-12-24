from __future__ import unicode_literals

import frappe


def execute():
    if frappe.db.exists("DocType", "Lost Reason Detail"):
        frappe.reload_doc("crm", "doctype", "opportunity_lost_reason")
        frappe.reload_doc("crm", "doctype", "opportunity_lost_reason_detail")
        frappe.reload_doc("setup", "doctype", "quotation_lost_reason_detail")

        frappe.db.sql("""INSERT INTO `tabOpportunity Lost Reason Detail` SELECT * FROM `tabLost Reason Detail` WHERE `parenttype` = 'Opportunity'""")

        frappe.db.sql("""INSERT INTO `tabQuotation Lost Reason Detail` SELECT * FROM `tabLost Reason Detail` WHERE `parenttype` = 'Quotation'""")

        frappe.db.sql("""INSERT INTO `tabQuotation Lost Reason` (`name`, `creation`, `modified`, `modified_by`, `owner`, `docstatus`, `parent`, `parentfield`, `parenttype`, `idx`, `_comments`, `_assign`, `_user_tags`, `_liked_by`, `order_lost_reason`)
            SELECT o.`name`, o.`creation`, o.`modified`, o.`modified_by`, o.`owner`, o.`docstatus`, o.`parent`, o.`parentfield`, o.`parenttype`, o.`idx`, o.`_comments`, o.`_assign`, o.`_user_tags`, o.`_liked_by`, o.`lost_reason`
            FROM `tabOpportunity Lost Reason` o LEFT JOIN `tabQuotation Lost Reason` q ON q.name = o.name WHERE q.name IS NULL""")

        frappe.delete_doc("DocType", "Lost Reason Detail")
