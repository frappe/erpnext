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

@webnotes.whitelist()
def get_sc_list(arg=None):
	"""return list of reports for the given module module"""	
	webnotes.response['values'] = webnotes.conn.sql("""select 
		distinct criteria_name, doc_type, parent_doc_type
		from `tabSearch Criteria` 
		where module='%(module)s' 
		and docstatus in (0, NULL)
		and ifnull(disabled, 0) = 0 
		order by criteria_name 
		limit %(limit_start)s, %(limit_page_length)s""" % webnotes.form_dict, as_dict=True)

@webnotes.whitelist()
def get_report_list():
	"""return list on new style reports for modules"""
	webnotes.response['values'] = webnotes.conn.sql("""select 
		distinct tabReport.name, tabReport.ref_doctype
		from `tabReport`, `tabDocType`
		where tabDocType.module='%(module)s' 
		and tabDocType.name = tabReport.ref_doctype
		and tabReport.docstatus in (0, NULL)
		order by tabReport.name 
		limit %(limit_start)s, %(limit_page_length)s""" % webnotes.form_dict, as_dict=True)