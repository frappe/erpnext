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
	
	# bulk rename
	def do_rename(self):
		import csv 
		data = csv.reader(self.get_csv_data().splitlines())
		
		updated = 0
				
		msgprint(self.doc.rename_doctype)
		
		if self.doc.rename_doctype == 'Account':
			for line in data:
				if len(line)==2:
					rec = sql("select tc.abbr, ta.name from `tabAccount` ta, `tabCompany` tc where ta.company = tc.name and ta.account_name = %s", line[0], as_dict=1)
					if rec:										
						new_name = line[1] + ' - ' + rec[0]['abbr']						
						
						webnotes.conn.begin()
						webnotes.model.rename(self.doc.rename_doctype, rec[0]['name'], new_name)						
						sql("update `tabAccount` set account_name = '%s' where name = '%s'" %(line[1],new_name))						
						webnotes.conn.commit()												
						
						updated += 1			
				else:
					msgprint("[Ignored] Incorrect format: %s" % str(line))		
		else:		
			for line in data:
				if len(line)==2:
				
					webnotes.conn.begin()				

					obj = get_obj(self.doc.rename_doctype, line[0])
					if hasattr(obj, 'on_rename'):
						obj.on_rename(line[1],line[0])			

					webnotes.model.rename(self.doc.rename_doctype, line[0], line[1])
					
					webnotes.conn.commit()
						
					updated += 1
				else:
					msgprint("[Ignored] Incorrect format: %s" % str(line))
		
		
		msgprint("<b>%s</b> items updated" % updated)		

	# Update CSV data
	def get_csv_data(self):
		if not self.doc.file_list:
		  msgprint("File not attached!")
		  raise Exception

		fid = self.doc.file_list.split(',')[1]
		  
		from webnotes.utils import file_manager
		fn, content = file_manager.get_file(fid)
		
		if not type(content) == str:
		  content = content.tostring()

		return content
