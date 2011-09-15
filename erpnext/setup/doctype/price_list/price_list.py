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
		self.cl = []
	
	# validate currency
	def is_currency_valid(self, currency):
		if currency in self.cl:
			return 1
			
		if sql("select name from tabCurrency where name=%s", currency):
			self.cl.append(currency)
			return 1
		else:
			return 0
	
	# update prices in Price List
	def update_prices(self):
		import csv 
		data = csv.reader(self.get_csv_data().splitlines())
				
		updated = 0
		
		for line in data:
			if len(line)==3:
				# if item exists
				if sql("select name from tabItem where name=%s", line[0]):
					if self.is_currency_valid(line[2]):
						# if price exists
						ref_ret_detail = sql("select name from `tabRef Rate Detail` where parent=%s and price_list_name=%s and ref_currency=%s", \
							(line[0], self.doc.name, line[2]))
						if ref_ret_detail:
							sql("update `tabRef Rate Detail` set ref_rate=%s where name=%s", (line[1], ref_ret_detail[0][0]))
						else:
							d = Document('Ref Rate Detail')
							d.parent = line[0]
							d.parentfield = 'ref_rate_details'
							d.parenttype = 'Item'
							d.price_list_name = self.doc.name
							d.ref_rate = line[1]
							d.ref_currency = line[2]
							d.save(1)
						updated += 1
					else:
						msgprint("[Ignored] Unknown currency '%s' for Item '%s'" % (line[2], line[0]))
				else:
					msgprint("[Ignored] Did not find Item '%s'" % line[1])
			else:
				msgprint("[Ignored] Incorrect format: %s" % str(line))
		
		msgprint("<b>%s</b> items updated" % updated)

	# clear prices
	def clear_prices(self):
		cnt = sql("select count(*) from `tabRef Rate Detail` where price_list_name = %s", self.doc.name)
		sql("delete from `tabRef Rate Detail` where price_list_name = %s", self.doc.name)
		msgprint("%s prices cleared" % cnt[0][0])

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