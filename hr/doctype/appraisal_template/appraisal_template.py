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
from webnotes import _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.doc.total_points = 0
		for d in self.doclist.get({"doctype":"Appraisal Template Goal"}):
			self.doc.total_points += int(d.per_weightage or 0)
		
		if int(self.doc.total_points) != 100:
			webnotes.msgprint(_("Total (sum of) points distribution for all goals should be 100.") \
				+ " " + _("Not") + " " + str(self.doc.total_points),
				raise_exception=True)