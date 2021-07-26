# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import frappe
from datetime import datetime
from dateutil.relativedelta import relativedelta
from six import iteritems

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
		if self.filters['range'] == "Monthly":
			
			current_date = datetime.date(datetime.now())
			current_month_number = int(current_date.strftime("%m"))
			
			for i in range(current_month_number,13):		
				self.columns.append(
					{
						'fieldname': current_date.strftime("%B"),
						'label': current_date.strftime("%B"),
						'width': 200
					}
				)
				current_date = current_date + relativedelta(months=1)

		elif self.filters['range'] == "Quaterly":

			for quarter in range(1,5):
				self.columns.append(
					{
						'fieldname': f"Q{quarter}",
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
		self.data = []
		if self.filters.get("range") == "Monthly":
			data = self.get_monthly_data()

		if self.filters.get("range") == "Quaterly":
			data = self.get_quaterly_data()

		return data

	def get_monthly_data(self):

		if self.filters.get("pipeline_by") == "Owner":
			select = '_assign as opportunity_owner'
			group_by = '_assign'
			
		if self.filters.get("pipeline_by") == "Sales Stage":
			select = 'sales_stage'
			group_by = 'sales_stage'

		if self.filters.get("based_on") == "Number":
			self.query_result = frappe.db.sql("""SELECT  COUNT(name) as count,{select},monthname(expected_closing) as month from tabOpportunity 
				where {conditions}
				GROUP BY {group_by},month(expected_closing) ORDER BY month(expected_closing)""".format(conditions=self.get_conditions(),select=select,group_by=group_by)
				,self.filters,as_dict=1)

			if self.filters.get("pipeline_by") == "Owner":
				self.get_periodic_data()
				for customer,period_data in iteritems(self.periodic_data):
					row = {'opportunity_owner': customer}
					for info in self.query_result:
						period = info.get('month')
						count  = period_data.get(period,0.0)
						row[period] = count
					self.data.append(row)
				
			
			if self.filters.get("pipeline_by") == "Sales Stage":
				self.get_periodic_data()
				for sales_stage,period_data in iteritems(self.periodic_data):
					row = {'sales_stage': sales_stage}
					for info in self.query_result:
						period = info.get('month')
						count  = period_data.get(period,0.0)
						row[period] = count
					self.data.append(row)

			return self.data

			
		if self.filters.get("based_on") == "Amount":
			self.query_result = frappe.db.sql("""SELECT  sum(opportunity_amount) as amount,{select},monthname(expected_closing) as month from tabOpportunity 
				where {conditions}
				GROUP BY {group_by},month(expected_closing) ORDER BY month(expected_closing)""".format(conditions=self.get_conditions(),select=select,group_by=group_by,)
				,self.filters,as_dict=1)

			if self.filters.get("pipeline_by") == "Owner":
				self.get_periodic_data()
				for user,period_data in iteritems(self.periodic_data):
					row = {'opportunity_owner': user}
					for info in self.query_result:
						period = info.get('month')
						count  = period_data.get(period,0.0)
						row[period] = count

					self.data.append(row)
			
			if self.filters.get("pipeline_by") == "Sales Stage":
				self.get_periodic_data()
				for sales_stage,period_data in iteritems(self.periodic_data):
					row = {'sales_stage': sales_stage}
					for info in self.query_result:
						period = info.get('month')
						count  = period_data.get(period,0.0)
						row[period] = count

					self.data.append(row)

			return self.data

	def get_quaterly_data(self):
		if self.filters.get("pipeline_by") == "Owner":
			select = '_assign as opportunity_owner'
			group_by = '_assign' 
		if self.filters.get("pipeline_by") == "Sales Stage":
			select = 'sales_stage'
			group_by = 'sales_stage'

		if self.filters.get("based_on") == "Number":
			self.query_result = frappe.db.sql("""select count(name) as count,{select},QUARTER(expected_closing) as quarter from tabOpportunity 
			where {conditions}
			group by {group_by},QUARTER(expected_closing) order by QUARTER(expected_closing)
			""".format(conditions=self.get_conditions(),select=select,group_by=group_by),self.filters,as_dict=1)

			if self.filters.get("pipeline_by") == "Owner":
				self.get_periodic_data()
				for customer,period_data in iteritems(self.periodic_data):
					row = {'opportunity_owner': customer}
					for info in self.query_result:
						period = "Q" + str(info.get('quarter'))
						count  = period_data.get(period,0.0)
						row[period] = count
					self.data.append(row)

				return self.data

			if self.filters.get("pipeline_by") == "Sales Stage":
				self.get_periodic_data()
				for customer,period_data in iteritems(self.periodic_data):
					row = {'sales_stage': customer}
					for info in self.query_result:
						period = "Q" + str(info.get('quarter'))
						count  = period_data.get(period,0.0)
						row[period] = count
					self.data.append(row)

				return self.data

		if self.filters.get("based_on") == "Amount":
			self.query_result = frappe.db.sql("""select sum(opportunity_amount) as amount,{select},QUARTER(expected_closing) as quarter from tabOpportunity 
			where {conditions}
			group by {group_by},QUARTER(expected_closing) order by QUARTER(expected_closing)
			""".format(conditions=self.get_conditions(),select=select,group_by=group_by),self.filters,as_dict=1)

			if self.filters.get("pipeline_by") == "Owner":
				self.get_periodic_data()
				for customer,period_data in iteritems(self.periodic_data):
					row = {'opportunity_owner': customer}
					for info in self.query_result:
						period = "Q" + str(info.get('quarter'))
						count  = period_data.get(period,0.0)
						row[period] = count
					self.data.append(row)

			if self.filters.get("pipeline_by") == "Sales Stage":
				self.get_periodic_data()
				for sales_stage,period_data in iteritems(self.periodic_data):
					row = {'sales_stage': sales_stage}
					for info in self.query_result:
						period = "Q" + str(info.get('quarter'))
						count  = period_data.get(period,0.0)
						row[period] = count
					self.data.append(row)

			return self.data
			
	def get_conditions(self):
		current_date =  datetime.date(datetime.now())
		conditions = []
		if self.filters.get("opportunity_source"):
			conditions.append('source=%(opportunity_source)s')
		if self.filters.get("opportunity_type"):
			conditions.append('opportunity_type=%(opportunity_type)s')
		if self.filters.get("status"):
			conditions.append('status=%(status)s')
		if self.filters.get("company"):
			conditions.append('company=%(company)s')
		if self.filters.get("from_date"):
			conditions.append('expected_closing>=%(from_date)s')
		if self.filters.get("to_date"):
			conditions.append('expected_closing<=%(to_date)s')

		if not self.filters.get("from_date") and not self.filters.get("to_date") and self.filters.get("Monthly"):
			conditions.append('expected_closing between {cd} and {dd}'.format(cd = current_date
		,dd= current_date + relativedelta(months=1) + relativedelta(months=1)))

		return "{}".format(" and ".join(conditions))

	def get_chart_data(self):
		labels = []
		values = []
		quarter_list = [1,2,3,4]
		count = [0,0,0,0]
		count_month = [0,0,0,0,0,0,0,0,0,0,0,0]
		datasets = []
		month_list = []
		current_date = datetime.date(datetime.now())
		current_month_number = int(current_date.strftime("%m"))

		for month in range(current_month_number,13):
			month_list.append(current_date.strftime("%B"))
			current_date = current_date + relativedelta(months=1)
	
		if self.filters.get("range") == "Quaterly" and self.filters.get("based_on") == "Amount":
			for info in self.query_result:
				for q in range(0,len(quarter_list)):
					if info['quarter'] == quarter_list[q]:
						count[q] = count[q] + info['amount']
			values = count
			datasets.append({'name':'Amount','values':values})
			

		if self.filters.get("range") == "Quaterly" and self.filters.get("based_on") == "Number":
			for info in self.query_result:
				for q in range(0,len(quarter_list)):
					if info['quarter'] == quarter_list[q]:
						count[q] = count[q] + info['count']
			values = count
			datasets.append({'name':'Number','values':values})

		if self.filters.get("range") == "Monthly" and self.filters.get("based_on") == "Amount":
			for info in self.query_result:
				for m in range(0,len(month_list)):
					if info['month'] == month_list[m]:
						count_month[m] = count_month[m] + info['amount']
			values = count_month
			datasets.append({'name':'Amount','values':values})


		if self.filters.get("range") == "Monthly" and self.filters.get("based_on") == "Number":
			for info in self.query_result:
				for m in range(0,len(month_list)):
					if info['month'] == month_list[m]:
						count_month[m] = count_month[m] + info['count']
			values = count_month
			datasets.append({'name':'Count','values':values})
					

		for c in self.columns:
			if c['fieldname'] == "opportunity_owner" or c['fieldname'] == "sales_stage":
				pass
			else:
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

		for info in self.query_result:
			if self.filters.get("range") == "Monthly" and self.filters.get("based_on") == "Number" and self.filters.get("pipeline_by") == "Owner":
				period = info.get('month')
				value = info.get('opportunity_owner')
				count = info.get('count')
				temp = json.loads(value)

				if self.filters.get("assigned_to"):
					for data in json.loads(info.get('opportunity_owner')):
						if data == self.filters.get("assigned_to"):
							self.helper(period,data,count,temp)
				else:
					self.helper(period,value,count,temp)							

				
			if self.filters.get("range") == "Monthly" and self.filters.get("based_on") == "Number" and self.filters.get("pipeline_by") == "Sales Stage":
				period = info.get('month')
				value = info.get('sales_stage')
				count = info.get('count')
				self.helper(period,value,count,None)


			if self.filters.get("range") == "Monthly" and self.filters.get("based_on") == "Amount" and self.filters.get("pipeline_by") == "Sales Stage":
				period = info.get('month')
				value = info.get('sales_stage')
				amount = info.get('amount')
				self.helper(period,value,amount,None)


			if self.filters.get("range") == "Monthly" and self.filters.get("based_on") == "Amount" and self.filters.get("pipeline_by") == "Owner":
				period = info.get('month')
				value = info.get('opportunity_owner')
				amount = info.get('amount')
				temp = json.loads(value)

				if self.filters.get("assigned_to"):
					for data in json.loads(info.get('opportunity_owner')):
						if data == self.filters.get("assigned_to"):
							self.helper(period,data,amount,temp)
				else:
					self.helper(period,value,amount,temp)	

			if self.filters.get("range") == "Quaterly" and self.filters.get("based_on") == "Number" and self.filters.get("pipeline_by") == "Owner":
				period = "Q" + str(info.get('quarter'))
				value = info.get('opportunity_owner')
				count = info.get('count')
				temp = json.loads(value)

				if self.filters.get("assigned_to"):
					for data in json.loads(info.get('opportunity_owner')):
						if data == self.filters.get("assigned_to"):
							self.helper(period,data,count,temp)
				else:
					self.helper(period,value,count,temp)							

			if self.filters.get("range") == "Quaterly" and self.filters.get("based_on") == "Number" and self.filters.get("pipeline_by") == "Sales Stage":
				period = "Q" + str(info.get('quarter'))
				value = info.get('sales_stage')
				count = info.get('count')
				self.helper(period,value,count,None)


			if self.filters.get("range") == "Quaterly" and self.filters.get("based_on") == "Amount" and self.filters.get("pipeline_by") == "Owner":
				period = "Q" + str(info.get('quarter'))
				value = info.get('opportunity_owner')
				amount = info.get('amount')
				temp = json.loads(value)

				if self.filters.get("assigned_to"):
					for data in json.loads(info.get('opportunity_owner')):
						if data == self.filters.get("assigned_to"):
							self.helper(period,data,amount,temp)
				else:
					self.helper(period,value,amount,temp)	
			
			if self.filters.get("range") == "Quaterly" and self.filters.get("based_on") == "Amount" and self.filters.get("pipeline_by") == "Sales Stage":
				period = "Q" + str(info.get('quarter'))
				value = info.get('sales_stage')
				amount = info.get('amount')
				self.helper(period,value,amount,None)

	def helper(self,period,value,val,temp):

		if temp:
			if len(temp) > 1:
				if self.filters.get("assigned_to"):
					print(temp)
					for user in temp:
						if self.filters.get("assigned_to") == user:
							value = user
							self.periodic_data.setdefault(value,frappe._dict()).setdefault(period,0.0)
							self.periodic_data[value][period]= val
				else:
					for user in temp:
						value = user
						self.periodic_data.setdefault(value,frappe._dict()).setdefault(period,0.0)
						self.periodic_data[value][period]= val
			else:
				value = temp[0]
				self.periodic_data.setdefault(value,frappe._dict()).setdefault(period,0.0)
				self.periodic_data[value][period]= val

		else:
			self.periodic_data.setdefault(value,frappe._dict()).setdefault(period,0.0)
			self.periodic_data[value][period]= val