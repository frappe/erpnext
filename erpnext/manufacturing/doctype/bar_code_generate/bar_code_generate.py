# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import ast


class BarCodeGenerate(Document):
    pass


@frappe.whitelist()
def operation_query(doctype, txt, searchfield, start, page_len, filters):
    from frappe.desk.reportview import get_match_cond
    txt = "%{}%".format(txt)
    if searchfield == "name":
        searchfield = "op.name"
    if not filters.get('production_order'):
        frappe.msgprint(frappe._("Production Order Id Required"))
        return []
    return frappe.db.sql("""select op.name
    		from `tabOperation` as op
    		left join `tabProduction Order Operation` as proop
    		on proop.operation = op.name
    		left join `tabProduction Order` as pro
    		on pro.name = proop.parent
    		where pro.name = '{po}'
    			and ({key} like %s)
    			{mcond}
    		limit %s, %s""".format(key=searchfield, mcond=get_match_cond(doctype), po=filters['production_order']),
                         tuple([txt, start, page_len]))
