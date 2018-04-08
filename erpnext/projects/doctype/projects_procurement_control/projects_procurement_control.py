# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ProjectsProcurementControl(Document):
	def get_project_item(self):
		scope_item = frappe.db.sql("select scope_item from `tabProject Costing Schedule` where parent='{0}'".format(self.project_name),as_dict=True)
		item=[]

		for i in range(len(scope_item)):
			item.append(scope_item[i].scope_item)
		return item


	def get_item_cost(self):
		item_info = frappe.db.sql("select items_cost_price,cost_value from `tabProject Costing Schedule` where parent='{0}' and scope_item='{1}' ".format(self.project_name,self.scope_item),as_dict=True)
		return item_info[0].items_cost_price,item_info[0].cost_value



	# def get_item_cost(self):
	# 	pass
	# 	item_info = frappe.db.sql("select items_value,billing_percentage,billing_value,SUM(billing_value) as billing_sum from `tabProject Costing Schedule` where parent='{0}' and scope_item='{1}' ".format(self.project_name,self.scope_item),as_dict=True)
	# 	return item_info[0].items_value,item_info[0].billing_percentage,item_info[0].billing_value,item_info[0].billing_sum

