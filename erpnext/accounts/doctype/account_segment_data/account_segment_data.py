# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import (today, add_days)
#site confige import
from nrp_manufacturing.utils import  get_config_by_name
class AccountSegmentData(Document):
	pass

@frappe.whitelist()
def calculate_segment_profit():
	date_yesterday = add_days(today(), -100)
	units = get_config_by_name("segment_wise_profit_csd", {})
	for single_unit in units:
		# sale_bgroup =	get_unit_sales_bgroup(single_unit,date_yesterday)
		for segment in units[single_unit].get('segment'):
			data =get_segment_gl_data(segment,units[single_unit].get('segment').get(segment),date_yesterday,single_unit)
		




def get_unit_sales_bgroup(unit,date):
	return frappe.db.sql("""
	select business_group,sum(amount) from `tabSales Invoice Item` as A
	INNER JOIN `tabItem CSD` as B ON A.`item_code` = B.item_code
	INNER JOIN `tabSales Invoice` AS C ON C.name = A.parent
	 where 
	DATE(A.`creation`) between '{0}' AND '{0}' AND C.company = '{1}' AND
	`business_group` IN ('CSD (Carbonated Soft Drinks)','Confectionery','Water')
	group by `business_group`
	""".format(date,unit),debug=True)
	


def get_segment_gl_data(account_title,account,date,unit):
	data = frappe.db.sql("""
	SELECT SUM(`credit_in_account_currency`-`debit_in_account_currency`) AS account_value 
FROM `tabGL Entry` WHERE account IN {1}  AND company='{3}' 
AND DATE(creation) BETWEEN '{2}' AND '{2}'
	""".format(account_title,tuple(account),date,unit))
	save_doc = {
		'doctype':'Account Segment Data',
		'segment':'CSD',
		'account':account_title,
		'coa': str(account),
		'company':unit,
		'date':date,
		'account_value':data[0][0]
	}
	frappe.get_doc(save_doc).save(ignore_permissions=True)