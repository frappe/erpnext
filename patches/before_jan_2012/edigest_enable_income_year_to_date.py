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
from webnotes.model.doc import Document

def execute():
	companies_list = webnotes.conn.sql("SELECT company_name FROM `tabCompany`", as_list=1)
	for company in companies_list:
		if company and company[0]:
			edigest = Document('Email Digest', "Default Weekly Digest - " + company[0])
			if edigest:
				edigest.income_year_to_date = 1
				edigest.save()
