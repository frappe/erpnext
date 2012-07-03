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

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
		
	
	# Get Roles and Modules on loading Permission Engine
	# ----------------------------------------------------- 
	def get_doctype_list(self):
		ret = sql("""SELECT `name` FROM tabDocType 
			WHERE ifnull(docstatus,0)=0
			AND ifnull(istable,0)=0
			AND ifnull(issingle,0)=0
			AND (`module` NOT IN ('System','Utilities','Setup Masters','Roles','Recycle Bin','Mapper','Application Internal','Development', 'Core')
			OR name IN ('Contact', 'Address'))
			ORDER BY `name` ASC""")
		
		rl = [''] + [a[0] for a in sql("select name from tabRole where ifnull(docstatus,0)=0")]
		
		return {'doctypes': [r[0] for r in ret], 'roles': rl}
		

	# Get Perm Level, Perm type of Doctypes of Module and Role Selected
	# -------------------------------------------------------------------
	def get_permissions(self,doctype):
		import webnotes.model.doctype
		doclist = webnotes.model.doctype.get(doctype, form=0)
		
		ptype = [{
				'role': perm.role,
				'permlevel': cint(perm.permlevel),
				'read': cint(perm.read),
				'write': cint(perm.write),
				'create': cint(perm.create),
				'cancel': cint(perm.cancel),
				'submit': cint(perm.submit),
				'amend': cint(perm.amend),
				'match': perm.match
				} for perm in sorted(doclist,
					key=lambda d: [d.fields.get('permlevel'),
						d.fields.get('role')]) if perm.doctype=='DocPerm']

		fl = ['', 'owner'] + [d.fieldname for d in doclist \
				if d.doctype=='DocField' and ((d.fieldtype=='Link' \
				and cstr(d.options)!='') or (d.fieldtype=='Select' and
					'link:' in cstr(d.options).lower()))]

		return {
			'perms':ptype,
			'fields':fl,
			'is_submittable': doclist[0].fields.get('is_submittable')
		}
		
	# get default values
	# ------------------
	def get_defaults(self, arg):
		match_key, with_profiles = arg.split('~~~')
		
		pl = ol = []
	
		# defaults
		dl = [a for a in sql("select parent, ifnull(parenttype,'') as parenttype, ifnull(defvalue,'') as defvalue from tabDefaultValue where defkey=%s order by parenttype desc, parent asc", match_key, as_dict=1)]

		# options
		tn = sql("select options from tabDocField where fieldname=%s and fieldtype='Link' and docstatus=0 limit 1", match_key)[0][0]
		ol = [''] + [a[0] for a in sql("select name from `tab%s` where ifnull(docstatus,0)=0" % tn)]

		# roles
		if with_profiles=='Yes':			
			# profiles
			pl = [''] + [a[0] for a in sql("select name from tabProfile where ifnull(enabled,0)=1")]
	

		return {'dl':dl, 'pl':pl, 'ol':ol}

	# delete default
	# ----------------------
	def delete_default(self, arg):
		parent, defkey, defvalue = arg.split('~~~')
		sql("delete from tabDefaultValue where parent=%s and defkey=%s and defvalue=%s", (parent, defkey, defvalue))

	# add default
	# ----------------------
	def add_default(self, arg):
		parent, parenttype, defkey, defvalue = arg.split('~~~')

		if sql("select name from tabDefaultValue where parent=%s and defkey=%s and defvalue=%s", (parent, defkey, defvalue)):
			msgprint("This rule already exists!")
			return
					
		dv = Document('DefaultValue')
		dv.parent = parent
		dv.parenttype = parenttype
		dv.parentfield = 'defaults'
		dv.defkey = defkey
		dv.defvalue = defvalue
		dv.save(1)
		return dv.fields

	# Add Permissions
	# ----------------------
	def add_permission(self,args=''):
		parent, role, level = eval(args)
		if sql("select name from tabDocPerm where parent=%s and role=%s and permlevel=%s", (parent, role, level)):
			msgprint("This permission rule already exists!")
			return
		
		d = Document('DocPerm')
		d.parent = parent
		d.parenttype = 'DocType'
		d.parentfield = 'permissions'
		d.role = role
		d.permlevel = cint(level)
		d.docstatus = 0
		d.save(1)
		
		sql("update tabDocType set modified = %s where name = %s",(now(), parent))


	# Update Permissions
	# ----------------------
	def update_permissions(self,args=''):
		args = eval(args)
		di = args['perm_dict']
		doctype_keys = di.keys()	# ['Opportunity','Competitor','Zone','State']
		for parent in doctype_keys:
			for permlevel in di[parent].keys():
				for role in di[parent][permlevel].keys(): 
				
					if role:
				
						# check if Permissions for that perm level and Role exists
						exists = sql("select name from tabDocPerm where parent = %s and role = %s and ifnull(permlevel, 0) = %s",(parent, role, cint(permlevel)))
	
						# Get values of dictionary of Perm Level
						pd = di[parent][permlevel][role]

						# update
						if exists and (1 in pd.values()):
							sql("update tabDocPerm set `read` = %s, `write` = %s, `create` = %s, `submit` = %s, `cancel` = %s, `amend` = %s, `match`=%s where parent = %s and role = %s and permlevel = %s",(pd['read'],pd['write'],pd['create'],pd['submit'],pd['cancel'],pd['amend'], pd.get('match'), parent, role, permlevel))
							
						# new
						elif not exists and (1 in pd.values()):

							ch = Document('DocPerm')
							ch.parentfield = 'permissions'
							ch.parenttype = 'DocType'
							ch.parent = parent
							ch.role = role
							ch.permlevel = cint(permlevel)
							for key in pd.keys():
								ch.fields[key] = pd.get(key, None)
							ch.save(1)
	
						# delete
						elif exists and (1 not in pd.values()):
							sql("delete from tabDocPerm where parent = %s and role = %s and ifnull(permlevel,0) = %s",(parent, role, cint(permlevel)))
						
						sql("update tabDocType set modified = %s where name = %s",(now(), parent))


		from webnotes.utils.cache import CacheItem
		CacheItem(parent).clear()		

		msgprint("Permissions Updated")
				
	# Get Fields based on DocType and Permlevel
	# ----------------------------------------------
	def get_fields(self, args = ''):
		ret = {}
		args = eval(args)
		table_fields_dict = {}
		table_exists = sql("Select options from tabDocField where fieldtype = 'Table' and parent = %s",args['dt'])
		if table_exists:
			for d in table_exists:
				table_fields_dict[d[0]]= sql("select label,fieldtype,fieldname,options from tabDocField where parent = %s and permlevel = %s",(d[0],args['permlevel']),as_dict = 1)
			
		parent_fields_dict = sql("select label, fieldtype, fieldname, options from tabDocField where parent = %s and permlevel = %s and fieldtype not in ('Section Break','Column Break')",(args['dt'],args['permlevel']),as_dict = 1)
		
		ret['parent_fields_dict'] = parent_fields_dict
		ret['table_fields_dict'] = table_fields_dict
	 
		return ret
		
