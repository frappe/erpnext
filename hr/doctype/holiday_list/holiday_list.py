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
  def __init__(self,doc,doclist=[]):
    self.doc = doc
    self.doclist = doclist

  # ---------
  # autoname
  # ---------
  def autoname(self):
    self.doc.name = make_autoname(self.doc.fiscal_year +"/"+ self.doc.holiday_list_name+"/.###")


# *************************************************** utilities ***********************************************
  # ----------------
  # validate values
  # ----------------
  def validate_values(self):
    if not self.doc.fiscal_year:
      msgprint("Please select Fiscal Year")
      raise Exception
    if not self.doc.weekly_off:
      msgprint("Please select weekly off day")
      raise Exception


  # ------------------------------------
  # get fiscal year start and end dates
  # ------------------------------------
  def get_fy_start_end_dates(self):
    st_date = sql("select year_start_date from `tabFiscal Year` where name = '%s'" %(self.doc.fiscal_year))
    st_date = st_date and st_date[0][0].strftime('%Y-%m-%d') or ''
    ed_date = add_days(add_years(st_date,1), -1)
    return st_date, ed_date

  # -------------------------
  # get weekly off date list
  # -------------------------
  def get_weekly_off_date_list(self, yr_start_date, yr_end_date):
    days_dict, dt_list, lst_st = {'Monday':0,'Tuesday':1,'Wednesday':2,'Thursday':3,'Friday':4,'Saturday':5,'Sunday':6}, [], ''

    w = cint(days_dict[self.doc.weekly_off])    # Weekly Off Day No.

    st_dt_weekday = getdate(yr_start_date).weekday()    # Year Start Date weekday()

    if w == st_dt_weekday:     # Get Start Date
      lst_st = yr_start_date
      dt_list.append(lst_st)
    elif w > st_dt_weekday:
      lst_st = add_days(yr_start_date,w - st_dt_weekday)
      dt_list.append(lst_st)
    else:
      lst_st = add_days(yr_start_date,6 - st_dt_weekday + 1)
      dt_list.append(lst_st)

    while getdate(lst_st) < getdate(yr_end_date):    # Get list of dates
      lst_st = add_days(lst_st,7)
      if getdate(lst_st) > getdate(yr_end_date):
        break
      dt_list.append(lst_st)

    return dt_list

  # ---------------------
  # get weekly off dates
  # ---------------------
  def get_weekly_off_dates(self):
    self.validate_values()
    yr_start_date, yr_end_date = self.get_fy_start_end_dates()
    date_list = self.get_weekly_off_date_list(yr_start_date, yr_end_date)
    for d in date_list:
      ch = addchild(self.doc, 'holiday_list_details', 'Holiday List Detail', 1, self.doclist)
      ch.description = self.doc.weekly_off
      ch.holiday_date = d

  # ------------
  # clear table
  # ------------
  def clear_table(self):
    self.doc.clear_table(self.doclist,'holiday_list_details')


# ***************************************** validate *************************************************

  # ---------------------------
  # check default holiday list
  # ---------------------------
  def update_default_holiday_list(self):
    sql("update `tabHoliday List` set is_default = 0 where ifnull(is_default, 0) = 1 and fiscal_year = '%s'" % (self.doc.fiscal_year))


  # ---------
  # validate
  # ---------
  def validate(self):
    self.update_default_holiday_list()
