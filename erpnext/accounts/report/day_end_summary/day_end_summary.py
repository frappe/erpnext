from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import (today)
from six import iteritems
from frappe.query_builder.functions import Sum, Concat
from functools import reduce
from itertools import accumulate
import string
import random


def execute(filters=None):
	return DayEndSummaryReport().run(filters)

class DayEndSummaryReport():
	def run(self, filters):
			
		self.get_columns()
		self.get_data(filters)
		message="Daily Collection Report"
		
		self.get_chart(filters)
		self.get_summary(filters)
		return self.columns, self.data,message,self.chart,self.summary

	def get_data(self, filters):
		
		if filters is None:
			filters = dict(report_date= today())
		self.data=[]
		pEntry 		= 	frappe.qb.DocType('Payment Entry')
		journal 	= 	frappe.qb.DocType('Journal Entry')
		accounts 	= 	frappe.qb.DocType('Journal Entry Account')
		paid_amount = 	Sum(pEntry.paid_amount).as_("paid_amount")
		account_details= Concat(accounts.party,":",accounts.user_remark).as_("account_details")
		payment_details= Concat(pEntry.party,":",pEntry.remarks).as_("account_details")
		self.total_paid	=	0
		self.total_expenses=0
		self.cash_in_hand =0
		self.bank_in_hand=0
		self.today_cash=0
		self.total_sales=0
		self.total_payments=0
		self.acc_receivable=0

		expenses = frappe.qb.from_(journal) \
			.select(accounts.account,accounts.party,accounts.user_remark,accounts.debit.as_("expense_amount"), account_details) \
			.join(accounts) \
			.on(journal.name == accounts.parent) \
			.where(journal.posting_date==filters['report_date']) \
      		.where(journal.docstatus==1) \
			.where(accounts.account!='Cash - AT') \
            .where(accounts.debit!=0) \
			.run(as_dict=True)	

		collections = (frappe.qb.from_(pEntry)
					.select(paid_amount,pEntry.sales_person,pEntry.territory)
					.where(pEntry.posting_date == filters['report_date'])
					.where(pEntry.payment_type == 'Receive')
					.where(pEntry.party_type== 'Customer')
					.where(pEntry.docstatus==1)
					.groupby(pEntry.sales_person)).run(as_dict=True)
		payments= (frappe.qb.from_(pEntry)
					.select(pEntry.party_type.as_('account'),pEntry.party,
						pEntry.remarks, payment_details,
						pEntry.paid_amount.as_("expense_amount"))
					.where(pEntry.posting_date == filters['report_date'])
					.where(pEntry.paid_to=='Creditors - AT')).run(as_dict=True)		

		if collections is not None and collections:
			list=map(lambda value: value.paid_amount,collections)
			self.total_paid=reduce(lambda total,value: total+value,list,0)
		if expenses is not None and expenses:
			list=map(lambda value: value.expense_amount,expenses)
			self.total_expenses=reduce(lambda total,value: total+value,list,0)
		if payments is not None and payments:
			list=map(lambda value: value.expense_amount,expenses)
			self.total_payments=reduce(lambda total,value: total+value,list,0)

		if collections: self.data.extend(collections)
		if expenses: self.data.extend(expenses)	
		if payments: self.data.extend(payments)	

		summary={
			'cash_in_hand':self.cash_in_hand,
   			'today_cash':self.today_cash,
			'bank_in_hand':self.bank_in_hand,
			'today_collection':self.total_paid,
			'today_expenses':self.total_expenses,
			'today_sales':self.total_sales,
			'total_supplier_payment': self.total_payments,
			'account_receivable':self.acc_receivable
			}
		data= self.data
		data.append({'totals':summary})
		
		return data

	
	def get_chart(self, filters):		
		salesItem = frappe.qb.DocType('Sales Invoice Item')
		sales = frappe.qb.DocType('Sales Invoice')
		collections = frappe.qb.from_(salesItem) \
			.join(sales) \
			.on(sales.name == salesItem.parent) \
			.select(salesItem.brand,Sum(salesItem.qty).as_("qty"), Sum(salesItem.net_amount).as_("net_amount")) \
			.where(sales.posting_date == filters['report_date']) \
			.groupby(salesItem.brand).run(as_dict=True)


		accTable= frappe.qb.DocType('Account')
		banks	= [v['name'] for v in frappe.qb.from_(accTable).select(accTable.name).where(accTable.account_type=="Bank").run(as_dict=True)]

	

		gl = frappe.qb.DocType('GL Entry')
		self.bank_in_hand = frappe.qb.from_(gl) \
			.select((Sum(gl.debit)-Sum(gl.credit)).as_("value")) \
			.where(gl.account.isin(banks) ) \
       		.where(gl.docstatus==1) \
			.run(as_dict=True)[0].value

		self.cash_in_hand = frappe.qb.from_(gl) \
		.select((Sum(gl.debit)-Sum(gl.credit)).as_("value")) \
		.where(gl.account.isin(['Cash - AT','Cash In Hand - AT' ]) ) \
      	.where(gl.docstatus==1) \
		.run(as_dict=True)[0].value

		self.today_cash = frappe.qb.from_(gl) \
		.select((Sum(gl.debit)-Sum(gl.credit)).as_("value")) \
		.where(gl.account.isin(['Cash - AT','Cash In Hand - AT' ]) ) \
      	.where(gl.docstatus==1) \
        .where(gl.posting_date== filters['report_date']) \
        .run(as_dict=True)[0].value        
  

		self.acc_receivable = frappe.qb.from_(gl) \
		.select((Sum(gl.debit)-Sum(gl.credit)).as_("value")) \
		.where(gl.party_type =='Customer') \
      	.where(gl.docstatus==1) \
		.run(as_dict=True)[0].value

		chart_data=[ val['net_amount'] for val in collections]	
		self.total_sales =reduce(lambda total,value: total+value,chart_data,0)

		summary={
			'cash_in_hand':self.cash_in_hand,
   			'today_cash':self.today_cash,
			'bank_in_hand':self.bank_in_hand,
			'today_collection':self.total_paid,
			'today_expenses':self.total_expenses,
			'today_sales':self.total_sales,
			'total_supplier_payment': self.total_payments,
			'account_receivable':self.acc_receivable
			}

		self.data.append({'totals':summary})

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
				"label": _("Today Collection"),
				"fieldtype": "Data",
			},
			{
				"value": self.total_expenses,
				"label": _("Today Expense"),
				"fieldtype": "Data",
			},
   			{
				"value": self.today_cash,
				"label": _("=Today Cash"),
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
		    "label": _("Expense Head"),
		    "fieldtype": "Data",
		    "width": 200
		},
		{
		    "fieldname": "account_details",
		    "label": _("Expense Details"),
		    "fieldtype": "Data",
		    "width": 300
		},
		{
		    "fieldname": "expense_amount",
		    "label": _("Expense Amount"),
		    "fieldtype": "Data",

		},
		
		]