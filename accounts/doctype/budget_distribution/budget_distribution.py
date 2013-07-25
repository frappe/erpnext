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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import flt
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes import msgprint, _

class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc,self.doclist = doc,doclist
		
	def get_months(self):
		month_list = ['January','February','March','April','May','June','July','August','September',
		'October','November','December']
		idx =1
		for m in month_list:
			mnth = addchild(self.doc, 'budget_distribution_details',
				'Budget Distribution Detail', self.doclist)
			mnth.month = m or ''
			mnth.idx = idx
			idx += 1
			
	def validate(self):
		total = sum([flt(d.percentage_allocation, 2) for d in self.doclist.get(
			{"parentfield": "budget_distribution_details"})])
			
		if total != 100.0:
			msgprint(_("Percentage Allocation should be equal to ") + "100%", raise_exception=1)