# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from controllers.trends	import get_columns,get_data

def execute(filters=None):
	if not filters: filters ={}
	data = []
	conditions = get_columns(filters, "Delivery Note")
	data = get_data(filters, conditions)
	
	return conditions["columns"], data 