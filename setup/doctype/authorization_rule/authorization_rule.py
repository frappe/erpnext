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

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.wrapper import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self, d, dl):
    self.doc, self.doclist = d, dl


  # Duplicate Entry
  # ----------------
  def check_duplicate_entry(self):
    exists = sql("select name, docstatus from `tabAuthorization Rule` where transaction = %s and based_on = %s and system_user = %s and system_role = %s and approving_user = %s and approving_role = %s and to_emp =%s and to_designation=%s and name != %s", (self.doc.transaction, self.doc.based_on, cstr(self.doc.system_user), cstr(self.doc.system_role), cstr(self.doc.approving_user), cstr(self.doc.approving_role), cstr(self.doc.to_emp), cstr(self.doc.to_designation), self.doc.name))
    auth_exists = exists and exists[0][0] or ''
    if auth_exists:
      if cint(exists[0][1]) == 2:
        msgprint("Duplicate Entry. Please remove from trash Authorization Rule : %s." %(auth_exists))
        raise Exception
      else:
        msgprint("Duplicate Entry. Please check Authorization Rule : %s." % (auth_exists))
        raise Exception


  # Validate Master Name
  # ---------------------
  def validate_master_name(self):
    if self.doc.based_on == 'Customerwise Discount' and not sql("select name from tabCustomer where name = '%s' and docstatus != 2" % (self.doc.master_name)):
      msgprint("Please select valid Customer Name for Customerwise Discount.")
      raise Exception
    elif self.doc.based_on == 'Itemwise Discount' and not sql("select name from tabItem where name = '%s' and docstatus != 2" % (self.doc.master_name)):
      msgprint("Please select valid Item Name for Itemwise Discount.")
      raise Exception
    elif (self.doc.based_on == 'Grand Total' or self.doc.based_on == 'Average Discount') and self.doc.master_name:
      msgprint("Please remove Customer / Item Name for %s." % (self.doc.based_on))
      raise Exception


  # Validate Rule
  # --------------
  def validate_rule(self):
    if not self.doc.transaction == 'Expense Claim' and not self.doc.transaction == 'Appraisal':
      if not self.doc.approving_role and not self.doc.approving_user:
        msgprint("Please enter Approving Role or Approving User")
        raise Exception
      elif self.doc.system_user and self.doc.system_user == self.doc.approving_user:
        msgprint("Approving User cannot be same as user the rule is Applicable To (User).")
        raise Exception
      elif self.doc.system_role and self.doc.system_role == self.doc.approving_role:
        msgprint("Approving Role cannot be same as user the rule is Applicable To (Role).")
        raise Exception
      elif self.doc.system_user and self.doc.approving_role and has_common([self.doc.approving_role],[x[0] for x in sql("select role from `tabUserRole` where parent = '%s'" % (self.doc.system_user))]):
        msgprint("System User : %s is assigned role : %s. So rule does not make sense." % (self.doc.system_user,self.doc.approving_role))
        raise Exception
      elif (self.doc.transaction == 'Purchase Order' or self.doc.transaction == 'Purchase Receipt' or self.doc.transaction == 'Purchase Invoice' or self.doc.transaction == 'Stock Entry') and (self.doc.based_on == 'Average Discount' or self.doc.based_on == 'Customerwise Discount' or self.doc.based_on == 'Itemwise Discount'):
        msgprint("You cannot set authorization on basis of Discount for %s." % (self.doc.transaction))
        raise Exception
      elif self.doc.based_on == 'Average Discount' and flt(self.doc.value) > 100.00:
        msgprint("Discount cannot given for more than 100 %s." % ('%'))
        raise Exception
      elif self.doc.based_on == 'Customerwise Discount' and not self.doc.master_name:
        msgprint("Please enter Customer Name for 'Customerwise Discount'")
        raise Exception
    else:
      if self.doc.transaction == 'Appraisal' and self.doc.based_on != 'Not Applicable':
        msgprint("Based on is 'Not Applicable' while setting authorization rule for 'Appraisal'")
        raise Exception
      if self.doc.transaction == 'Expense Claim' and self.doc.based_on != 'Total Claimed Amount':
        msgprint("Authorization rule should be based on 'Total Calimed Amount' while setting authorization rule for 'Expense Claim'")
        raise Exception


  def validate(self):
    self.check_duplicate_entry()
    self.validate_rule()
    self.validate_master_name()
    if not self.doc.value: self.doc.value = flt(0)