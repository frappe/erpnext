# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.permissions
import frappe.defaults

def execute():
	frappe.reload_doc("core", "doctype", "docperm")
	update_user_properties()
	update_user_match()
	add_employee_restrictions_to_leave_approver()
	update_permissions()
	remove_duplicate_restrictions()
	frappe.defaults.clear_cache()
	frappe.clear_cache()

def update_user_properties():
	frappe.reload_doc("core", "doctype", "docfield")
	
	for d in frappe.db.sql("""select parent, defkey, defvalue from tabDefaultValue
		where parent not in ('__global', 'Control Panel')""", as_dict=True):
		df = frappe.db.sql("""select options from tabDocField
			where fieldname=%s and fieldtype='Link'""", d.defkey, as_dict=True)
		
		if df:
			frappe.db.sql("""update tabDefaultValue
				set defkey=%s, parenttype='Restriction'
				where defkey=%s and
				parent not in ('__global', 'Control Panel')""", (df[0].options, d.defkey))

def update_user_match():
	import frappe.defaults
	doctype_matches = {}
	for doctype, match in frappe.db.sql("""select parent, `match` from `tabDocPerm`
		where `match` like %s and ifnull(`match`, '')!="leave_approver:user" """, "%:user"):
		doctype_matches.setdefault(doctype, []).append(match)
	
	for doctype, user_matches in doctype_matches.items():
		meta = frappe.get_meta(doctype)
		
		# for each user with roles of this doctype, check if match condition applies
		for user in frappe.db.sql_list("""select name from `tabUser`
			where enabled=1 and user_type='System User'"""):
			
			user_roles = frappe.get_roles(user)
			
			perms = meta.get({"doctype": "DocPerm", "permlevel": 0, 
				"role": ["in", [["All"] + user_roles]], "read": 1})

			# user does not have required roles
			if not perms:
				continue
			
			# assume match
			user_match = True
			for perm in perms:
				if not perm.match:
					# aha! non match found
					user_match = False
					break
			
			if not user_match:
				continue
			
			# if match condition applies, restrict that user
			# add that doc's restriction to that user
			for match in user_matches:
				for name in frappe.db.sql_list("""select name from `tab{doctype}`
					where `{field}`=%s""".format(doctype=doctype, field=match.split(":")[0]), user):
					
					frappe.defaults.add_default(doctype, name, user, "Restriction")
					
def add_employee_restrictions_to_leave_approver():
	from frappe.core.page.user_properties import user_properties
	
	# add restrict rights to HR User and HR Manager
	frappe.db.sql("""update `tabDocPerm` set `restrict`=1 where parent in ('Employee', 'Leave Application')
		and role in ('HR User', 'HR Manager') and permlevel=0 and `read`=1""")
	frappe.clear_cache()
	
	# add Employee restrictions (in on_update method)
	for employee in frappe.db.sql_list("""select name from `tabEmployee`
		where exists(select leave_approver from `tabEmployee Leave Approver`
			where `tabEmployee Leave Approver`.parent=`tabEmployee`.name)
		or ifnull(`reports_to`, '')!=''"""):
		
		frappe.get_doc("Employee", employee).save()

def update_permissions():
	# clear match conditions other than owner
	frappe.db.sql("""update tabDocPerm set `match`=''
		where ifnull(`match`,'') not in ('', 'owner')""")

def remove_duplicate_restrictions():
	# remove duplicate restrictions (if they exist)
	for d in frappe.db.sql("""select parent, defkey, defvalue,
		count(*) as cnt from tabDefaultValue
		where parent not in ('__global', 'Control Panel')
		group by parent, defkey, defvalue""", as_dict=1):
		if d.cnt > 1:
			# order by parenttype so that restriction does not get removed!
			frappe.db.sql("""delete from tabDefaultValue where `parent`=%s and `defkey`=%s and
				`defvalue`=%s order by parenttype limit %s""", (d.parent, d.defkey, d.defvalue, d.cnt-1))
