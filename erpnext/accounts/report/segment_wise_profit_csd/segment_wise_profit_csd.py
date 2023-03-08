# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):

	company = filters.get('company')
	from_date = filters.get('from_date')
	to_date = filters.get('to_date')
	columns = [
		("ACCOUNT") + "::250",
        ("CSD") + "::250",
        ("JUICES") + "::200",
        ("WATER") + "::150",
        ("CandyConfectionary") + "::120",
        ("Concentrates") + "::120",
        ("19LTR") + "::180",
		("Other") + "::180"
    ]
	data = []
	data = frappe.db.sql(""" 
		SELECT `account`,
			SUM(IF (`segment`='CSD' , `account_value`,0)) as csd, 
			SUM(IF (`segment`='JUICES' , `account_value` ,0))as juices,
			SUM(IF (`segment`='WATER' , `account_value`,0))AS  water,
			SUM(IF (`segment`='Candy&Confectionary' , `account_value`,0)) AS  candyconfectionary,
			SUM(IF (`segment`='Concentrates' , `account_value` ,0)) AS concentrates,
			SUM(IF (`segment`='19 LTR.'  ,`account_value`,0) ) as 19ltr,
			SUM(IF (`segment`='Other' , `account_value` ,0)) as other
		FROM `tabAccount Segment Data`
		WHERE date BETWEEN '{from_date}' and '{to_date}' 
		AND company = '{company}'
			group by `account`
	""".format(from_date=from_date, to_date=to_date,company=company), as_dict=True)
	
	return columns, data
