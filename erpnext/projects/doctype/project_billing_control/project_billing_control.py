# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ProjectBillingControl(Document):
	def get_project_payment_schedule(self):
		scope_item = frappe.db.sql("select scope_item from `tabProject Payment Schedule` where parent='{0}'".format(self.project_name),as_dict=True)
		item=[]

		for i in range(len(scope_item)):
			item.append(scope_item[i].scope_item)
		return item


	def get_item_cost(self):
		item_info = frappe.db.sql("select items_value,billing_percentage,billing_value,SUM(billing_value) as billing_sum  from `tabProject Payment Schedule` where parent='{0}' and scope_item='{1}' ".format(self.project_name,self.scope_item),as_dict=True)
		invoice_num = frappe.db.sql("select count(name) from `tabProject Billing Control` where project_name='{0}' and scope_item='{1}' ".format(self.project_name,self.scope_item))
		return item_info[0].items_value,item_info[0].billing_percentage,item_info[0].billing_value,item_info[0].billing_sum,invoice_num[0][0]


def get_item_list(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(""" select name,item_group from `tabItem` """)
