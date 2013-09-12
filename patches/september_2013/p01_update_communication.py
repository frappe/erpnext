# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import MySQLdb

def execute():
	webnotes.reload_doc("core", "doctype", "communication")
	webnotes.conn.sql("""update tabCommunication set communication_date = creation where 
		ifnull(communication_date, '')='' """)
	
	for doctype in ("Contact", "Lead", "Job Applicant", "Supplier", "Customer", "Quotation", "Sales Person", "Support Ticket"):
		try:
			fieldname = doctype.replace(" ", '_').lower()
			webnotes.conn.sql("""update tabCommunication
				set parenttype=%s, parentfield='communications', 
				parent=`%s` 
				where ifnull(`%s`, '')!=''""" % ("%s", fieldname, fieldname), doctype)
		except MySQLdb.OperationalError, e:
			if e.args[0] != 1054:
				raise e
