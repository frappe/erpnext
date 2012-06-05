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
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist
    self.nsm_parent_field = 'parent_territory'

  def check_state(self):
    return "\n" + "\n".join([i[0] for i in sql("select state_name from `tabState` where `tabState`.country='%s' " % self.doc.country)])

       

  # update Node Set Model
  def update_nsm_model(self):
    import webnotes
    import webnotes.utils.nestedset
    webnotes.utils.nestedset.update_nsm(self)

  # ON UPDATE
  #--------------------------------------
  def on_update(self):
  
    # update nsm
    self.update_nsm_model()  
    


  def validate(self): 
    if self.doc.lft and self.doc.rgt:
      res = sql("select name from `tabTerritory` where is_group = 'Yes' and docstatus!= 2 and name ='%s' and name !='%s'"%(self.doc.parent_territory,self.doc.territory_name))
      if not res:
        msgprint("Please enter proper parent territory.") 
        raise Exception

    r = sql("select name from `tabTerritory` where name = '%s' and docstatus = 2"%(self.doc.territory_name))
    if r:
      msgprint("%s record is trashed. To untrash please go to Setup & click on Trash."%(self.doc.territory_name))
      raise Exception

    for d in getlist(self.doclist, 'target_details'):
      if not flt(d.target_qty) and not flt(d.target_amount):
        msgprint("Either target qty or target amount is mandatory.")
        raise Exception


	def on_trash(self):
		cust = sql("select name from `tabCustomer` where ifnull(territory, '') = %s", self.doc.name)
		cust = [d[0] for d in cust]		
		
		if cust:
			msgprint("""Territory: %s can not be trashed/deleted because it is used in customer: %s. 
				To trash/delete this, remove/change territory in customer master""" % (self.doc.name, cust or ''), raise_exception=1)
				
				
		if sql("select name from `tabTerritory` where parent_territory = %s and docstatus != 2", self.doc.name):
			msgprint("Child territory exists for this territory. You can not trash/cancel/delete this territory.", raise_exception=1)

		# rebuild tree
		set(self.doc,'old_parent', '')
		self.update_nsm_model()
