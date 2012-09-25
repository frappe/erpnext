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
  def __init__(self, doc, doclist):
    self.doc = doc
    self.doclist = doclist
    self.account_list = []
    self.ac_details = {} # key: account id, values: debit_or_credit, lft, rgt
    
    self.roles = webnotes.user.get_roles()

    self.period_list = []
    self.period_start_date = {}
    self.period_end_date = {}

    self.fs_list = []
    self.root_bal = []
    self.flag = 0

  # Get defaults on load of MIS, MIS - Comparison Report and Financial statements
  # ----------------------------------------------------
  def get_comp(self):
    ret = {}
    type = []
    comp = []
    # ------ get period -----------
    ret['period'] = ['Annual','Half Yearly','Quarterly','Monthly']
    
    # ---- get companies ---------
    res = sql("select name from `tabCompany`")
    for r in res:
      comp.append(r[0])
    #comp.append(r[0] for r in res)
    ret['company'] = comp

    #--- to get fiscal year and start_date of that fiscal year -----
    res = sql("select name, year_start_date from `tabFiscal Year`")
    ret['fiscal_year'] = [r[0] for r in res]
    ret['start_dates'] = {}
    for r in res:
      ret['start_dates'][r[0]] = str(r[1])
      
    #--- from month and to month (for MIS - Comparison Report) -------
    month_list = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    fiscal_start_month = sql("select MONTH(year_start_date) from `tabFiscal Year` where name = %s",(get_defaults()['fiscal_year']))
    fiscal_start_month = fiscal_start_month and fiscal_start_month[0][0] or 1
    mon = ['']
    for i in range(fiscal_start_month,13): mon.append(month_list[i-1])
    for i in range(0,fiscal_start_month-1): mon.append(month_list[i])
    ret['month'] = mon

    # ------------------------ get MIS Type on basis of roles of session user ------------------------------------------
    if has_common(self.roles, ['Sales Manager']):
      type.append('Sales')
    if has_common(self.roles, ['Purchase Manager']):
      type.append('Purchase')
    ret['type'] = type
    return ret
    
  # Gets Transactions type and Group By options based on module
  #------------------------------------------------------------------
  def get_trans_group(self,module):
    ret = {}
    st,group = [],[]
    if module == 'Sales':
      st = ['Quotation','Sales Order','Delivery Note','Sales Invoice']
      group = ['Item','Item Group','Customer','Customer Group','Cost Center']
    elif module == 'Purchase':
      st = ['Purchase Order','Purchase Receipt','Purchase Invoice']
      group = ['Item','Item Group','Supplier','Supplier Type']
    
    ret['stmt_type'] = st
    ret['group_by'] = group
    
    return ret

  # Get Days based on month (for MIS Comparison Report)
  # --------------------------------------------------------
  def get_days(self,month):
    days = []
    ret = {}
    if month == 'Jan' or month == 'Mar' or month == 'May' or month == 'Jul' or month == 'Aug' or month == 'Oct' or month == 'Dec':
      for i in range(1,32):
        days.append(i)
    elif month == 'Apr' or month == 'Jun' or month == 'Sep' or month == 'Nov':
      for i in range(1,31):
        days.append(i)
    elif month == 'Feb':
      for i in range(1,29):
        days.append(i)
    ret['days'] = days
    return ret
	
  # Get from date and to date based on fiscal year (for in summary - comparison report)
  # -----------------------------------------------------------------------------------------------------
  def dates(self,fiscal_year,from_date,to_date):
    import datetime
    ret = ''
    start_date = cstr(sql("select year_start_date from `tabFiscal Year` where name = %s",fiscal_year)[0][0])
    st_mon = cint(from_date.split('-')[1])
    ed_mon = cint(to_date.split('-')[1])
    st_day = cint(from_date.split('-')[2])
    ed_day = cint(to_date.split('-')[2])
    fiscal_start_month = cint(start_date.split('-')[1])
    next_fiscal_year = cint(start_date.split('-')[0]) + 1
    current_year = ''
    next_year = ''
    
    #CASE - 1 : Jan - Mar (Valid)
    if st_mon < fiscal_start_month and ed_mon < fiscal_start_month:
      current_year = cint(start_date.split('-')[0]) + 1
      next_year  = cint(start_date.split('-')[0]) + 1
    
    # Case - 2 : Apr - Dec (Valid)
    elif st_mon >= fiscal_start_month and ed_mon <= 12 and ed_mon >= fiscal_start_month:
      current_year = cint(start_date.split('-')[0])
      next_year  = cint(start_date.split('-')[0])

    # Case 3 : Jan - May (Invalid)
    elif st_mon < fiscal_start_month and ed_mon >= fiscal_start_month:
      current_year = cint(start_date.split('-')[0]) + 1
      next_year  = cint(start_date.split('-')[0]) + 2
	
    # check whether from date is within fiscal year
    if datetime.date(current_year, st_mon, st_day) >= datetime.date(cint(start_date.split('-')[0]), cint(start_date.split('-')[1]), cint(start_date.split('-')[2])) and datetime.date(cint(current_year), cint(st_mon), cint(st_day)) < datetime.date((cint(start_date.split('-')[0])+1), cint(start_date.split('-')[1]), cint(start_date.split('-')[2])):
      begin_date = cstr(current_year)+"-"+cstr(st_mon)+"-"+cstr(st_day)
    else:
      msgprint("Please enter appropriate from date.")
      raise Exception
    # check whether to date is within fiscal year
    if datetime.date(next_year, ed_mon, ed_day) >= datetime.date(cint(start_date.split('-')[0]), cint(start_date.split('-')[1]), cint(start_date.split('-')[2])) and datetime.date(cint(next_year), cint(ed_mon), cint(ed_day)) < datetime.date(cint(start_date.split('-')[0])+1, cint(start_date.split('-')[1]), cint(start_date.split('-')[2])):
      end_date = cstr(next_year)+"-"+cstr(ed_mon)+"-"+cstr(ed_day)
    else:
      msgprint("Please enter appropriate to date.")
      raise Exception
    ret = begin_date+'~~~'+end_date
    return ret

  # Get MIS Totals
  # ---------------
  def get_totals(self, args):
    args = eval(args)
    #msgprint(args)
    totals = sql("SELECT %s FROM %s WHERE %s %s %s %s" %(cstr(args['query_val']), cstr(args['tables']), cstr(args['company']), cstr(args['cond']), cstr(args['add_cond']), cstr(args['fil_cond'])), as_dict = 1)[0]
    #msgprint(totals)
    tot_keys = totals.keys()
    # return in flt because JSON doesn't accept Decimal
    for d in tot_keys:
      totals[d] = flt(totals[d])
    return totals

  # Get Statement
  # -------------
  
  def get_statement(self, arg): 
    self.return_data = []    

    # define periods
    arg = eval(arg)
    pl = ''
    
    self.define_periods(arg['year'], arg['period'])    # declares 1.period_list i.e. (['Jan','Feb','Mar'...] or ['Q1','Q2'...] or ['FY2009-2010']) based on period
                                                       #          2.period_start_date dict {'Jan':'01-01-2009'...}
                                                       #          3.period_start_date dict {'Jan':'31-01-2009'...}
    self.return_data.append([4,'']+self.period_list)

        
    if arg['statement'] == 'Balance Sheet': pl = 'No'
    if arg['statement'] == 'Profit & Loss': pl = 'Yes'
    
    self.get_children('',0,pl,arg['company'], arg['year'])
        
    #self.balance_pl_statement(acct, arg['statement'])
    #msgprint(self.return_data)
    return self.return_data
    
  # Get Children
  # ------------
  def get_children(self, parent_account, level, pl, company, fy):
    cl = sql("select distinct account_name, name, debit_or_credit, lft, rgt from `tabAccount` where ifnull(parent_account, '') = %s and ifnull(is_pl_account, 'No')=%s and company=%s and docstatus != 2 order by name asc", (parent_account, pl, company))
    level0_diff = [0 for p in self.period_list]
    if pl=='Yes' and level==0: # switch for income & expenses
      cl = [c for c in cl]
      cl.reverse()
    if cl:
      for c in cl:
        self.ac_details[c[1]] = [c[2], c[3], c[4]]
        bal_list = self.get_period_balance(c[1], level, pl, company, fy)
        if level==0: # top level - put balances as totals
          self.return_data.append([level, c[0]] + ['' for b in bal_list])
          totals = bal_list
          for i in range(len(totals)): # make totals
            if c[2]=='Credit':
              level0_diff[i] += flt(totals[i])
            else:
              level0_diff[i] -= flt(totals[i])
        else:
          self.return_data.append([level, c[0]]+bal_list)
          
        if level < 2:
          self.get_children(c[1], level+1, pl, company, fy)
          
        # make totals - for top level
        # ---------------------------
        if level==0:
          # add rows for profit / loss in B/S
          if pl=='No':
            if c[2]=='Credit':
              self.return_data.append([1, 'Total Liabilities'] + totals)
              level0_diff = [-i for i in level0_diff] # convert to debit
              self.return_data.append([5, 'Profit/Loss (Provisional)'] + level0_diff)
              for i in range(len(totals)): # make totals
                level0_diff[i] = flt(totals[i]) + level0_diff[i]
              self.return_data.append([4, 'Total '+c[0]] + level0_diff)
            else:
              self.return_data.append([4, 'Total '+c[0]] + totals)

          # add rows for profit / loss in P/L
          else:
            if c[2]=='Debit':
              self.return_data.append([1, 'Total Expenses (before Profit)'] + totals)
              self.return_data.append([5, 'Profit/Loss (Provisional)'] + level0_diff)
              for i in range(len(totals)): # make totals
                level0_diff[i] = flt(totals[i]) + level0_diff[i]
              self.return_data.append([4, 'Total '+c[0]] + level0_diff)
            else:
              self.return_data.append([4, 'Total '+c[0]] + totals)
  
  # Define Periods
  # --------------
  
  def define_periods(self, year, period):
    
    # get year start date    
    ysd = sql("select year_start_date from `tabFiscal Year` where name=%s", year)
    ysd = ysd and ysd[0][0] or ''

    self.ysd = ysd

    # year
    if period == 'Annual':
      pn = 'FY'+year
      self.period_list.append(pn)
      self.period_start_date[pn] = ysd
      self.period_end_date[pn] = get_last_day(get_first_day(ysd,0,11))

    # quarter
    if period == 'Quarterly':
      for i in range(4):
        pn = 'Q'+str(i+1)
        self.period_list.append(pn)
      
        self.period_start_date[pn] = get_first_day(ysd,0,i*3)
        self.period_end_date[pn] = get_last_day(get_first_day(ysd,0,((i+1)*3)-1))  

    # month
    if period == 'Monthly':
      mlist = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
      for i in range(12):
        fd = get_first_day(ysd,0,i)
        pn = mlist[fd.month-1]
        self.period_list.append(pn)
      
        self.period_start_date[pn] = fd
        self.period_end_date[pn] = get_last_day(fd)
      
  # Get Balance For A Period
  # ------------------------
  
  def get_period_balance(self, acc, level, pl, company, fy):
    debit_or_credit, lft, rgt = self.ac_details[acc]
    ret = []
    for p in self.period_list:
      sd, ed = self.period_start_date[p].strftime('%Y-%m-%d'), self.period_end_date[p].strftime('%Y-%m-%d')
      cond = "and t1.voucher_type != 'Period Closing Voucher'"
      if pl=='No':
        sd = self.ysd.strftime('%Y-%m-%d')
        cond = ""

      bal = sql("select SUM(t1.debit), SUM(t1.credit) from `tabGL Entry` t1, `tabAccount` t2 WHERE t1.posting_date >= '%s' AND t1.posting_date <= '%s' AND t1.company = '%s' AND t1.account = t2.name AND t2.lft >= %s AND t2.rgt <= %s and ifnull(t1.is_opening,'No') = 'No' and ifnull(t1.is_cancelled, 'No') = 'No' %s" % (sd,ed,company,lft,rgt, cond))
      
      
      bal = bal and (flt(bal[0][0]) - flt(bal[0][1])) or 0
      if debit_or_credit == 'Credit' and bal:
        bal = -bal
      if pl=='No':
        op = sql("select opening from `tabAccount Balance` where account=%s and period=%s", (acc, fy))
        op = op and op[0][0] or 0
        bal += flt(op)
      
      ret.append(bal)
    return ret
    
  # Get Dashboard Amounts
  # ---------------------
  
  def get_balance(self, acc, sd, ed, company, fy):
    a = sql("select account_name, name, debit_or_credit, lft, rgt, is_pl_account from `tabAccount` where account_name=%s and company=%s", (acc, company), as_dict=1)
    if a:
      a = a[0]
      bal = sql("select SUM(IFNULL(t1.debit,0)), SUM(IFNULL(t1.credit,0)) from `tabGL Entry` t1, `tabAccount` t2 WHERE t1.posting_date >= %s AND t1.posting_date <= %s AND t1.account = t2.name AND t2.lft >= %s AND t2.rgt <= %s and ifnull(is_opening, 'No') = 'No' and ifnull(t1.is_cancelled, 'No') = 'No'", (sd,ed,a['lft'],a['rgt']))
      if a['debit_or_credit']=='Debit':
        bal = flt(flt(bal[0][0]) - flt(bal[0][1]))
      else:
        bal = flt(flt(bal[0][1]) - flt(bal[0][0]))

      if a['is_pl_account']=='No':
        op = sql("select opening from `tabAccount Balance` where account=%s and period=%s", (acc, fy))
        op = op and op[0][0] or 0
        bal += flt(op)

      return flt(bal)

    else:
      msgprint("Did not find %s for %s" % (acc, company))
      return 0

  def get_cur_balance(self, acc, company):
    bal = sql("select IFNULL(t1.balance,0) from `tabAccount Balance` t1, `tabAccount` t2 where t1.account = %s and t1.period=%s and t1.account = t2.name and t2.company=%s", (acc, self.fiscal_year, company))
    return bal and flt(bal[0][0]) or 0
  
  def get_top_5_cust(self, company):
    rec_grp = sql("select receivables_group from tabCompany where name=%s", company)
    if rec_grp:
      pa_lft_rgt = sql("select lft, rgt from tabAccount where name=%s and company=%s", (rec_grp[0][0], company))[0]
      return sql("select t1.account_name, SUM(t2.debit) from tabAccount t1, `tabGL Entry` t2 where t1.lft > %s and t1.rgt < %s and t2.account = t1.name  and ifnull(t2.is_cancelled, 'No') = 'No' GROUP BY t1.name ORDER BY SUM(t2.debit) desc limit 5", (pa_lft_rgt[0], pa_lft_rgt[1]))
    else:
      return []

  def get_top_5_exp(self, company):
    a = sql("select distinct account_name, name, debit_or_credit, lft, rgt from `tabAccount` where account_name=%s and company=%s", ('Expenses', company), as_dict=1)[0]
    return sql("select t1.account_name, SUM(t2.debit) from tabAccount t1, `tabGL Entry` t2 where t1.lft>%s and t1.rgt<%s and t1.group_or_ledger = 'Ledger' and t2.account = t1.name  and ifnull(t2.is_cancelled, 'No') = 'No' and t2.voucher_type != 'Period Closing Voucher' GROUP BY t1.name ORDER BY SUM(t2.debit) desc limit 5", (a['lft'],a['rgt']))
  
  def bl(self, acc, company):
    dt = getdate(nowdate())

    r = []
    # cur
    r.append(self.get_cur_balance(acc, company))
    # this month
    r.append(self.get_balance(acc, get_first_day(dt), get_last_day(dt), company, self.fiscal_year))
    # last month
    r.append(self.get_balance(acc, get_first_day(dt,0,-1), get_last_day(get_first_day(dt,0,-1)), company, self.fiscal_year))
    return r

  def bl_bs(self, acc, company, sd):
    dt = getdate(nowdate())
    r = []
    # cur
    r.append(self.get_cur_balance(acc, company))
    # last month
    r.append(self.get_balance(acc, sd, get_last_day(get_first_day(dt,0,-1)), company, self.fiscal_year))
    # opening
    r.append(self.get_balance(acc, sd, sd, company, self.fiscal_year))
    return r

  def get_dashboard_values(self, arg=''):
    d = get_defaults()
    self.fiscal_year = d['fiscal_year']
    if arg:
      company = arg
    else:
      company = d['company']

    r = {}
    r['Income'] = self.bl('Income', company)
    r['Expenses'] = self.bl('Expenses', company)

    r['Profit'] = []
    for i in range(3):
      r['Profit'].append(r['Income'][i] - r['Expenses'][i])
    
    r['Current Assets'] = self.bl_bs('Current Assets', company, getdate(d['year_start_date']))
    r['Current Liabilities'] = self.bl_bs('Current Liabilities', company, getdate(d['year_start_date']))
    
    r['Working Capital'] = []
    for i in range(3):
      r['Working Capital'].append(r['Current Assets'][i] - r['Current Liabilities'][i])

    r['Bank Accounts'] = self.bl_bs('Bank Accounts', company, getdate(d['year_start_date']))
    
    r['Top Customers'] = convert_to_lists(self.get_top_5_cust(company))
    r['Top Expenses'] = convert_to_lists(self.get_top_5_exp(company))
    
    return r
