# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from six import iteritems
import json


def execute(filters=None):
	return OpportunitySummaryBySalesStage(filters).run()

class OpportunitySummaryBySalesStage(object):

	def __init__(self,filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()

		return self.columns,self.data,None,self.chart

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
			self.columns.append({
				'label': _(sales_stage),
				'fieldname': sales_stage,
				'width':150
			})

		return self.columns

	def get_data(self):
		self.data = []
		if self.filters.get('based_on') == "Opportunity Owner":
			sql = "_assign"
			self.get_data_query(sql)
		if self.filters.get('based_on') == "Source":
			sql = "source"
			self.get_data_query(sql)
		if self.filters.get('based_on') == "Opportunity Type":
			sql = "opportunity_type"
			self.get_data_query(sql)

		self.get_rows()
	
	def get_data_query(self,sql):
		filter_data = self.filters.get('status')
		
		if self.filters.get("data_based_on") == "Number":
			self.filters.update({'status':tuple(filter_data)})
			self.query_result = frappe.db.sql("""select sales_stage,count(name) as count,{sql} from tabOpportunity
			where {conditions} 
			group by sales_stage,{sql}""".format(conditions=self.get_conditions(),sql=sql),self.filters,as_dict=1)

		if self.filters.get("data_based_on") == "Amount":
			self.filters.update({'status':tuple(filter_data)})
			self.query_result = frappe.db.sql("""select sales_stage,sum(opportunity_amount) as amount,{sql} from tabOpportunity
			where {conditions} 
			group by sales_stage,{sql}""".format(conditions=self.get_conditions(),sql=sql),self.filters,as_dict=1)
		
	def get_rows(self):
		self.data = []
		self.get_formatted_data()
		currency_symbol = self.get_currency()
		
		for based_on,data in iteritems(self.formatted_data):
			if self.filters.get("based_on") == "Opportunity Owner":
				row = {'opportunity_owner': based_on}

				if self.filters.get("data_based_on") == "Number":
					for d in self.query_result:
						sales_stage = d.get('sales_stage')
						count = data.get(sales_stage)
						row[sales_stage] = count

				if self.filters.get("data_based_on") == "Amount":
					for d in self.query_result:
						sales_stage = d.get('sales_stage')
						amount = data.get(sales_stage)
						if amount:
							row[sales_stage] = str(amount) + currency_symbol

			if self.filters.get("based_on") == "Source":
				row = {'source': based_on}

				if self.filters.get("data_based_on") == "Number":
					for d in self.query_result:
						sales_stage = d.get('sales_stage')
						count = data.get(sales_stage)
						row[sales_stage] = count

				if self.filters.get("data_based_on") == "Amount":
					for d in self.query_result:
						sales_stage = d.get('sales_stage')
						amount = data.get(sales_stage)
						if amount:
							row[sales_stage] = str(amount) + currency_symbol

			if self.filters.get("based_on") == "Opportunity Type":
				row = {'opportunity_type': based_on}
		
				if self.filters.get("data_based_on") == "Number":
					for d in self.query_result:
						sales_stage = d.get('sales_stage')
						count = data.get(sales_stage)
						row[sales_stage] = count

				if self.filters.get("data_based_on") == "Amount":
					for d in self.query_result:
						sales_stage = d.get('sales_stage')
						amount = data.get(sales_stage)
						if amount:
							row[sales_stage] = str(amount) + currency_symbol

			self.data.append(row)

	def get_formatted_data(self):
		self.formatted_data = frappe._dict()

		for d in self.query_result:
			if self.filters.get("based_on") == "Opportunity Owner":
				if self.filters.get("data_based_on") == "Number":
					temp = json.loads(d.get("_assign"))
					if len(temp) > 1:
						sales_stage = d.get('sales_stage')
						count = d.get('count')
						for owner in temp:
							self.helper(owner,sales_stage,count)

					else:
						owner = temp[0]
						sales_stage = d.get('sales_stage')
						count = d.get('count')
						self.helper(owner,sales_stage,count)

				if self.filters.get("data_based_on") == "Amount":

					temp = json.loads(d.get("_assign"))
					if len(temp) > 1:
						sales_stage = d.get('sales_stage')
						amount = d.get('amount')
						for owner in temp:
							self.helper(owner,sales_stage,amount)

					else:
						owner = temp[0]
						sales_stage = d.get('sales_stage')
						amount = d.get('amount')
						self.helper(owner,sales_stage,amount)
						

			if self.filters.get("based_on") == "Source":
				if self.filters.get("data_based_on") == "Number":
					source = d.get('source')
					sales_stage = d.get('sales_stage')
					count = d.get('count')
					self.helper(source,sales_stage,count)

				if self.filters.get("data_based_on") == "Amount":
					source = d.get('source')
					sales_stage = d.get('sales_stage')
					amount = d.get('amount')
					self.helper(source,sales_stage,amount)

			if self.filters.get("based_on") == "Opportunity Type":
				if self.filters.get("data_based_on") == "Number":
					opportunity_type = d.get('opportunity_type')
					sales_stage = d.get('sales_stage')
					count = d.get('count')
					self.helper(opportunity_type,sales_stage,count)
					
				if self.filters.get("data_based_on") == "Amount":
					opportunity_type = d.get('opportunity_type')
					sales_stage = d.get('sales_stage')
					amount = d.get('amount')
					self.helper(opportunity_type,sales_stage,amount)

	def helper(self,based_on,sales_stage,data):
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

		if self.filters.get("data_based_on") == "Number":
			for data in self.query_result:
				for count in range(0,8):
					if data['sales_stage'] == labels[count]:
						values[count] = values[count] + data['count']
			datasets.append({"name":'Count','values':values})

		if self.filters.get("data_based_on") == "Amount":
			for data in self.query_result:
				for count in range(0,8):
					if data['sales_stage'] == labels[count]:
						values[count] = values[count] + data['amount']
			datasets.append({"name":'Amount','values':values})

		self.chart = {
			"data":{
				'labels': labels,
				'datasets': datasets
			},
			"type":"line"
		}

	def get_currency(self):
		company = self.filters.get('company')
		default_currency = frappe.db.get_value('Company',company,['default_currency'])
		return frappe.db.get_value('Currency',default_currency,['symbol'])