# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import (today,get_link_to_form, get_url_to_report, global_date_format, now,
						format_time,flt)
from six import iteritems
from frappe.query_builder.functions import Sum, Concat
from functools import reduce
from itertools import accumulate
import string
import random


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
			.where(journal.posting_date==filters.report_date) \
      		.where(journal.docstatus==1) \
			.where(accounts.account!='Cash - AT') \
            .where(accounts.debit!=0) \
			.run(as_dict=True)	

		collections = (frappe.qb.from_(pEntry)
					.select(paid_amount,pEntry.sales_person,pEntry.territory)
					.where(pEntry.posting_date == filters.report_date)
					.where(pEntry.payment_type == 'Receive')
					.where(pEntry.party_type== 'Customer')
					.where(pEntry.docstatus==1)
					.groupby(pEntry.sales_person)).run(as_dict=True)
		payments= (frappe.qb.from_(pEntry)
					.select(pEntry.party_type.as_('account'),pEntry.party,
						pEntry.remarks, payment_details,
						pEntry.paid_amount.as_("expense_amount"))
					.where(pEntry.posting_date == filters.report_date)
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
        .where(gl.posting_date== filters.report_date) \
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


def get_report_content():
	report = frappe.get_doc('Report', 'Day End Summary')
	filters= {"report_date":today()}
	columns, data = report.get_data(filters = filters, as_dict=True, ignore_prepared_report=True)
	
	if data is None or len(data)==0 :
		return None
	# columns, data = make_links(columns, data)
	# columns = update_field_types(columns)
	return get_html_table(columns, data)


def make_links(columns, data):
	for row in data:
		doc_name = row.get('name')
		for col in columns:
			if not row.get(col.fieldname):
				continue			
			if col.fieldtype == "Link":
				if col.options and col.options != "Currency":
					row[col.fieldname] = get_link_to_form(col.options, row[col.fieldname])
			elif col.fieldtype == "Dynamic Link":
				if col.options and row.get(col.options):
					row[col.fieldname] = get_link_to_form(row[col.options], row[col.fieldname])
			elif col.fieldtype == "Currency":
				doc = frappe.get_doc(col.parent, doc_name) if doc_name and col.parent else None
				# Pass the Document to get the currency based on docfield option
				row[col.fieldname] = frappe.format_value(row[col.fieldname], col, doc=doc)
	return columns, data

def update_field_types(columns):
	for col in columns:
		if col.fieldtype in  ("Link", "Dynamic Link", "Currency")  and col.options != "Currency":
			col.fieldtype = "Data"
			col.options = ""
	return columns

def get_html_table(columns=None, data=None):
	date_time = global_date_format(now()) + ' ' + format_time(now())
	report='Day End Summary'

	totals= data[-1]["totals"]

	return frappe.render_template('erpnext/accounts/report/day_end_summary/day_end_summary2.html', {
		'title': 'Day End Summary Report',
		'date_time': date_time,
		'columns': columns,
		'data': data,
		'report_name': report,
		'totals': totals
	})

def send():
	email_to=['alwahabs@gmail.com','ankhan.1976@gmail.com']
	data = get_report_content()
	if not data:
		return

	attachments = None
	message = data

	frappe.sendmail(
		recipients = email_to,
		subject = 'Day End Summary Report',
		message = message,
		attachments = attachments,
		reference_name = 'Day End Summary'
	)