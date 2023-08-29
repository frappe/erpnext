# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate
from datetime import datetime
from frappe.query_builder.functions import Sum
from functools import reduce



def execute(filters=None):
	return SimpleCustomerLedger().run(filters)

class SimpleCustomerLedger():
	def run(self, filters):
		self.get_columns()
		self.get_data(filters)
		message=""
		self.get_chart(filters)
		self.get_summary(filters)
		return self.columns, self.data

	def get_data(self, filters):
		self.data=[]
		gl_entries = frappe.qb.DocType('GL Entry')
		curr_yr=frappe.utils.today()[:4]
		start_date= filters.from_date if filters.from_date is not None else frappe.utils.getdate(curr_yr+'-01-01')
		end_date= filters.to_date if filters.to_date is not None else frappe.utils.today()


		credit_case = frappe.qb.terms.Case().when(gl_entries.voucher_type == "Payment Entry", gl_entries.credit).else_(0)
		credit_alt = frappe.qb.terms.Case().when(gl_entries.voucher_type != "Payment Entry", gl_entries.credit).else_(0)
		values = {'start_date': start_date, 'customer_name':filters.customer_name}


		opening = frappe.db.sql(
				f"""
				SELECT SUM(gl.debit) - SUM(gl.credit) as balance
				FROM `tabGL Entry` as gl
				WHERE gl.posting_date<%(start_date)s AND party_type='Customer' AND docstatus=1 AND is_cancelled=0 AND party=%(customer_name)s
				""", values=values, as_dict=1)
		op=[op_bal['balance'] for op_bal in opening][0]
		sm = 0 if op is None else op
		opening_line={'voucher_type': 'Opening', 'balance':sm,'posting_date':start_date}

		sum_of_credit= Sum(credit_case)
		sum_of_misc= Sum(credit_alt)
		sum_of_debt= Sum(gl_entries.debit)

		query= (
			frappe.qb.from_(gl_entries)
				.select(gl_entries.voucher_no, gl_entries.voucher_type,
						sum_of_debt.as_('debit'),
						sum_of_credit.as_('credit'),
						sum_of_misc.as_('misc_credit'),
						gl_entries.against_voucher,gl_entries.against_voucher_type,
						gl_entries.party, gl_entries.remarks,
						gl_entries.posting_date)
				.where(gl_entries.party_type=='Customer')
				.where(gl_entries.docstatus==1)
				.where(gl_entries.is_cancelled==0)
				.where(gl_entries.party==filters.customer_name)
				.where(gl_entries.posting_date>=start_date)
				.where(gl_entries.posting_date<=end_date)
				.groupby(gl_entries.voucher_no)
				.orderby(gl_entries.posting_date)
			)
		result=query.run(as_dict=True)

		list1=[v['against_voucher'] for v in result if v['against_voucher_type']=='Sales Invoice']
		
		invoices= frappe.db.get_list('Sales Invoice',
			filters={'name': ['in', list( dict.fromkeys(list1) )]},
			fields=['name', 'status','clearance_date','total_net_weight','outstanding_amount','due_date','posting_date']
			)
		invoice_list = {i.name: i for i in invoices}
		data = []
		for ele in result:
			#  calculate balance 
			sm = sm+ ((ele.debit or 0) - (ele.credit or 0)- (ele.misc_credit or 0))
			ele.balance=round(sm, 2)

			# add the invoice status and aging
			if ele.voucher_type=='Sales Invoice':
				ele.status=invoice_list[ele.against_voucher].status
				ele.weight=invoice_list[ele.against_voucher].total_net_weight
				ele.weight =  None if ele.weight ==0 else ele.weight
				if invoice_list[ele.against_voucher].clearance_date is not None:
					delta=invoice_list[ele.against_voucher].clearance_date - invoice_list[ele.against_voucher].posting_date
					ele.age=delta.days
		
			data.append(ele)
			
		data.sort(key=lambda x: x['posting_date'])
		
		data.insert(0,opening_line)
		ranges=self.calculate_ranges(invoices,data[0])		
		data.append({'ranges':ranges})
		
		self.data=data
	
	def calculate_ranges(self, invoices,op):	
		# invoices.append({'posting_date': op.posting_date,'outstanding_amount':op.balance})
		range1=filter(lambda i:  (getdate()- i['posting_date']).days<=30, invoices)
		range2=filter(lambda i:  (getdate()- i.posting_date).days>30 and (getdate()- i.posting_date).days<=45, invoices)
		range3=filter(lambda i:  (getdate()- i.posting_date).days>45 and (getdate()- i.posting_date).days<=60, invoices)
		range4=filter(lambda i:  (getdate()- i.posting_date).days>60 and (getdate()- i.posting_date).days<=75, invoices)
		range5=filter(lambda i:  (getdate()- i.posting_date).days>75 and (getdate()- i.posting_date).days<=90, invoices)
		range6=filter(lambda i:  (getdate()- i.posting_date).days>90, invoices)

		out1=reduce(lambda t,v: t+v   ,map(lambda x: x['outstanding_amount'],range1),0)
		out2=reduce(lambda t,v: t+v   ,map(lambda x: x['outstanding_amount'],range2),0)
		out3=reduce(lambda t,v: t+v   ,map(lambda x: x['outstanding_amount'],range3),0)
		out4=reduce(lambda t,v: t+v   ,map(lambda x: x['outstanding_amount'],range4),0)
		out5=reduce(lambda t,v: t+v   ,map(lambda x: x['outstanding_amount'],range5),0)
		out6=reduce(lambda t,v: t+v   ,map(lambda x: x['outstanding_amount'],range6),0)
		return {'range1':out1, 'range2':out2, 'range3': out3, 'range4': out4, 'range5': out5, 'range6':out6}
	
	def sanatize(self, data):
		new_data=[]
		for d in data:
			if hasattr(d, 'debit') and d.debit==0:
				d.debit=''
			if hasattr(d, 'credit') and d.credit==0:
				d.credit=''
			if hasattr(d, 'misc_credit') and d.misc_credit==0:
				d.misc_credit=''
			new_data.append(d)
		return new_data

	def get_summary(self,filters):
		self.summary = []
	
	def get_chart(self,filters):
		self.chart=[]

	def get_columns(self):
		self.columns =  [
			{
				'fieldname': 'posting_date',
				'label': _('Date'),
				'fieldtype': 'Date',
				'align': 'left',
				'width': 140
			},
			{
				'fieldname': 'voucher_type',
				'label': _('Type'),
				'fieldtype': 'Data',
				'width': 130,
				'align': 'left'
			},
			{
				'fieldname': 'voucher_no',
				'label': _('Folio No'),
				'fieldtype': 'Dynamic Link',
				'options': 'voucher_type',
				'width': 180,
			},
			{
				'fieldname': 'weight',
				'label': _('wt'),
				'fieldtype': 'Data',
				'width': 60,
				'precision':2
			},
			{
				'fieldname': 'age',
				'label': _('Age'),
				'fieldtype': 'Data',
				'width': 60,
			},
			{
				'fieldname': 'status',
				'label': _('Status'),
				'fieldtype': 'Data',
				'width': 80,
			},
			{
				'fieldname': 'debit',
				'label': _('Debit'),
				'fieldtype': 'Data',
				'align': 'right',
				'width': 130
			},
			{
				'fieldname': 'credit',
				'label': _('Credit'),
				'fieldtype': 'Data',
				'align': 'right',
				'width': 130
			},
			{
				'fieldname': 'misc_credit',
				'label': _('Misc Credit'),
				'fieldtype': 'Data',
				'align': 'right',
				'width': 100
			},
			{
				'fieldname': 'balance',
				'label': _('Balance'),
				'fieldtype': 'Data',
				'align': 'right',
				'width': 150,
			},
		]
