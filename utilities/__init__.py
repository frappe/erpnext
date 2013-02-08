# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
from webnotes.utils import cint, comma_or

@webnotes.whitelist()
def get_sc_list(arg=None):
	"""return list of reports for the given module module"""
	limit_start = webnotes.form_dict.get("limit_start")
	limit_page_length = webnotes.form_dict.get("limit_page_length")
	module = webnotes.form_dict.get("module")
	
	webnotes.response['values'] = webnotes.conn.sql("""
		select distinct criteria_name, doc_type, parent_doc_type
		from `tabSearch Criteria` 
		where module=%s 
			and docstatus in (0, NULL)
			and ifnull(disabled, 0) = 0 
			order by criteria_name 
			limit %s, %s""" % \
		("%s", cint(limit_start), cint(limit_page_length)), (module,), as_dict=True)

@webnotes.whitelist()
def get_report_list():
	"""return list on new style reports for modules"""
	limit_start = webnotes.form_dict.get("limit_start")
	limit_page_length = webnotes.form_dict.get("limit_page_length")
	module = webnotes.form_dict.get("module")
	
	webnotes.response['values'] = webnotes.conn.sql("""
		select distinct tabReport.name, tabReport.ref_doctype, 
			if(ifnull(tabReport.query, '')!='', 1, 0) as is_query_report
		from `tabReport`, `tabDocType`
		where tabDocType.module=%s
			and tabDocType.name = tabReport.ref_doctype
			and tabReport.docstatus in (0, NULL)
			and ifnull(tabReport.disabled,0) != 1
			order by tabReport.name 
			limit %s, %s""" % \
		("%s", cint(limit_start), cint(limit_page_length)), (module,), as_dict=True)

def validate_status(status, options):
	if status not in options:
		msgprint(_("Status must be one of ") + comma_or(options), raise_exception=True)

def build_filter_conditions(filters):
	conditions, filter_values = [], []
	for key in filters:
		conditions.append('`' + key + '` = %s')
		filter_values.append(filters[key])

	conditions = conditions and " and " + " and ".join(conditions) or ""
	return conditions, filter_values