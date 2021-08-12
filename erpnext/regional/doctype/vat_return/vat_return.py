# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import json
import frappe
from six import iteritems
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cstr
from erpnext.regional.india import state_numbers

class VATRETURN(Document):
	def validate(self):
		self.get_data()

	def get_data(self):
		self.report_dict = json.loads(get_json('vat_return_template'))
		self.report_dict["company_name"]=self.company
		self.report_dict["pan_no"]=1234
		self.report_dict["ret_period"] = get_period(self.month, self.year)
		self.month_no = get_period(self.month)
		self.get_sales()
		self.json_output = frappe.as_json(self.report_dict)

	def get_sales(self):
		doc=frappe.db.sql("""select
		si.company,
		monthname(si.posting_date) as month,
		year(si.posting_date) as year,
		count(si.name) as no_of_invoice,
		(sum(total) + (select sum(grand_total) from `tabSales Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) group by month(xsi.posting_date) desc, year(xsi.posting_date)
			)) as total,
		(select sum(grand_total) from `tabSales Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) group by month(xsi.posting_date) desc, year(xsi.posting_date)
			)
				as exempted_sales,
		(select count(name) from `tabSales Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and year(xsi.posting_date)=year(si.posting_date) and xsi.is_return=1 and xsi.company=si.company  
			 group by month(xsi.posting_date) desc, year(xsi.posting_date)  ) as no_credit_note,
		(select count(name) from `tabSales Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and year(xsi.posting_date)=year(si.posting_date) and xsi.is_debit_note=1 and xsi.company=si.company  
			 group by month(xsi.posting_date) desc, year(xsi.posting_date)  ) as no_debit_note,
		case 
			when si.currency != "NPR" then sum(si.total)
		end as export,
		sum(total) as taxable_sales,
		sum(total_taxes_and_charges) as tax
		from `tabSales Invoice` as si
		where si.docstatus=1 
		group by year(si.posting_date) desc,
		monthname(si.posting_date) asc,
		company 
			""",as_dict=1)
		print(doc)
		last_month=["January" ,"February","March","April","May","June","July","August","September","October","November","December"]
		index =last_month.index(self.month)
		last=last_month[index-1]
		for i in doc:
			if i.month==self.month and i.company==self.company and i.year==int(self.year):
				self.report_dict["particular"]["sales"][0]["tv"]=i.taxable_sales+i.exempted_sales+i.export
				self.report_dict["particular"]["sales"][0]["tc"]=i.tax
				self.report_dict["particular"]["export"][0]["tv"]=i.export
				self.report_dict["particular"]["taxable_sales"][0]["tv"]=i.taxable_sales
				self.report_dict["particular"]["taxable_sales"][0]["tc"]=i.tax
				self.report_dict["particular"]["exempted_sales"][0]["tv"]=i.exempted_sales
				self.report_dict["particular"]["total"][0]["tc"]=i.tax + self.adjusted_tax_paid_on_sales
				self.report_dict["particular"]["other_adj"][0]["tc"]=self.adjusted_tax_paid_on_sales
				self.report_dict["particular"]["no_of_sales_invoice"][0]["tc"]=i.no_of_invoice
				self.report_dict["particular"]["no_of_credit_note"][0]["tc"]=i.no_credit_note
				self.report_dict["particular"]["no_of_debit_note"][0]["tc"]=i.no_debit_note
			if i.month==last and i.company==self.company and i.year==int(self.year) and i.month!="January":
				high=i.tax + self.adjusted_tax_paid_on_sales
			if i.month=="January" and i.company==self.company and i.year==int(self.year)-1:
				high=i.tax + self.adjusted_tax_paid_on_sales
		c_tax=high
		a=self.report_dict["particular"]["total"][0]["tc"]
		total=self.report_dict["particular"]["sales"][0]["tv"]

		doc1=frappe.db.sql("""select
		company,
		monthname(posting_date) as month,
		year(posting_date) as year,
		count(si.name) as no_of_invoices,
		(sum(total) + (select sum(grand_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) and xsi.company=si.company  group by month(xsi.posting_date) desc, year(xsi.posting_date)
			)) as total,
		(select sum(grand_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) and xsi.company=si.company group by month(xsi.posting_date) desc, year(xsi.posting_date)
			)
			as exempted_purchase,
		(select count(name) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) and xsi.company=si.company and xsi.is_return=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)
			) as is_debit_advice,
		(select sum(grand_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) and xsi.company=si.company group by month(xsi.posting_date) desc, year(xsi.posting_date) 
			and xsi.currency != "NPR"
			)
			as exempted_import,
		sum(total) as taxable_purchase,
		sum(total)*13/100 as local_tax,
		case 
			when si.currency != "NPR" then sum(si.total)
		end as taxable_import,
		case 
			when si.currency != "NPR" then sum(si.total)*13/100
		end as import_tax,
		(select sum(pii.amount) from `tabPurchase Invoice` as pd 
		inner join `tabPurchase Invoice Item` as pii on pd.name=pii.parent 
		where  month(pd.posting_date)= month(si.posting_date) and year(pd.posting_date)=year(si.posting_date) 
		and pii.is_fixed_asset=1 and si.company=pd.company group by month(pd.posting_date) desc, year(pd.posting_date)) as capital_purchase,

		(select sum(pii.amount)*13/100 from `tabPurchase Invoice Item` as pii  
		inner join `tabPurchase Invoice` as pd on pd.name=pii.parent 
		where month(pd.posting_date)=month(si.posting_date) and year(pd.posting_date)=year(si.posting_date)
		and pii.is_fixed_asset=1 and si.company=pd.company group by month(pd.posting_date) desc, year(pd.posting_date) ) as capital_tax
		from
		`tabPurchase Invoice` as si
		where si.docstatus=1 
		group by year(si.posting_date) desc,
		monthname(si.posting_date) asc,
		company""",as_dict=1)
		for i in doc1:
			if i.month==self.month and i.company==self.company and i.year==int(self.year):
				self.report_dict["particular"]["purchase"][0]["tv"]=i.taxable_purchase + i.taxable_import + i.exempted_purchase+i.exempted_import
				self.report_dict["particular"]["taxcable_purchase"][0]["tv"]=i.taxable_purchase
				self.report_dict["particular"]["taxcable_purchase"][0]["tp"]=i.local_tax
				self.report_dict["particular"]["taxcable_import"][0]["tv"]=i.taxable_import
				self.report_dict["particular"]["taxcable_import"][0]["tp"]=i.import_tax
				self.report_dict["particular"]["exempted_purchase"][0]["tv"]=i.exempted_purchase
				self.report_dict["particular"]["exempted_import"][0]["tv"]=i.exempted_import
				
				self.report_dict["particular"]["other_adj"][0]["tp"]=self.adjusted_tax_paid_on_purchase
				self.report_dict["particular"]["total"][0]["tp"]=i.local_tax + i.import_tax+self.adjusted_tax_paid_on_purchase
				self.report_dict["particular"]["no_of_purchase_invoice"][0]["tc"]=i.no_of_invoices
				self.report_dict["particular"]["no_of_debit_advice"][0]["tc"]=i.is_debit_advice
			if i.month==last and i.company==self.company and i.year==int(self.year) and i.month != "January":
				top=i.local_tax + i.import_tax+self.adjusted_tax_paid_on_purchase
			if i.month=="January" and i.company==self.company and i.year==int(self.year)-1:
				top=i.local_tax + i.import_tax+self.adjusted_tax_paid_on_purchase
		t_tax=top
		tot=self.report_dict["particular"]["purchase"][0]["tv"]
		b=self.report_dict["particular"]["total"][0]["tp"]
		self.report_dict["particular"]["debit_credit"][0]["tc"]	=a-b
		self.report_dict["particular"]["total"][0]["tv"]=total+tot
		print(c_tax)
		print(t_tax)
		if a-b < 0:
			self.report_dict["particular"]["vat_adj_last_mon"][0]["tc"]=c_tax-t_tax
			self.report_dict["particular"]["net_tax"][0]["tc"]=self.report_dict["particular"]["vat_adj_last_mon"][0]["tc"]+self.report_dict["particular"]["debit_credit"][0]["tc"]
		if a-b > 0:
			self.report_dict["particular"]["vat_adj_last_mon"][0]["tc"]=0
			self.report_dict["particular"]["net_tax"][0]["tc"]=self.report_dict["particular"]["vat_adj_last_mon"][0]["tc"]+self.report_dict["particular"]["debit_credit"][0]["tc"]
		self.report_dict["particular"]["total_payment"][0]["tv"]=self.report_dict["particular"]["net_tax"][0]["tc"]
		self.report_dict["particular"]["total_payment"][0]["tp"]="Voucher No:"
		self.report_dict["particular"]["total_payment"][0]["tc"]=self.voucher_no
		



def get_json(template):
	file_path = os.path.join(os.path.dirname(__file__), '{template}.json'.format(template=template))
	with open(file_path, 'r') as f:
		return cstr(f.read())


def get_period(month, year=None):
	month_no = {
		"January": 1,
		"February": 2,
		"March": 3,
		"April": 4,
		"May": 5,
		"June": 6,
		"July": 7,
		"August": 8,
		"September": 9,
		"October": 10,
		"November": 11,
		"December": 12
	}.get(month)

	if year:
		return str(month).zfill(2) +"-"+ str(year)
	else:
		return month_no

@frappe.whitelist()
def view_report(name):
	json_data = frappe.get_value("VAT RETURN", name, 'json_output')
	return json.loads(json_data)

@frappe.whitelist()
def make_json(name):
	json_data = frappe.get_value("VAT RETURN", name, 'json_output')
	file_name = "vat_return.json"
	frappe.local.response.filename = file_name
	frappe.local.response.filecontent = json_data
	frappe.local.response.type = "download"
