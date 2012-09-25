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
from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist
    self.prefix = is_testing and 'test' or 'tab'

  def validate(self):
    import string
  
    if not (self.doc.address_line1)  and not (self.doc.address_line2) and not (self.doc.city) and not (self.doc.state) and not (self.doc.country) and not (self.doc.pincode):
      return "Please enter address"
      
    else:
      address =["address_line1", "address_line2", "city", "state", "country", "pincode"]
      comp_address=''
      for d in address:
        if self.doc.fields[d]:
          comp_address += self.doc.fields[d] + "\n"
      self.doc.address = comp_address

  def check_state(self):
    return "\n" + "\n".join([i[0] for i in sql("select state_name from `tabState` where `tabState`.country='%s' " % self.doc.country)])
    
  def get_contacts(self,nm):
    if nm:
      contact_details =convert_to_lists(sql("select name, CONCAT(IFNULL(first_name,''),' ',IFNULL(last_name,'')),contact_no,email_id from `tabContact` where sales_partner = '%s'"%nm))
      return contact_details
    else:
      return ''