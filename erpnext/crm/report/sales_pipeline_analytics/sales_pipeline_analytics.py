# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import frappe
from datetime import date
import pandas
from dateutil.relativedelta import relativedelta
from six import iteritems
from frappe.utils import flt
from erpnext.setup.utils import get_exchange_rate

def execute(filters=None):
	return SalesPipelineAnalytics(filters).run()

class SalesPipelineAnalytics(object):

	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()

		return self.columns, self.data, None, self.chart

	def get_columns(self):
		self.columns = []

		based_on = {
			'Number' : "Int",
			'Amount' : "Currency"
		}[self.filters.get('based_on')]

		if self.filters.get('range') == "Monthly":
			month_list = self.get_month_list()

			for month in month_list:		
				self.columns.append(
					{
						'fieldname': month,
						'fieldtype': based_on,
						'label': month,
						'width': 200
					}
				)

		elif self.filters.get('range') == "Quaterly":
			for quarter in range(1,5):
				self.columns.append(
					{
						'fieldname': f"Q{quarter}",
						'fieldtype': based_on,
						'label': f"Q{quarter}",
						'width': 200
					}
				)

		if self.filters.get("pipeline_by") == "Owner":				
			self.columns.insert(0,{
				'fieldname': "opportunity_owner",
				'label': "Opportunity Owner",
				'width':200
			})

		elif self.filters.get("pipeline_by") == "Sales Stage":
			self.columns.insert(0,{
				'fieldname':"sales_stage",
				'label':"Sales Stage",
				'width':200
			})		
		return self.columns

	def get_data(self):

		select_1 ={
			'Owner': '_assign as opportunity_owner',
			'Sales Stage': 'sales_stage'
		}[self.filters.get('pipeline_by')]

		select_2 ={
			'Number': 'count(name) as count',
			'Amount': 'opportunity_amount as amount'  
		}[self.filters.get('based_on')]

		group_by_1 = {
			'Owner': '_assign',
			'Sales Stage': 'sales_stage'
		}[self.filters.get('pipeline_by')]

		group_by_2 = {
			'Monthly': 'month(expected_closing)',
			'Quaterly': 'QUARTER(expected_closing)'
		}[self.filters.get('range')]


		pipeline_by = {
			'Owner': 'opportunity_owner',
			'Sales Stage': 'sales_stage'
		}[self.filters.get('pipeline_by')]

		duration = {
			'Monthly': 'monthname(expected_closing) as month',
			'Quaterly': 'QUARTER(expected_closing) as quarter'
		}[self.filters.get('range')]

		period_by = {
			'Monthly': 'month',
			'Quaterly': 'quarter'
		}[self.filters.get('range')]

		if self.filters.get('based_on') == 'Number':
			self.query_result = frappe.db.get_list('Opportunity',filters=self.get_conditions(),fields=[select_1,select_2,duration]
				,group_by="{},{}".format(group_by_1,group_by_2),order_by=group_by_2)

		if self.filters.get('based_on') == 'Amount':
			self.query_result = frappe.db.get_list('Opportunity',filters=self.get_conditions(),fields=[select_1,select_2,duration,'currency'])
			self.convert_to_base_currency()
			dataframe = pandas.DataFrame.from_records(self.query_result)
			result = dataframe.groupby([pipeline_by,period_by],as_index=False)['amount'].sum()
			self.grouped_data = []

			for i in range(len(result['amount'])):
				self.grouped_data.append({pipeline_by : result[pipeline_by][i], period_by : result[period_by][i], 'amount': result['amount'][i]})
			self.query_result = self.grouped_data

		self.get_periodic_data()
		self.append_data(pipeline_by,period_by)

	def get_conditions(self):

		conditions = []
		if self.filters.get("opportunity_source"):
			conditions.append({"source": self.filters.get('opportunity_source')})
		if self.filters.get("opportunity_type"):
			conditions.append({'opportunity_type': self.filters.get('opportunity_type')})
		if self.filters.get("status"):
			conditions.append({'status': self.filters.get('status')})
		if self.filters.get("company"):
			conditions.append({'company': self.filters.get('company')})
		if self.filters.get("from_date") and self.filters.get("to_date"):
			conditions.append(['expected_closing','between',[self.filters.get("from_date"),self.filters.get("to_date")]])

		return conditions

	def get_chart_data(self):
		
		labels = values = []
		datasets = []

		self.append_to_dataset(values,datasets)
					
		for c in self.columns:
			if c['fieldname'] != "opportunity_owner" and c['fieldname'] != "sales_stage":
				labels.append(c['fieldname'])

		self.chart = {
			"data":{
				'labels': labels,
				'datasets': datasets
			},
			"type":"line"
		}

		return self.chart

	def get_periodic_data(self):
		self.periodic_data = frappe._dict()

		based_on = {
			'Number': 'count',
			'Amount': 'amount'
		}[self.filters.get('based_on')]

		pipeline_by = {
			'Owner': 'opportunity_owner',
			'Sales Stage': 'sales_stage'
		}[self.filters.get('pipeline_by')]

		range ={
			'Monthly': 'month',
			'Quaterly': 'quarter'
		}[self.filters.get('range')]

		for info in self.query_result:
			if self.filters.get('range') == 'Monthly':
				period = info.get(range)
			if self.filters.get('range') == 'Quaterly':
				period = "Q" + str(info.get('quarter'))

			value = info.get(pipeline_by)
			count = info.get(based_on)

			if self.filters.get('pipeline_by') == 'Owner':

				if value is None or value == '[]':
					temp = ["Not Assigned"]
				else:
					temp = json.loads(value)
				self.check_for_assigned_to(period,value,count,temp,info)

			else:
				self.insert_formatted_data(period,value,count,None)	

	def insert_formatted_data(self,period,value,val,temp):

		if temp:
			if len(temp) > 1:
				if self.filters.get("assigned_to"):
					for user in temp:
						if self.filters.get("assigned_to") == user:
							value = user
							self.periodic_data.setdefault(value,frappe._dict()).setdefault(period,0)
							self.periodic_data[value][period] += val
				else:
					for user in temp:
						value = user
						self.periodic_data.setdefault(value,frappe._dict()).setdefault(period,0)
						self.periodic_data[value][period] += val
			else:
				value = temp[0]
				self.periodic_data.setdefault(value,frappe._dict()).setdefault(period,0)
				self.periodic_data[value][period] += val

		else:
			value = value
			self.periodic_data.setdefault(value,frappe._dict()).setdefault(period,0)
			self.periodic_data[value][period] += val

	def check_for_assigned_to(self,period,value,count,temp,info):
		if self.filters.get("assigned_to"):
			for data in json.loads(info.get('opportunity_owner')):
				if data == self.filters.get("assigned_to"):
					self.insert_formatted_data(period,data,count,temp)
		else:
			self.insert_formatted_data(period,value,count,temp)

	def get_month_list(self):
		month_list= []
		current_date = date.today()
		month_number = date.today().month

		for month in range(month_number,13):
			month_list.append(current_date.strftime("%B"))
			current_date = current_date + relativedelta(months=1)
		
		return month_list

	def append_to_dataset(self,values,datasets):

		range_by = {
			'Monthly': 'month',
			'Quaterly': 'quarter'
		}[self.filters.get('range')]

		based_on = {
			'Amount': 'amount',
			'Number': 'count'
		}[self.filters.get('based_on')]

		if self.filters.get("range") == "Quaterly":
			list = [1,2,3,4]
			count = [0,0,0,0]

		if self.filters.get("range") == "Monthly":
			list = self.get_month_list()
			count = [0,0,0,0,0,0,0,0,0,0,0,0]

		for info in self.query_result:
			for i in range(len(list)):
				if info[range_by] == list[i]:
					count[i] = count[i] + info[based_on]
		values = count
		datasets.append({'name': based_on,'values':values})

	def append_data(self,pipeline_by,period_by):
		self.data = []
		for pipeline,period_data in iteritems(self.periodic_data):
			row = {pipeline_by : pipeline}
			for info in self.query_result:
				if self.filters.get('range') == 'Monthly':
					period = info.get(period_by)
				if self.filters.get('range') == 'Quaterly':
					period = "Q" + str(info.get(period_by))

				count = period_data.get(period,0.0)
				row[period] = count
			self.data.append(row)
				
		return self.data

	def get_default_currency(self):
		company = self.filters.get('company')
		return frappe.db.get_value('Company',company,['default_currency'])

	def get_currency_rate(self,from_currency,to_currency):
		cacheobj = frappe.cache()

		if cacheobj.get(from_currency):
			return flt(str(cacheobj.get(from_currency),'UTF-8'))

		else:
			value = get_exchange_rate(from_currency,to_currency)
			cacheobj.set(from_currency,value)
			return flt(str(cacheobj.get(from_currency),'UTF-8'))

	def convert_to_base_currency(self):
		default_currency = self.get_default_currency()
		for data in self.query_result:
			if data.get('currency') != default_currency:
				opportunity_currency = data.get('currency')
				value = self.get_currency_rate(opportunity_currency,default_currency)
				data['amount'] = data['amount'] * value