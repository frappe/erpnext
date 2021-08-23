# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import pandas
from frappe import _
from six import iteritems
import json
from frappe.utils import flt
from erpnext.setup.utils import get_exchange_rate


def execute(filters=None):
	return OpportunitySummaryBySalesStage(filters).run()

class OpportunitySummaryBySalesStage(object):

	def __init__(self,filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.get_columns()
		self.get_data()
		self.chart = {}
		self.get_chart_data()
		return self.columns, self.data, None, self.chart

	def get_columns(self):
		self.columns = []

		if self.filters.get('based_on') == "Opportunity Owner":
			self.columns.append({
				'label': _('Opportunity Owner'),
				'fieldname': 'opportunity_owner',
				'width':200
			})
		if self.filters.get('based_on') == "Source":
			self.columns.append({
				'label': _('Source'),
				'fieldname': 'source',
				'fieldtype': 'Link',
				'options':'Lead Source',
				'width': 200
			})
		if self.filters.get('based_on') == "Opportunity Type":
			self.columns.append({
				'label': _('Opportunity Type'),
				'fieldname': 'opportunity_type',
				'width': 200
			})
		
		self.sales_stage_list = frappe.db.get_list("Sales Stage",pluck="name")
		for sales_stage in self.sales_stage_list:
			if self.filters.get('data_based_on') == 'Number':
				self.columns.append({
					'label': _(sales_stage),
					'fieldname': sales_stage,
					'fieldtype': 'Int',
					'width':150
				})
			if self.filters.get('data_based_on') == 'Amount':
				self.columns.append({
					'label': _(sales_stage),
					'fieldname': sales_stage,
					'fieldtype': 'Currency',
					'width':150
				})

		return self.columns

	def get_data(self):
		self.data = []

		based_on = {
			'Opportunity Owner': "_assign",
			'Source': "source",
			'Opportunity Type': "opportunity_type"
		}[self.filters.get('based_on')]

		data_based_on = {
			'Number': "count(name) as count",
			'Amount': "opportunity_amount as amount",
		}[self.filters.get('data_based_on')]

		self.get_data_query(based_on,data_based_on)

		self.get_rows()
	
	def get_data_query(self,based_on,data_based_on):
		filter_data = self.filters.get('status')

		if filter_data:
			self.filters.update({'status':tuple(filter_data)})

		if self.filters.get('data_based_on') == 'Number':
			self.query_result = frappe.db.sql("""select sales_stage,{select},{sql},currency from tabOpportunity
				where {conditions} 
				group by sales_stage,{sql}""".format(conditions=self.get_conditions(),sql=based_on,select=data_based_on),self.filters,as_dict=1)

		if self.filters.get('data_based_on') == 'Amount':
			self.query_result = frappe.db.sql("""select sales_stage,{based_on},currency,{data_based_on} from tabOpportunity
				where {conditions} """.format(conditions=self.get_conditions(),based_on=based_on,data_based_on=data_based_on),self.filters,as_dict=1)

			self.convert_to_base_currency()
			dataframe = pandas.DataFrame.from_records(self.query_result)
			result = dataframe.groupby(['sales_stage',based_on],as_index=False)['amount'].sum()
			self.grouped_data = []

			for i in range(len(result['amount'])):
				self.grouped_data.append({'sales_stage': result['sales_stage'][i], based_on : result[based_on][i], 'amount': result['amount'][i]})
			
			self.query_result = self.grouped_data

	def get_rows(self):
		self.data = []
		self.get_formatted_data()
		
		for based_on,data in iteritems(self.formatted_data):

			row_based_on={
				'Opportunity Owner': 'opportunity_owner',
				'Source': 'source',
				'Opportunity Type': 'opportunity_type'
			}[self.filters.get('based_on')]

			row = {row_based_on: based_on}

			for d in self.query_result:
				sales_stage = d.get('sales_stage')
				row[sales_stage] = data.get(sales_stage)
				
			self.data.append(row)

	def get_formatted_data(self):
		self.formatted_data = frappe._dict()

		for d in self.query_result:
			data_based_on ={
				'Number': 'count',
				'Amount': 'amount'
			}[self.filters.get('data_based_on')]

			based_on ={
				'Opportunity Owner': '_assign',
				'Source': 'source',
				'Opportunity Type': 'opportunity_type'
			}[self.filters.get('based_on')]

			if self.filters.get("based_on") == "Opportunity Owner":
				if d.get(based_on) == '[]':
					temp = ["Not Assigned"]
				else:
					temp = json.loads(d.get(based_on))

				sales_stage = d.get('sales_stage')
				count = d.get(data_based_on)
				if temp:
					if len(temp) > 1:
						for value in temp:
							self.insert_formatted_data(value,sales_stage,count)
					else:
						value = temp[0]
						self.insert_formatted_data(value,sales_stage,count)	
			else:
				value = d.get(based_on)
				sales_stage = d.get('sales_stage')
				count = d.get(data_based_on)
				self.insert_formatted_data(value,sales_stage,count)

	def insert_formatted_data(self,based_on,sales_stage,data):
		self.formatted_data.setdefault(based_on,frappe._dict()).setdefault(sales_stage,0)
		self.formatted_data[based_on][sales_stage] += data
						
	def get_conditions(self):
		conditions = []
		if self.filters.get("opportunity_source"):
			conditions.append('source=%(opportunity_source)s')
		if self.filters.get("opportunity_type"):
			conditions.append('opportunity_type=%(opportunity_type)s')
		if self.filters.get("status"):
			conditions.append('status in %(status)s')
		if self.filters.get("company"):
			conditions.append('company=%(company)s')
		if self.filters.get("from_date"):
			conditions.append('transaction_date>=%(from_date)s')
		if self.filters.get("to_date"):
			conditions.append('transaction_date<=%(to_date)s')

		return "{}".format(" and ".join(conditions))

	def get_chart_data(self):
		labels = []
		datasets = []
		values = [0,0,0,0,0,0,0,0]
		for sales_stage in self.sales_stage_list:
			labels.append(sales_stage)

		options = {
			'Number': 'count',
			'Amount': 'amount'
		}[self.filters.get('data_based_on')]

		for data in self.query_result:
			for count in range(len(values)):
				if data['sales_stage'] == labels[count]:
					values[count] = values[count] + data[options]
		datasets.append({"name":options,'values':values})

		self.chart = {
			"data":{
				'labels': labels,
				'datasets': datasets
			},
			"type":"line"
		}

	def currency_conversion(self,from_currency,to_currency):
		cacheobj = frappe.cache()

		if cacheobj.get(from_currency):
			return flt(str(cacheobj.get(from_currency),'UTF-8'))

		else:
			value = get_exchange_rate(from_currency,to_currency)
			cacheobj.set(from_currency,value)
			return flt(str(cacheobj.get(from_currency),'UTF-8'))

	def get_default_currency(self):
		company = self.filters.get('company')
		return frappe.db.get_value('Company',company,['default_currency'])

	def convert_to_base_currency(self):
		default_currency = self.get_default_currency()
		for data in self.query_result:
			if data.get('currency') != default_currency:
				opportunity_currency = data.get('currency')
				value = self.currency_conversion(opportunity_currency,default_currency)
				data['amount'] = data['amount'] * value