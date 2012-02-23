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

import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	#
	# load current banner
	#
	def onload(self):
		self.doc.header_html = webnotes.conn.get_value('Control Panel', None, 'client_name')
	
	#
	# on update
	#
	def validate(self):
		from webnotes.utils import cint
		if self.doc.file_list and cint(self.doc.set_from_attachment):
			self.set_html_from_image()

		# update control panel - so it loads new letter directly
		webnotes.conn.set_value('Control Panel', None, 'client_name', self.doc.header_html)
		 
		# clear the cache so that the new letter head is uploaded
		webnotes.conn.sql("delete from __SessionCache")

	#
	# set html for image
	#
	def set_html_from_image(self):
		file_name = self.doc.file_list.split(',')[0]
		self.doc.header_html = """<div>
<img style="max-height: 120px; max-width: 600px" src="files/%s"/>
</div>""" % file_name
