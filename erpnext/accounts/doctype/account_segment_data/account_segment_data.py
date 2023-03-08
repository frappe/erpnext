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
	bgroup = ['CSD (Carbonated Soft Drinks)','Confectionery','Water','Juice','19 Ltr','Other']
	date_yesterday = add_days(today(), -100)
	units = get_config_by_name("segment_wise_profit_csd", {})
	for single_unit in units:
		sale_bgroup =	get_unit_sales_bgroup(single_unit,date_yesterday)
		for index,bg in enumerate(bgroup):
			if(index<=len(sale_bgroup)):
				if(bg in sale_bgroup[index].business_group):
					pass
				else:
					sale_bgroup.append({bg,1})
			else:
				sale_bgroup.append({bg,1})

		for coa in units[single_unit].get('segment'):
			data =get_segment_gl_data(coa,units[single_unit].get('segment').get(coa),date_yesterday,single_unit,sale_bgroup)
		




def get_unit_sales_bgroup(unit,date):
	return frappe.db.sql("""
	select business_group,sum(amount) as amount from `tabSales Invoice Item` as A
	INNER JOIN `tabItem CSD` as B ON A.`item_code` = B.item_code
	INNER JOIN `tabSales Invoice` AS C ON C.name = A.parent
	 where 
	DATE(A.`creation`) between '{0}' AND '{0}' AND C.company = '{1}' AND
	`business_group` IN ('CSD (Carbonated Soft Drinks)','Confectionery','Water')
	group by `business_group`
	""".format(date,unit),debug=True)
	


def get_segment_gl_data(account_title,account,date,unit,sale_bgroup):
	data = frappe.db.sql("""
	SELECT SUM(`credit_in_account_currency`-`debit_in_account_currency`) AS account_value 
FROM `tabGL Entry` WHERE account IN {1}  AND company='{3}' 
AND DATE(creation) BETWEEN '{2}' AND '{2}'
	""".format(account_title,tuple(account),date,unit))

			#business group wise sale_bgroup (account_value*busines group amount/100) 
			# put in bussiness group as segment in data base 

	# save_doc = {
	# 	'doctype':'Account Segment Data',
	# 	'segment':business_group,
	# 	'account':account_title,
	# 	'coa': str(account),
	# 	'company':unit,
	# 	'date':date,
	# 	#'account_value':(account_value*busines group amount/100)
	# }
	#frappe.get_doc(save_doc).save(ignore_permissions=True)