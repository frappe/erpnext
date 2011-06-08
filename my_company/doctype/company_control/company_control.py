# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
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
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl
		
	# All roles of Role Master
	def get_all_roles(self):
		r_list=sql("select name from `tabRole` where name not in ('All','Guest','Administrator','Customer','Supplier') and docstatus != 2")
		if r_list[0][0]:
			r_list = [x[0] for x in r_list]
		return r_list
		
	# Get all permissions for given role	
	def get_permission(self,role):
		perm = sql("select distinct t1.`parent`, t1.`read`, t1.`write`, t1.`create`, t1.`submit`,t1.`cancel`,t1.`amend` from `tabDocPerm` t1, `tabDocType` t2 where t1.`role` ='%s' and t1.docstatus !=2 and ifnull(t1.permlevel, 0) = 0 and t1.`read` = 1 and t2.module != 'Recycle Bin' and t1.parent=t2.name " % role)
		return perm or ''

	# Get roles for given user
	def get_user_roles(self,usr):
		r_list=sql("select role from `tabUserRole` where parent=%s and role not in ('All','Guest')",usr)
		if r_list:
			return [r[0] for r in r_list]
		else:
			return ''

	# Update roles of given user
	def update_roles(self,arg):
		arg = eval(arg)
		sql("delete from `tabUserRole` where parenttype='Profile' and parent ='%s'" % (cstr(arg['usr'])))
		role_list = arg['role_list'].split(',')
		for r in role_list:
			pr=Document('UserRole')
			pr.parent = arg['usr']
			pr.parenttype = 'Profile'
			pr.role = r
			pr.parentfield = 'userroles'
			pr.save(1)
		sql("delete from __SessionCache where user=%s", cstr(arg['usr']))

	# Save profile
	def save_profile(self,arg):
		arg = eval(arg)
		p = Document('Profile', session['user'])
		for k in arg:
			p.fields[k] = arg[k]
		p.save()

	def update_profile_image(self, fid, fname):
		sql("update tabProfile set file_list = '%s,%s' where name='%s'" % (fname, fid, session['user']))
		

	def get_login_url(self):
		return session['data']['login_from']
		
	def get_user_info(self):
		
		usr = sql("select count(name) from tabProfile where docstatus != 2 and name not in ('Guest','Administrator')")
		usr = usr and usr[0][0] or 0
	
		ol = sql("select count(distinct t1.name) from tabProfile t1, tabSessions t2 where t1.name = t2.user and t1.name not in('Guest','Administrator') and TIMESTAMPDIFF(HOUR,t2.lastupdate,NOW()) <= 1 and t1.docstatus != 2 and t1.enabled=1")
		ol = ol and ol[0][0] or 0
		
		ac = sql("select count(name) from tabProfile where enabled=1 and docstatus != 2 and name not in ('Guest', 'Administrator')")
		ac = ac and ac[0][0] or 0
		
		inac = sql("select count(name) from tabProfile where (enabled=0 or enabled is null or enabled = '') and docstatus != 2 and name not in ('Guest','Administrator')")
		inac = inac and inac[0][0] or 0
		
		return usr, ol, ac, inac
		
	def get_sm_count(self)	:
		return sql("select count(t1.parent) from tabUserRole t1, tabProfile t2 where t1.role='System Manager' and t1.parent = t2.name and t2.enabled=1")[0][0] or 0
