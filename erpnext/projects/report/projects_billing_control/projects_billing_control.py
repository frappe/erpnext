# encoding: utf-8
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days
from datetime import datetime
import datetime
# import operator
import re
from datetime import date
from dateutil.relativedelta import relativedelta


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		_("Scope Item") + "::150",
		_("Item’s Value") + ":Currency:150",
		_("Billing Percentage (%)") + "::150",
		_("Billing Value") + ":Currency:150",
		_("Total Project Billing So Far") + "::150",
		_("Issue Invoice Request") + "::150"
		]


def get_conditions(filters):
	conditions = ""

	# if filters.get("when"): conditions += " and when= '{0}' ".format(filters.get('when'))
	# frappe.msgprint(conditions)
	return conditions


def get_data(filters):
	data = []
	# conditions = get_conditions(filters)
	li_list=frappe.db.sql("""select * from `tabProject Payment Schedule` where parent = '{0}' """.format(filters.project),as_dict=1)

	for asset in li_list:

		row = [
		asset.scope_item,
		asset.items_value,
		asset.billing_percentage,
		asset.billing_value,
		asset.total_billing_value,
		asset.total_billing_value
		]
		data.append(row)

	return data
