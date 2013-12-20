# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	update_user_properties()
	update_user_match()
	update_permissions()
	remove_duplicate_restrictions()
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
				
def update_user_match():
	import webnotes.defaults
	doctype_matches = {}
	for doctype, match in webnotes.conn.sql("""select parent, `match` from `tabDocPerm`
		where `match` like %s""", "%:user"):
		doctype_matches.setdefault(doctype, []).append(match)
	
	for doctype, user_matches in doctype_matches.items():
		# get permissions of this doctype
		perms = webnotes.conn.sql("""select role, `match` from `tabDocPerm` 
			where parent=%s and permlevel=0 and `read`=1""", doctype, as_dict=True)
		
		# for each user with roles of this doctype, check if match condition applies
		for profile in webnotes.conn.sql_list("""select name from `tabProfile`
			where enabled=1 and user_type='System User'"""):
			
			roles = webnotes.get_roles(profile)
			
			user_match = False
			for perm in perms:
				if perm.role in roles and (perm.match and \
					(perm.match.endswith(":user") or perm.match.endswith(":profile"))):
					user_match = True
					break
			
			if not user_match:
				continue
			
			# if match condition applies, restrict that user
			# add that doc's restriction to that user
			for match in user_matches:
				for name in webnotes.conn.sql_list("""select name from `tab{doctype}`
					where `{field}`=%s""".format(doctype=doctype, field=match.split(":")[0]), profile):
					
					webnotes.defaults.add_default(doctype, name, profile, "Restriction")

def update_permissions():
	# clear match conditions other than owner
	webnotes.conn.sql("""update tabDocPerm set `match`=''
		where ifnull(`match`,'') not in ('', 'owner')""")
		
def remove_duplicate_restrictions():
	# remove duplicate restrictions (if they exist)
	for d in webnotes.conn.sql("""select parent, defkey, defvalue, 
		count(*) as cnt from tabDefaultValue 
		where parent not in ('__global', 'Control Panel') 
		group by parent, defkey, defvalue""", as_dict=1):
		if d.cnt > 1:
			webnotes.conn.sql("""delete from tabDefaultValue where parent=%s, defkey=%s, 
				defvalue=%s limit %s""", (d.parent, d.defkey, d.defvalue, d.cnt-1))