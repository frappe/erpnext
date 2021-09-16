# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import json

import frappe
import pandas
from frappe import _
from frappe.utils import flt
from six import iteritems

from erpnext.setup.utils import get_exchange_rate


def execute(filters=None):
	return OpportunitySummaryBySalesStage(filters).run()

class OpportunitySummaryBySalesStage(object):
	def __init__(self,filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()
		return self.columns, self.data, None, self.chart

	def get_columns(self):
		self.columns = []

		if self.filters.get('based_on') == 'Opportunity Owner':
			self.columns.append({
				'label': _('Opportunity Owner'),
				'fieldname': 'opportunity_owner',
				'width': 200
			})

		if self.filters.get('based_on') == 'Source':
			self.columns.append({
				'label': _('Source'),
				'fieldname': 'source',
				'fieldtype': 'Link',
				'options': 'Lead Source',
				'width': 200
			})

		if self.filters.get('based_on') == 'Opportunity Type':
			self.columns.append({
				'label': _('Opportunity Type'),
				'fieldname': 'opportunity_type',
				'width': 200
			})

		self.set_sales_stage_columns()

	def set_sales_stage_columns(self):
		self.sales_stage_list = frappe.db.get_list('Sales Stage', pluck='name')

		for sales_stage in self.sales_stage_list:
			if self.filters.get('data_based_on') == 'Number':
				self.columns.append({
					'label': _(sales_stage),
					'fieldname': sales_stage,
					'fieldtype': 'Int',
					'width': 150
				})

			elif self.filters.get('data_based_on') == 'Amount':
				self.columns.append({
					'label': _(sales_stage),
					'fieldname': sales_stage,
					'fieldtype': 'Currency',
					'width': 150
				})

	def get_data(self):
		self.data = []

		based_on = {
			'Opportunity Owner': '_assign',
			'Source': 'source',
			'Opportunity Type': 'opportunity_type'
		}[self.filters.get('based_on')]

		data_based_on = {
			'Number': 'count(name) as count',
			'Amount': 'opportunity_amount as amount',
		}[self.filters.get('data_based_on')]

		self.get_data_query(based_on, data_based_on)

		self.get_rows()

	def get_data_query(self, based_on, data_based_on):
		if self.filters.get('data_based_on') == 'Number':
			group_by = '{},{}'.format('sales_stage', based_on)
			self.query_result = frappe.db.get_list('Opportunity',
				filters=self.get_conditions(),
				fields=['sales_stage', data_based_on, based_on],
				group_by=group_by
			)

		elif self.filters.get('data_based_on') == 'Amount':
			self.query_result = frappe.db.get_list('Opportunity',
				filters=self.get_conditions(),
				fields=['sales_stage', based_on, data_based_on, 'currency']
			)

			self.convert_to_base_currency()

			dataframe = pandas.DataFrame.from_records(self.query_result)
			dataframe.replace(to_replace=[None], value='Not Assigned', inplace=True)
			result = dataframe.groupby(['sales_stage', based_on], as_index=False)['amount'].sum()

			self.grouped_data = []

			for i in range(len(result['amount'])):
				self.grouped_data.append({
					'sales_stage': result['sales_stage'][i],
					based_on : result[based_on][i],
					'amount': result['amount'][i]
				})

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

			if self.filters.get('based_on') == 'Opportunity Owner':
				if d.get(based_on) == '[]' or d.get(based_on) is None or d.get(based_on) == 'Not Assigned':
					assignments = ['Not Assigned']
				else:
					assignments = json.loads(d.get(based_on))

				sales_stage = d.get('sales_stage')
				count = d.get(data_based_on)

				if assignments:
					if len(assignments) > 1:
						for assigned_to in assignments:
							self.set_formatted_data_based_on_sales_stage(assigned_to, sales_stage, count)
					else:
						assigned_to = assignments[0]
						self.set_formatted_data_based_on_sales_stage(assigned_to, sales_stage, count)
			else:
				value = d.get(based_on)
				sales_stage = d.get('sales_stage')
				count = d.get(data_based_on)
				self.set_formatted_data_based_on_sales_stage(value, sales_stage, count)

	def set_formatted_data_based_on_sales_stage(self, based_on, sales_stage, count):
		self.formatted_data.setdefault(based_on, frappe._dict()).setdefault(sales_stage, 0)
		self.formatted_data[based_on][sales_stage] += count

	def get_conditions(self):
		filters = []

		if self.filters.get('company'):
			filters.append({'company': self.filters.get('company')})

		if self.filters.get('opportunity_type'):
			filters.append({'opportunity_type': self.filters.get('opportunity_type')})

		if self.filters.get('opportunity_source'):
			filters.append({'source': self.filters.get('opportunity_source')})

		if self.filters.get('status'):
			filters.append({'status': ('in',self.filters.get('status'))})

		if self.filters.get('from_date') and self.filters.get('to_date'):
			filters.append(['transaction_date', 'between', [self.filters.get('from_date'), self.filters.get('to_date')]])

		return filters

	def get_chart_data(self):
		labels = []
		datasets = []
		values = [0] * 8

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

		datasets.append({'name':options, 'values':values})

		self.chart = {
			'data':{
				'labels': labels,
				'datasets': datasets
			},
			'type':'line'
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
		return frappe.db.get_value('Company', company, 'default_currency')

	def convert_to_base_currency(self):
		default_currency = self.get_default_currency()
		for data in self.query_result:
			if data.get('currency') != default_currency:
				opportunity_currency = data.get('currency')
				value = self.currency_conversion(opportunity_currency,default_currency)
				data['amount'] = data['amount'] * value