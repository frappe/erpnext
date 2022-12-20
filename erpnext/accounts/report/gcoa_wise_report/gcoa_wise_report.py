# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt,getdate,nowdate,cint,add_days
from frappe.utils.data import get_first_day

def execute(filters=None):
	filter 					= {}
	filter['from_date'] 	= filters.from_date
	filter['to_date'] 		= filters.to_date
	filter['gcoa_name'] 	= filters.gcoa_name
	year					= getdate(filters['to_date']).year 
	month 					= getdate(filters['to_date']).month
	filter['time'] 			= str(year)+'0'+ str(month) if len(str(month)) == 2 else str(year) + '00' + str(month)
	columns 				= get_columns()
	data 					= get_data(filter,True)
	return columns, data

def get_data(filters,is_for_report=None):
	value = frappe._dict({'opening_debit':0,'opening_credit':0,'debit':0,'credit':0,'amount':0,'data':[]})
	is_inter_company = frappe.db.get_value('DHI GCOA Mapper',filters['gcoa_name'],['is_inter_company'])
	val = []
	for d in get_coa(filters['gcoa_name']):
		if d.doc_company :
			val 					= from_gl_applicable_for_doc(d,filters)
			value.data 				+= val['data']
		elif not d.doc_company:
			val 					= from_gl_applicable_for_both(is_inter_company,d,filters)
			value.data 				+= val['data']
		if val:
			value.opening_debit 	+= flt(val['opening_debit'])
			value.opening_credit 	+= flt(val['opening_credit'])
			value.debit 			+= flt(val['debit'])
			value.credit 			+= flt(val['credit'])
			value.amount 			+= flt(val['amount'])
  
	if not is_for_report:
		return value.data
	if is_for_report:
		value.data.append({'account':'Total', 'opening_debit':value['opening_debit'], 'opening_credit':value['opening_credit'],
							'debit':value['debit'],'credit':value['credit'],'amount':value['amount']
						})
	return value.data

# for gl selected for particular doc company
def from_gl_applicable_for_doc(coa,filters):
	value = frappe._dict({'opening_debit':0,'opening_credit':0,'debit':0,'credit':0,'amount':0,'data':[]})
	doc = frappe.get_doc('DHI Setting')
	total_debit = total_credit = 0
	query = """
				SELECT  SUM(CASE WHEN posting_date < '{0}' THEN debit ELSE 0 END) AS opening_debit,
						SUM(CASE WHEN posting_date < '{0}' THEN credit ELSE 0 END) AS opening_credit,
						SUM(CASE WHEN posting_date >= "{0}" AND posting_date <="{1}" THEN debit ELSE 0 END) AS debit,
						SUM(CASE WHEN posting_date >= "{0}" AND posting_date <="{1}" THEN credit ELSE 0 END) AS credit
				FROM `tabGL Entry` where account = "{2}"
				AND (credit IS NOT NULL OR debit IS NOT NULL)
				AND posting_date <= '{1}'
			""".format(filters['from_date'],filters['to_date'],coa.account)
	for d in frappe.db.sql(query, as_dict = True):
		total_debit 	= flt(flt(d.debit) + flt(d.opening_debit))
		total_credit 	= flt(flt(d.credit) + flt(d.opening_credit))
		d['amount'] 	= total_debit - total_credit if coa.root_type in ['Asset','Expense'] else flt(total_credit - total_debit) * -1
		if d.amount or total_credit or total_debit or d.debit or d.credit:
			if flt(d.opening_debit) > flt(d.opening_credit):
				d.opening_debit 	= flt(d.opening_debit) - flt(d.opening_credit)
				d.opening_credit 	= 0
			elif flt(d.opening_credit) > flt(d.opening_debit):
				d.opening_credit 	= flt(d.opening_credit) - flt(d.opening_debit)
				d.opening_debit 	= 0
			else:
				d.opening_credit 	= 0
				d.opening_debit 	= 0
			value.opening_debit 	+= flt(d.opening_debit)
			value.opening_credit 	+= flt(d.opening_credit)
			value.debit 			+= flt(d.debit)
			value.credit 			+= flt(d.credit)
			value.amount 			+= flt(d.amount)
			value.data.append({
							'opening_debit': value['opening_debit'],'opening_credit':value['opening_credit'],
							'account':coa.account,'entity':doc.entity,'segment':doc.segment,'flow':doc.flow,
							'interco':'I_'+coa.doc_company,'time':filters['time'],'debit':value['debit'],
							'credit':value['credit'],'amount':value['amount'],})
	return value

# when gl is used for both inter and none inter companies
def from_gl_applicable_for_both(is_inter_company,coa,filters):
	value 	= frappe._dict({'opening_debit':0,'opening_credit':0,'debit':0,'credit':0,'amount':0,'data':[]})
	doc 	= frappe.get_doc('DHI Setting')
	inter_company = frappe._dict()
	i_none = frappe._dict({'opening_debit': 0,'opening_credit': 0,'account':coa.account,
							'entity':doc.entity,'segment':doc.segment,'flow':doc.flow,
							'interco':'I_NONE','time':filters['time'],'debit':0,'credit':0,'amount':0,
							})
	if coa.account_type in ['Payable','Receivable']:
		query = """SELECT 
					SUM(CASE WHEN posting_date < '{0}' THEN debit ELSE 0 END) AS opening_debit,
					SUM(CASE WHEN posting_date < '{0}' THEN credit ELSE 0 END) AS opening_credit,
					SUM(CASE WHEN posting_date >= "{0}" AND posting_date <="{1}" THEN debit ELSE 0 END) AS debit,
					SUM(CASE WHEN posting_date >= "{0}" AND posting_date <="{1}" THEN credit ELSE 0 END) AS credit, 
					party, party_type
				FROM `tabGL Entry` where posting_date <= "{1}" 
				AND account = "{2}" 
				AND (credit IS NOT NULL OR debit IS NOT NULL)
				GROUP BY party
				""".format(filters['from_date'],filters['to_date'],coa.account)
	else:
		query = """SELECT 
					SUM(CASE WHEN posting_date < '{0}' THEN debit ELSE 0 END) AS opening_debit,
					SUM(CASE WHEN posting_date < '{0}' THEN credit ELSE 0 END) AS opening_credit,
					SUM(CASE WHEN posting_date >= "{0}" AND posting_date <="{1}" THEN debit ELSE 0 END) AS debit,
					SUM(CASE WHEN posting_date >= "{0}" AND posting_date <="{1}" THEN credit ELSE 0 END) AS credit, 
					'' AS party, '' AS party_type
				FROM `tabGL Entry` where posting_date <= "{1}" 
				AND account = "{2}" 
				AND (credit IS NOT NULL OR debit IS NOT NULL)
				""".format(filters['from_date'],filters['to_date'],coa.account)
	total_debit = total_credit = 0
	for a in frappe.db.sql(query,as_dict=True) :
		if flt(a.opening_debit) > flt(a.opening_credit):
			a.opening_debit 	= flt(a.opening_debit) - flt(a.opening_credit)
			a.opening_credit 	= 0
		elif flt(a.opening_credit) > flt(a.opening_debit):
			a.opening_credit 	= flt(a.opening_credit) - flt(a.opening_debit)
			a.opening_debit 	= 0
		else:
			a.opening_credit 	= 0
			a.opening_debit 	= 0
		if flt(a.debit) > 0 or flt(a.credit) > 0 or flt(a.opening_debit) > 0 or flt(a.opening_credit) > 0:
			total_debit 	= flt(flt(a.debit) + flt(a.opening_debit))
			total_credit 	= flt(flt(a.credit) + flt(a.opening_credit))
			a['amount'] 	= total_debit - total_credit if coa.root_type in ['Asset','Expense'] else flt(total_credit - total_debit) * -1
			# if a.debit or a.credit or a.opening_debit or a.opening_credit or a.amount:
			dhi_company_code =''
			# fetch company code base on party for dhi companies
			if a.party_type == 'Supplier':
				dhi_company_code 	= frappe.db.get_value('Supplier',{'name':a.party,'inter_company':1,'disabled':0},['company_code'])
			elif a.party_type == 'Customer':
				dhi_company_code 	= frappe.db.get_value('Customer',{'name':a.party,'inter_company':1,'disabled':0},['company_code'])
			if dhi_company_code and is_inter_company:
				# create row for each dhi companies base company code
				if dhi_company_code in inter_company.keys():
					inter_company[dhi_company_code]["opening_debit"] 	+= flt(a.opening_debit)
					inter_company[dhi_company_code]["opening_credit"] 	+= flt(a.opening_credit)
					inter_company[dhi_company_code]["debit"] 			+= flt(a.debit)
					inter_company[dhi_company_code]["credit"] 			+= flt(a.credit)
					inter_company[dhi_company_code]["amount"] 			+= flt(a.amount)
				else:
					inter_company.setdefault(dhi_company_code,{'opening_debit': a.opening_debit,'opening_credit': a.opening_credit,'account':coa.account,
																'entity':doc.entity,'segment':doc.segment,'flow':doc.flow,'interco':str('I_'+dhi_company_code),
																'time':filters['time'],'debit':a.debit,'credit':a.credit,'amount':a.amount,
															}) 
				
				value['debit'] 				+= flt(a.debit)
				value['credit'] 			+= flt(a.credit)
				value['amount'] 			+= flt(a.amount)
			elif not dhi_company_code and not is_inter_company:
				value['debit'] 				+= flt(a.debit)
				value['credit'] 			+= flt(a.credit)
				value['amount'] 			+= flt(a.amount)
				i_none['opening_debit'] 	+= flt(a.opening_debit)
				i_none['opening_credit'] 	+= flt(a.opening_credit)
				i_none['debit'] 			+= flt(a.debit)
				i_none['credit'] 			+= flt(a.credit)
				i_none['amount'] 			+= flt(a.amount)
	for key, item in inter_company.items():
		value.data.append(item)
	if flt(i_none['amount']) != 0:
		value.data.append(i_none)
	for a in value.data:
		if flt(a['opening_debit']) > flt(a['opening_credit']):
			a['opening_debit'] 	= flt(a['opening_debit']) - flt(a['opening_credit'])
			a['opening_credit'] 	= 0
		elif flt(a['opening_credit']) > flt(a['opening_debit']):
			a['opening_credit'] 	= flt(a['opening_credit']) - flt(a['opening_debit'])
			a['opening_debit'] 	= 0
		else:
			a['opening_credit'] 	= 0
			a['opening_debit'] 	= 0
		value['opening_debit'] 		+= flt(a['opening_debit'])
		value['opening_credit'] 	+= flt(a['opening_credit'])
	return value

def get_coa(gcoa_account_name):
	return frappe.db.sql('''
						 SELECT account, account_type,
						   root_type, doc_company
						FROM `tabDHI Mapper Item`
						WHERE parent = '{}'
						 '''.format(gcoa_account_name),as_dict = True)

def create_transaction(is_monthly_report=None):
	dhi_setting = frappe.get_doc('DHI Setting')
	filters 						= {}
	filters['is_inter_company'] 	= ''

	if cint(dhi_setting.manual_pull) :
		filters['from_date']  		= dhi_setting.from_date
		filters['to_date'] 	  		= dhi_setting.to_date
		year						= getdate(dhi_setting.to_date).year 
		month 						= getdate(dhi_setting.to_date).month
		filters['time'] 			= str(year) + '0'+ str(month) if len(str(month)) == 2 else str(year) + '00'+ str(month)
		dhi_setting.manual_pull		= 0
		dhi_setting.from_date		= None
		dhi_setting.to_date			= None
	elif getdate(nowdate()) == getdate(get_first_day(nowdate())):
		filters['from_date']  		= getdate(frappe.defaults.get_user_default("year_start_date"))
		filters['to_date'] 	  		= getdate(add_days(get_first_day(nowdate()),-1))
		year						= getdate(filters['to_date']).year 
		month 						= getdate(filters['to_date']).month
		filters['time'] 			= str(year)+'.'+ '0'+ str(month) if len(str(month)) == 2 else str(year) + '00' + str(month)
	else:
		return
	doc 			= frappe.new_doc('Consolidation Transaction')
	doc.from_date 	= filters['from_date']
	doc.to_date 	= filters['to_date']
	doc.set('items',[])
	for d in frappe.db.sql('''
				SELECT account_name, account_code, is_inter_company
				FROM `tabDHI GCOA Mapper`
				''',as_dict=True):
		filters['gcoa_name'] = d.account_name
		i_none = frappe._dict({ 'flow':dhi_setting.flow,'interco':dhi_setting.interco,'entity':dhi_setting.entity,
						 		'time':filters['time'],'segment':dhi_setting.segment,'account':d.account_name,
	  							'account_code':d.account_code,'opening_debit':0,'opening_credit':0,'debit':0,'credit':0,'amount':0})
		for a in get_data(filters,False):
			if a['interco'] == 'I_NONE':
				i_none['opening_debit'] 	+= flt(a.opening_debit)
				i_none['opening_credit'] 	+= flt(a.opening_credit)
				i_none['debit'] 			+= flt(a.debit)
				i_none['credit'] 			+= flt(a.credit)
				i_none['amount'] 			+= flt(a.amount)
			elif a['interco'] != 'I_NONE':
				row 						= doc.append('items',{})
				row.account 				= d.account_name
				row.account_code 			= d.account_code
				row.amount 					= a['amount']
				row.opening_debit 			= a['opening_debit']
				row.opening_credit 			= a['opening_credit']
				row.debit 					= a['debit']
				row.credit 					= a['credit']
				row.entity 					= a['entity']
				row.segment 				= a['segment']
				row.flow 					= a['flow']
				row.interco 				= a['interco']
				row.time 					= a['time']
		row 	= doc.append('items',{})
		row.update(i_none)
	doc.save(ignore_permissions=True)
	doc.submit()
	dhi_setting.save()
	
def get_columns():
	return [
     		{
				"fieldname":"account",
				"label":"Account",
				"fieldtype":"Link",
				"options":"Account",
				"width":180
			},
			{
				"fieldname":"entity",
				"label":"Entity",
				"fieldtype":"Data",
				"width":60
			},
			{
				"fieldname":"segment",
				"label":"Segment",
				"fieldtype":"Data",
				"width":60
			},
			{
				"fieldname":"flow",
				"label":"Flow",
				"fieldtype":"Data",
				"width":60
			},
			{
				"fieldname":"interco",
				"label":"Interco",
				"fieldtype":"Data",
				"width":60
			},
			{
				"fieldname":"time",
				"label":"Time",
				"fieldtype":"Data",
				"width":100
			},
			{
				"fieldname":"opening_debit",
				"label":"Opening(Dr)",
				"fieldtype":"Currency",
				"width":100
			},
			{
				"fieldname":"opening_credit",
				"label":"Opening(Cr)",
				"fieldtype":"Currency",
				"width":100
			},
			{
				"fieldname":"debit",
				"label":"Debit",
				"fieldtype":"Currency",
				"width":100
			},
			{
				"fieldname":"credit",
				"label":"Credit",
				"fieldtype":"Currency",
				"width":100
			},
			{
				"fieldname":"amount",
				"label":"Amount",
				"fieldtype":"Currency",
				"width":120
			},
		]