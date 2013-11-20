# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	for dt in webnotes.conn.sql("""select distinct parent from tabDocField 
		where fieldname='file_list'"""):
		try:
			webnotes.conn.sql("""update `tab%s` set file_list = 
				replace(file_list, "-", "")""" % dt[0])
		except Exception, e:
			if e.args[0]!=1146: raise