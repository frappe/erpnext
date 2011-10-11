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
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def get_field_id(self, doctype, fieldname):
		f = sql("select name, idx from tabDocField where parent=%s and fieldname=%s", (doctype, fieldname))
		if not f:
			f=sql("select name, idx from tabDocField where parent=%s and label=%s", (doctype, fieldname))
		if not f:
			return '__notfound__', 0
			#msgprint("No field found for %s" % fieldname)
			#raise Exception
		return f[0]

	def set_field_property(self, doctype, fieldname, property, value):
		f = self.get_field_id(doctype, fieldname)
		sql("update tabDocField set `%s`=%s where name=%s" % (property,'%s','%s'), (value, f[0]))
	
	def move_field(self, doctype, fieldname, before_field='', after_field=''):
		f1 = self.get_field_id(doctype, fieldname)
		
		# get new id
		new_idx = self.get_field_id(doctype, before_field or after_field)[1]
		if after_field: 
			new_idx = new_idx + 1
				
		# push fields down at new idx
		sql("update tabDocField set idx=idx+1 where idx>=%s and parent=%s", (new_idx, doctype))

		# push fields up at old idx
		sql("update tabDocField set idx=idx-1 where idx>%s and parent=%s", (f1[1], doctype))
		
		# set field idx
		sql("update tabDocField set idx=%s where name=%s", (new_idx, f1[0]))
	
	def delete_field(self, doctype, fieldname):
		sql("delete from tabDocField where name=%s limit 1", self.get_field_id(doctype, fieldname)[0])

	def delete_unnamed_field(self, doctype, after_field=''):
		f1 = self.get_field_id(doctype, after_field)
		
		if f1[0]=='__notfound__':
			return
		
		# check if truly un-named
		f2 = sql("select name, fieldname, label from tabDocField where idx=%s and parent=%s limit 1", (f1[1]+1, doctype))
		
		if not f2:
			return
		f2 = f2[0]
		
		if f2[1] or f2[2]:
			return
		else:
			sql("delete from tabDocField where name=%s limit 1", (f2[0]))

			# move fields up
			sql("update tabDocField set idx=idx-1 where idx>%s and parent=%s", (f1[1], doctype))
		
	def add_permission(self, doctype, role, level=0, read=0, write=0, create=0, submit=0, cancel=0, amend=0, match=''): 
		# check if exists
		pid = sql("select name from tabDocPerm where parent=%s and role=%s and permlevel=%s", (doctype, role, level))
		if pid:
			d = Document('DocPerm', pid[0][0])
		else:
			d = Document('DocPerm')
			d.parent = doctype
			d.parenttype = 'DocType'
			d.parentfield = 'permissions'
			
		d.permlevel = level
		d.role = role
		d.read = read
		d.write = write
		d.create = create
		d.submit = submit
		d.cancel = cancel
		d.amend = amend
		d.match = match
		
		d.save(new = (not d.name and 1 or 0))

	def delete_permission(self, doctype, role, level):
		sql("delete from `tabDocPerm` where role = '%s' and parent = '%s' and permlevel = '%s'" % (role, doctype, level))
