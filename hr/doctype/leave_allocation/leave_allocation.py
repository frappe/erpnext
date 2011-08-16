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
import datetime
	
# -----------------------------------------------------------------------------------------
class DocType:
  def __init__(self, doc, doclist):
    self.doc = doc
    self.doclist = doclist


# ************************************************ utilities *************************************************
  # --------------
  # get leave bal
  # --------------
  def get_leave_bal(self, prev_fyear):
    # leaves allocates
    tot_leaves_all = sql("select SUM(total_leaves_allocated) from `tabLeave Allocation` where employee = '%s' and leave_type = '%s' and fiscal_year = '%s' and docstatus = 1 and name != '%s'" % (self.doc.employee, self.doc.leave_type, prev_fyear, self.doc.name))
    tot_leaves_all = tot_leaves_all and flt(tot_leaves_all[0][0]) or 0

    # leaves applied
    tot_leaves_app = sql("select SUM(total_leave_days) from `tabLeave Application` where employee = '%s' and leave_type = '%s' and fiscal_year = '%s' and docstatus = 1" % (self.doc.employee, self.doc.leave_type, prev_fyear))
    tot_leaves_app = tot_leaves_app and flt(tot_leaves_app[0][0]) or 0

    return tot_leaves_all - tot_leaves_app

 
# ******************************************** client triggers ***********************************************

  # ------------------------------------------------------------------
  # check whether carry forward is allowed or not for this leave type
  # ------------------------------------------------------------------
  def allow_carry_forward(self):
    cf = sql("select is_carry_forward from `tabLeave Type` where name = %s" , self.doc.leave_type)
    cf = cf and cint(cf[0][0]) or 0
    if not cf:
      set(self.doc,'carry_forward',0)
      msgprint("Sorry ! You cannot carry forward %s" % (self.doc.leave_type))
      raise Exception

  # ---------------------------
  # get carry forwarded leaves
  # ---------------------------
  def get_carry_forwarded_leaves(self):
    if self.doc.carry_forward: self.allow_carry_forward()
    prev_fiscal_year = sql("select name from `tabFiscal Year` where name < '%s' order by name desc limit 1" % (self.doc.fiscal_year))
    prev_fiscal_year = prev_fiscal_year and prev_fiscal_year[0][0] or ''
    ret = {}
    prev_bal = 0
    if prev_fiscal_year and cint(self.doc.carry_forward) == 1:
      prev_bal = self.get_leave_bal(prev_fiscal_year)
    ret = {
      'carry_forwarded_leaves'  :  prev_bal,
      'total_leaves_allocated'   :  flt(prev_bal) + flt(self.doc.new_leaves_allocated)
    }
    return ret


# ********************************************** validate *****************************************************

  # ---------------------------
  # get total allocated leaves
  # ---------------------------
  def get_total_allocated_leaves(self):
    leave_det = eval(self.get_carry_forwarded_leaves())
    set(self.doc,'carry_forwarded_leaves',flt(leave_det['carry_forwarded_leaves']))
    set(self.doc,'total_leaves_allocated',flt(leave_det['total_leaves_allocated']))

  # ------------------------------------------------------------------------------------
  # validate leave (i.e. check whether leave for same type is already allocated or not)
  # ------------------------------------------------------------------------------------
  def validate_allocated_leave(self):
    l = sql("select name from `tabLeave Allocation` where employee = '%s' and leave_type = '%s' and fiscal_year = '%s' and docstatus = 1" % (self.doc.employee, self.doc.leave_type, self.doc.fiscal_year)) 
    l = l and l[0][0] or ''
    if l:
      msgprint("%s is allocated to Employee: %s for Fiscal Year : %s. Please refer Leave Allocation : %s" % (self.doc.leave_type, self.doc.employee, self.doc.fiscal_year, l))
      raise Exception

  # ---------
  # validate
  # ---------
  def validate(self):
    self.validate_allocated_leave()

  # ----------
  # on update
  # ----------
  def on_update(self):
    self.get_total_allocated_leaves()


# ********************************************** cancel ********************************************************

  # -------------------------
  # check for applied leaves
  # -------------------------
  def check_for_leave_application(self):
    chk = sql("select name from `tabLeave Application` where employee = '%s' and leave_type = '%s' and fiscal_year = '%s' and docstatus = 1" % (self.doc.employee, self.doc.leave_type, self.doc.fiscal_year))
    chk = chk and chk[0][0] or ''
    if chk:
      msgprint("Cannot cancel this Leave Allocation as Employee : %s has already applied for %s. Please check Leave Application : %s" % (self.doc.employee, self.doc.leave_type, chk))
      raise Exception

  # -------
  # cancel
  # -------
  def on_cancel(self):
    self.check_for_leave_application()
