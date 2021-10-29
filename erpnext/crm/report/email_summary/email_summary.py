# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from erpnext.crm.report.call_log_summary.call_log_summary import get_period_list, validate_filters, prepare_data, get_chart_data

def execute(filters=None):
	return EmailSummary(filters).run()
	columns, data = [], []
	return columns, data

class EmailSummary():
	def __init__(self, filters):
		self.filters = frappe._dict(filters or {})

	def run(self):
		validate_filters(self.filters.from_date, self.filters.to_date)
		columns = self.get_columns()
		data = prepare_data(columns, self.get_data())
		chart = get_chart_data(columns, data)
		columns.insert(0, {
            'fieldname': 'user',
            'label': _('{0} Owner').format(self.filters.reference_document_type),
            'fieldtype': 'Link',
            'options': 'User',
			'width': 200
        })
		return columns, data, None, chart

	def get_columns(self):
		return get_period_list(self.filters.from_date, self.filters.to_date, self.filters.frequency)

	def get_data(self):
		return frappe.db.sql(self.get_query(), as_dict=True, debug=1)

	def get_query(self):
		filters = self.filters

		join_field = """c.reference_doctype = '{0}' 
			AND c.reference_name = dt.name
			AND (c.creation BETWEEN '{1}' AND '{2}')
			""".format(filters.reference_document_type, filters.from_date, filters.to_date)

		if filters.reference_document_name:
			join_field += " AND c.reference_name = '{0}'".format(filters.reference_document_name)

		if filters.email_template_used:
			join_field += " AND c.email_template IS NOT NULL"

		if filters.company:
			join_field += " AND dt.company = '{0}'".format(filters.company)

		query = """SELECT c.name as name,
			DATE(c.creation) as creation, 
			dt._assign as assign,
			dt.name as reference_name
    		FROM (`tabCommunication` c 
			INNER JOIN `tab{0}` dt ON {1})
			""".format(filters.reference_document_type, join_field)

		return query