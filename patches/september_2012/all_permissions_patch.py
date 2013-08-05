# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
def execute():
	web_cache_perms()
	stock_perms()
	project_perms()
	account_perms()
	
def web_cache_perms():
	webnotes.conn.sql("""update `tabDocPerm`
		set role='Guest' where parent='Web Cache' and role='All' and permlevel=0""")
		
def project_perms():
	webnotes.conn.sql("""delete from `tabDocPerm`
		where parent in ('Task', 'Project Activity') and role='All'""")

def stock_perms():
	webnotes.conn.sql("""delete from `tabDocPerm`
		where parent in ('Landed Cost Wizard', 
		'Sales and Purchase Return Tool') and role='All' and permlevel=0""")
		
def account_perms():
	# since it is a child doctype, it does not need permissions
	webnotes.conn.sql("""delete from tabDocPerm where parent='TDS Detail'""")
