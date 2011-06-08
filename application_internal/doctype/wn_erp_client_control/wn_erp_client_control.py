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
  def __init__(self, doc, doclist):
    self.doc, self.doclist = doc, doclist


  # Check End of Trial Period
  # -------------------------
  def trial_payment_reminders(self):
    if cint(self.doc.is_trial_account)==1:
      # Trial Period Expiry
      trial_end_date = add_days(self.doc.account_start_date, 30)
      days = date_diff(trial_end_date, nowdate())
      # check if trial period has expired
      if days < 10 and days >= 0 and has_common(['System Manager'],webnotes.user.get_roles()):
        return "Your Trial Period expires on '%s'. Please buy credits online using Manage Account." % (formatdate(trial_end_date))
      
      # trial period has already expired
      elif days < 0 and days >= -6:
        extended_days = 7 + days
        return "Your Trial Period has expired on %s. However, your account will be live for %s days. Please contact your System Manager to buy credits." % (formatdate(trial_end_date),cstr(extended_days))
      elif not has_common(['Administrator'],webnotes.user.get_roles()) and days < -6:
        return "Stopped"
    
    # Account is not a trial account
    else:
      return self.account_expiry_reminder()
      

  # Account Expiry Reminder  
  # -----------------------
  def account_expiry_reminder(self):
    import webnotes.utils
    from datetime import datetime
    # Payment Reminder in case of not enough balance
    cr_reqd = cint(self.doc.total_users)
    days_left = cint(self.calc_days())
    # check if account balance is sufficient
    if cint(self.doc.credit_balance)<(cr_reqd):
      
      # Difference between last payment date and current date
      if self.doc.last_deduction_date: last_payment = date_diff(nowdate(),self.doc.last_deduction_date)
      else: last_payment = -1

      # 7 days extension
      remaining_days = days_left - 24
      if last_payment > 30 or last_payment == -1:
        if remaining_days < 8 and remaining_days >= 1:
          return "Your account will be de-activated in " + cstr(remaining_days) + " days. Please contact your System Manager to buy credits."
        elif remaining_days==0:
          return "Your account will be disabled from tomorrow. Please contact your System Manager to buy credits."
        elif not has_common(['Administrator'],webnotes.user.get_roles()):
          return "Stopped"

      # check if user account is extended for seven days
      if cint(self.doc.is_trial_account)==0:
        if days_left < 10 and days_left >= 0:
          return "You have only %s Credits in your account. Buy credits before %s." % (cint(self.doc.credit_balance),formatdate(self.next_bill_sdate))



  # Calculate days between current date and billing cycle end date
  # --------------------------------------------------------------
  def calc_days(self):
    if self.doc.billing_cycle_date:
      next_bill_month = cint(nowdate().split('-')[1])
      if cint(nowdate().split('-')[2]) > cint(self.doc.billing_cycle_date.split('-')[2]):
        next_bill_month = cint(nowdate().split('-')[1]) + 1
      next_bill_year = nowdate().split('-')[0]
      if next_bill_month > 12:
        next_bill_month = next_bill_month % 12
        next_bill_year += 1
      self.next_bill_sdate = cstr(next_bill_year)+'-'+cstr(next_bill_month)+'-'+(self.calc_next_day(next_bill_year,next_bill_month))
      #msgprint("next_bill_month :::" + self.next_bill_sdate)
      return date_diff(self.next_bill_sdate, nowdate())


  # Calculate next billing date day
  # --------------------------------
  def calc_next_day(self, next_year, next_month):
    bill_cycle_day = cstr(self.doc.billing_cycle_date).split('-')[2]
    if cint(next_month) == 2 and next_year%4==0 and (next_year%100!=0 or next_year%400==0) and cint(bill_cycle_day) > 28:
      bill_cycle_day = '28'
    elif cint(bill_cycle_day) == 31 and cint(next_month) in (4,6,9,11):
      bill_cycle_day = '30'
    return bill_cycle_day


  # Update acc credits and balance (making payment from gateway)
  # -------------------------------------------------------------
  def update_acc_bal(self,args):
    args = eval(args)
    self.doc.credit_balance = cint(self.doc.credit_balance) + cint(args.get('net_cr'))
    self.doc.total_users = cint(self.doc.total_users) + cint(args.get('total_users'))
    if cint(self.doc.is_trial_account) == 1:
      if not self.doc.account_start_date:
        self.doc.account_start_date = nowdate()
      self.doc.is_trial_account = 0
      self.doc.billing_cycle_date = nowdate()
      self.doc.last_deduction_date = nowdate()
    self.doc.save()


  # Check Credit Balance
  # ---------------------
  def check_credit_balance(self):
    if cint(self.doc.is_trial_account) == 0:
      if cint(self.doc.credit_balance) < 1:
        msgprint("You do not have enough credits to add new user. Please buy credits.")
        raise Exception
      else:
        self.doc.credit_balance = cint(self.doc.credit_balance) - 1
        msgprint("Your one credit is consumed. Balance Credits : %s" % (self.doc.credit_balance))
    self.doc.total_users = cint(self.doc.total_users) + 1
    self.doc.save()


  # Monthly Deduction
  # ------------------
  def monthly_deduction(self, cr_ded):
    self.doc.credit_balance = cint(self.doc.credit_balance) - cint(cr_ded)
    self.doc.last_deduction_date = nowdate()
    self.doc.save()