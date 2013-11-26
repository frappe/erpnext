# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	update_user_properties()
	update_permissions()
	webnotes.clear_cache()

def update_user_properties():
	webnotes.reload_doc("core", "doctype", "docfield")
	
	for d in webnotes.conn.sql("""select parent, defkey, defvalue from tabDefaultValue 
		where parent not in ('__global', 'Control Panel')""", as_dict=True):
		df = webnotes.conn.sql("""select options from tabDocField 
			where fieldname=%s and fieldtype='Link'""", d.defkey, as_dict=True)
		
		if df:
			webnotes.conn.sql("""update tabDefaultValue 
				set defkey=%s, parenttype='Restriction' 
				where defkey=%s and 
				parent not in ('__global', 'Control Panel')""", (df[0].options, d.defkey))
				
	# remove duplicate restrictions (if they exist)
	for d in webnotes.conn.sql("""select parent, defkey, substr(defvalue,0,10), 
		count(*) as cnt from tabDefaultValue 
		where parent not in ('__global', 'Control Panel') 
		group by parent, defkey, defvalue""", as_dict=1):
		if d.cnt > 1:
			webnotes.conn.sql("""delete from tabDefaultValue where parent=%s, defkey=%s, 
				defvalue=%s limit %s""", (d.parent, d.defkey, d.defvalue, d.cnt-1))
				
def update_permissions():
	# clear match conditions other than owner
	webnotes.conn.sql("""update tabDocPerm set `match`=''
		where ifnull(`match`,'') not in ('', 'owner')""")