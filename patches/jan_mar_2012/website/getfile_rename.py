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

def execute():
	"""rename from getfle"""
	l = [
		('Quotation Item', 'description'),
		('Sales Order Item', 'description'),
		('Delivery Note Item', 'description'),
		('Sales Invoice Item', 'description'),
		('Item', 'description_html'),
		('Letter Head', 'content')
	]
	
	import re
	
	for table in l:
		for item in webnotes.conn.sql("""select name, %s from `tab%s` 
			where %s like '%s'""" % (table[1], table[0], table[1], '%cgi-bin/getfile.cgi%')):
			txt = re.sub('\&acx=[^"\']*', '', item[1])\
				.replace('cgi-bin/getfile.cgi?name=', 'files/')\
				.replace('FileData/', 'FileData-')
			
			txt = get_file_id(txt)
			
			webnotes.conn.sql("""update `tab%s` set %s=%s where name=%s""" % \
				(table[0], table[1], '%s', '%s'), (txt, item[0]))
	
	# control panel, client name
	txt = webnotes.conn.get_value('Control Panel',None,'client_name')
	if txt:
		txt = get_file_id(txt)
		webnotes.conn.set_value('Control Panel', None, 'client_name', txt.replace('index.cgi?cmd=get_file&fname=', 'files/'))
	
def get_file_id(txt):
	"""old file links may be from fileid or filename"""
	import re
	match = re.search('files/([^"\']*)', txt)

	if not match:
		print txt
		return txt

	fname = match.groups()[0]
	if not fname.startswith('FileData'):
		fid = webnotes.conn.sql("""select name from `tabFile Data` 
			where file_name=%s""", fname)
		if fid:
			fid = fid[0][0].replace('/', '-')	
			txt = txt.replace(fname, fid)
	return txt
