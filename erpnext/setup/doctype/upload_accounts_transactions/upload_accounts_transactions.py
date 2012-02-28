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

	# upload transactions
	def upload_accounts_transactions(self):
		import csv
		data = csv.reader(self.get_csv_data().splitlines())

		abbr = sql("select concat(' - ',abbr) as abbr from tabCompany where name=%s",self.doc.company)
		updated = 0
		jv_name=''
#		jv = Document('Journal Voucher')
		global line,jv,name,jv_go
		for line in data:
			if len(line)>=7: #Minimum no of fields
				if line[3]!=jv_name: #Create JV
					if jv_name!='':
						jv_go = get_obj('Journal Voucher',name, with_children=1)
						jv_go.validate()
						jv_go.on_submit()

					jv_name=line[3]
					jv = Document('Journal Voucher')
					jv.voucher_type = line[0]
					jv.naming_series = line[1]
					jv.voucher_date = formatdate(line[2])
					jv.posting_date = formatdate(line[2])
#					jv.name = line[3]
					jv.fiscal_year = self.doc.fiscal_year
					jv.company = self.doc.company
					jv.remark = len(line)==8 and line[3]+' '+line[7] or line[3]+' Uploaded Record'
					jv.docstatus=1
					jv.save(1)
					name=jv.name

					jc = addchild(jv,'entries','Journal Voucher Detail',0)
					jc.account = line[4]+abbr[0][0]
					jc.cost_center=len(line)==9 and line[8] or self.doc.default_cost_center
					if line[5]!='':
						jc.debit = line[5]
					else:
						jc.credit = line[6]
					jc.save()

				else: #Create JV Child
					jc = addchild(jv,'entries','Journal Voucher Detail',0)
					jc.account = line[4]+abbr[0][0]
					jc.cost_center=len(line)==9 and line[8] or self.doc.default_cost_center
					if line[5]!='':
						jc.debit = line[5]
					else:
						jc.credit = line[6]
					jc.save()
			else:
				msgprint("[Ignored] Incorrect format: %s" % str(line))
		if jv_name!='':
			jv_go = get_obj('Journal Voucher',name, with_children=1)
			jv_go.validate()
			jv_go.on_submit()

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
		
		# NOTE: Don't know why this condition exists
		if not isinstance(content, basestring) and hasattr(content, 'tostring'):
		  content = content.tostring()

		return content
