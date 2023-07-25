# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import flt, cint
from six import iteritems
from frappe.query_builder.functions import Sum
from functools import reduce
from itertools import accumulate


def execute(filters=None):
	return CollectionReport().run(filters)

class CollectionReport():
	def run(self, filters):
		self.get_columns()
		self.get_data(filters)
		message="Daily Collection Report"
		
		self.get_chart(filters)
		self.get_summary(filters)
		return self.columns, self.data,message,self.chart,self.summary

	def get_data(self, filters):
		self.data=[]
		pEntry 		= 	frappe.qb.DocType('Payment Entry')
		journal 	= 	frappe.qb.DocType('Journal Entry')
		accounts 	= 	frappe.qb.DocType('Journal Entry Account')
		paid_amount = 	Sum(pEntry.paid_amount).as_("paid_amount")
		self.total_paid	=	0
		self.total_expenses=0

		expenses = frappe.qb.from_(journal) \
			.select(accounts.account,Sum(accounts.debit).as_("expense_amount")) \
			.join(accounts) \
			.on(journal.name == accounts.parent) \
			.where(journal.posting_date==filters.report_date) \
			.where(accounts.account !='Cash - AT') \
			.groupby(accounts.account) \
			.run(as_dict=True)	

		collections = (frappe.qb.from_(pEntry)
					.select(paid_amount,pEntry.sales_person)
					.where(pEntry.posting_date == filters.report_date)
					.where(pEntry.payment_type == 'Receive')
					.where(pEntry.party_type== 'Customer')
					.groupby(pEntry.sales_person)).run(as_dict=True)		

		if collections is not None and collections:
			list=map(lambda value: value.paid_amount,collections)
			self.total_paid=reduce(lambda total,value: total+value,list)
		if expenses is not None and expenses:
			list=map(lambda value: value.expense_amount,expenses)
			self.total_expenses=reduce(lambda total,value: total+value,list)

		if collections: self.data.extend(collections)
		if expenses: self.data.extend(expenses)	

	
	def get_chart(self, filters):		
		salesItem = frappe.qb.DocType('Sales Invoice Item')
		sales = frappe.qb.DocType('Sales Invoice')
		collections = frappe.qb.from_(salesItem) \
			.join(sales) \
			.on(sales.name == salesItem.parent) \
			.select(salesItem.brand,Sum(salesItem.qty).as_("qty"), Sum(salesItem.net_amount).as_("net_amount")) \
			.where(sales.posting_date == filters.report_date) \
			.groupby(salesItem.brand).run(as_dict=True)


		accTable= frappe.qb.DocType('Account')
		banks	= [v['name'] for v in frappe.qb.from_(accTable).select(accTable.name).where(accTable.account_type=="Bank").run(as_dict=True)]

	

		gl = frappe.qb.DocType('GL Entry')
		self.bank_in_hand = frappe.qb.from_(gl) \
			.select((Sum(gl.debit)-Sum(gl.credit)).as_("value")) \
			.where(gl.account.isin(banks) ) \
			.run(as_dict=True)[0].value

		self.cash_in_hand = frappe.qb.from_(gl) \
		.select((Sum(gl.debit)-Sum(gl.credit)).as_("value")) \
		.where(gl.account.isin(['Cash - AT','Cash In Hand - AT' ]) ) \
		.run(as_dict=True)[0].value


		self.acc_receivable = frappe.qb.from_(gl) \
		.select((Sum(gl.debit)-Sum(gl.credit)).as_("value")) \
		.where(gl.party_type =='Customer') \
		.run(as_dict=True)[0].value

		chart_data=[ val['net_amount'] for val in collections]	
		self.total_sales =reduce(lambda total,value: total+value,chart_data,0)

		self.chart = {
			'data': {
				'labels': [ val['brand'] for val in collections],
				'datasets': [
					{
					   'name': "Sales Data", 
					   'type': "pie",
					   'values': chart_data
					}]
				},
			'type': "pie"
		} 

	def get_summary(self,filters):
		self.summary = [{	
				"value": self.total_paid,
				"label": _("Total Collection"),
				"fieldtype": "Data",
			},
			{
				"value": self.total_expenses,
				"label": _("Total Expense"),
				"fieldtype": "Data",
			},
			{
				"value": self.cash_in_hand,
				"label": _("Total Cash in Hand"),
				"fieldtype": "Data",
			},
			{
				"value": self.bank_in_hand,
				"label": _("Total Bank"),
				"fieldtype": "Data",
			},
			{
				"value": self.total_sales,
				"label": _("Total Sale"),
				"fieldtype": "Data",
			},
			{
				"value": self.acc_receivable,
				"label": _("Total Receiable"),
				"fieldtype": "Data",
			}
			]

	def get_columns(self):
		self.columns = [{
		    "fieldname": "sales_person",
		    "label": _("Sales Persons"),
		    "fieldtype": "Data",
		    "width": 300
		},
		{
		    "fieldname": "paid_amount",
		    "label": _("Amount"),
		    "fieldtype": "Data",

		},
		{
		    "fieldname": "account",
		    "label": _("Expense Accounts"),
		    "fieldtype": "Data",
		    "width": 300
		},
		{
		    "fieldname": "expense_amount",
		    "label": _("Expense Amount"),
		    "fieldtype": "Data",

		},
		
		]
