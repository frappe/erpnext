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
  def __init__(self,d,dl):
    self.doc, self.doclist = d, dl
    self.td, self.tc = 0, 0
    self.year_start_date = ''
    self.year_end_date = ''


  # Validate Account Head
  #============================================================
  def validate_account_head(self):
    acc_det = sql("select debit_or_credit, is_pl_account, group_or_ledger, company from `tabAccount` where name = '%s'" % (self.doc.closing_account_head))

    # Account should be under liability 
    if cstr(acc_det[0][0]) != 'Credit' or cstr(acc_det[0][1]) != 'No':
      msgprint("Account: %s must be created under 'Source of Funds'" % self.doc.closing_account_head)
      raise Exception
   
    # Account must be a ledger
    if cstr(acc_det[0][2]) != 'Ledger':
      msgprint("Account %s must be a ledger" % self.doc.closing_account_head)
      raise Exception 
    
    # Account should belong to company selected 
    if cstr(acc_det[0][3]) != self.doc.company:
      msgprint("Account %s does not belong to Company %s ." % (self.doc.closing_account_head, self.doc.company))
      raise Exception 

  # validate posting date
  #=============================================================
  def validate_posting_date(self):
    yr = sql("select start_date, end_date from `tabPeriod` where period_name = '%s'" % (self.doc.fiscal_year))
    self.year_start_date = yr and yr[0][0] or ''
    self.year_end_date = yr and yr[0][1] or ''
    
    # Posting Date should be within closing year
    if getdate(self.doc.posting_date) < self.year_start_date or getdate(self.doc.posting_date) > self.year_end_date:
      msgprint("Posting Date should be within Closing Fiscal Year")
      raise Exception

    # Period Closing Entry
    pce = sql("select name from `tabPeriod Closing Voucher` where posting_date > '%s' and fiscal_year = '%s' and docstatus = 1" % (self.doc.posting_date, self.doc.fiscal_year))
    if pce and pce[0][0]:
      msgprint("Another Period Closing Entry: %s has been made after posting date: %s" % (cstr(pce[0][0]), self.doc.posting_date))
      raise Exception
     
  # Validate closing entry requirement
  #==========================================================
  def validate_pl_balances(self):
    income_bal = sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) from `tabGL Entry` t1, tabAccount t2 where t1.account = t2.name and t1.posting_date between '%s' and '%s' and t2.debit_or_credit = 'Credit' and t2.group_or_ledger = 'Ledger' and ifnull(t2.freeze_account, 'No') = 'No' and t2.is_pl_account = 'Yes' and t2.docstatus < 2 and t2.company = '%s'" % (self.year_start_date, self.doc.posting_date, self.doc.company))
    expense_bal = sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) from `tabGL Entry` t1, tabAccount t2 where t1.account = t2.name and t1.posting_date between '%s' and '%s' and t2.debit_or_credit = 'Debit' and t2.group_or_ledger = 'Ledger' and ifnull(t2.freeze_account, 'No') = 'No' and t2.is_pl_account = 'Yes' and t2.docstatus < 2 and t2.company = '%s'" % (self.year_start_date, self.doc.posting_date, self.doc.company))
    
    income_bal = income_bal and income_bal[0][0] or 0
    expense_bal = expense_bal and expense_bal[0][0] or 0
    
    if not income_bal and not expense_bal:
      msgprint("Both Income and Expense balances are zero. No Need to make Period Closing Entry.")
      raise Exception
    
  # Get account (pl) specific balance
  #===========================================================
  def get_pl_balances(self, d_or_c):
    acc_bal = sql("select  t1.account, sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) from `tabGL Entry` t1, `tabAccount` t2 where t1.account = t2.name and t2.group_or_ledger = 'Ledger' and ifnull(t2.freeze_account, 'No') = 'No' and t2.is_pl_account = 'Yes' and t2.debit_or_credit = '%s' and t2.docstatus < 2 and t2.company = '%s' and t1.posting_date between '%s' and '%s' group by t1.account " % (d_or_c, self.doc.company, self.year_start_date, self.doc.posting_date))
    return acc_bal

   
  # Makes GL Entries
  # ==========================================================
  def make_gl_entries(self, acc_det):
    for a in acc_det:
      if flt(a[1]):
        fdict = {
	        'account': a[0], 
	        'cost_center': '', 
	        'against': '', 
	        'debit': flt(a[1]) < 0 and -1*flt(a[1]) or 0,
	        'credit': flt(a[1]) > 0 and flt(a[1]) or 0,
	        'remarks': self.doc.remarks, 
	        'voucher_type': self.doc.doctype, 
	        'voucher_no': self.doc.name, 
	        'transaction_date': self.doc.transaction_date, 
	        'posting_date': self.doc.posting_date, 
	        'fiscal_year': self.doc.fiscal_year, 
	        'against_voucher': '', 
	        'against_voucher_type': '', 
	        'company': self.doc.company, 
	        'is_opening': 'No', 
	        'aging_date': self.doc.posting_date
        }
      
        self.save_entry(fdict)
   
 
  # Save GL Entry
  # ==========================================================
  def save_entry(self, fdict, is_cancel = 'No'):
    # Create new GL entry object and map values
    le = Document('GL Entry')
    for k in fdict:
      le.fields[k] = fdict[k]
    
    le_obj = get_obj(doc=le)
    # validate except on_cancel
    if is_cancel == 'No':
      le_obj.validate()
      
      # update total debit / credit except on_cancel
      self.td += flt(le.credit)
      self.tc += flt(le.debit)

    # save
    le.save(1)
    le_obj.on_update(adv_adj = '', cancel = '')
    

  # Reposting Balances
  # ==========================================================
  def repost_account_balances(self):
    # Get Next Fiscal Year
    fy = sql("select name, is_fiscal_year_closed from `tabFiscal Year` where name = '%s' and past_year = '%s'" % (self.doc.next_fiscal_year, self.doc.fiscal_year))
    if not fy:
      msgprint("There is no Fiscal Year with Name " + cstr(self.doc.next_fiscal_year) + " and Past Year " + cstr(self.doc.fiscal_year))
      raise Exception
   
    if fy and fy[0][1] == 'Yes':
      msgprint("Fiscal Year %s has been closed." % cstr(fy[1]))
      raise Exception
    
    # Repost Balances
    get_obj('Fiscal Year', fy[0][0]).repost()
 
     
  # Validation
  # ===========================================================
  def validate(self):
  
    # validate account head
    self.validate_account_head()

    # validate posting date
    self.validate_posting_date()

    # check if pl balance:
    self.validate_pl_balances()


  # On Submit
  # ===========================================================
  def on_submit(self):
    
    # Makes closing entries for Expense Account
    in_acc_det = self.get_pl_balances('Credit')
    self.make_gl_entries(in_acc_det)

    # Makes closing entries for Expense Account
    ex_acc_det = self.get_pl_balances('Debit')
    self.make_gl_entries(ex_acc_det)


    # Makes Closing entry for Closing Account Head
    bal = self.tc - self.td
    self.make_gl_entries([[self.doc.closing_account_head, flt(bal)]])


  # On Cancel
  # =============================================================
  def on_cancel(self):
    # get all submit entries of current closing entry voucher
    gl_entries = sql("select account, debit, credit from `tabGL Entry` where voucher_type = 'Period Closing Voucher' and voucher_no = '%s'" % (self.doc.name))

    # Swap Debit & Credit Column and make gl entry
    for gl in gl_entries:
      fdict = {'account': gl[0], 'cost_center': '', 'against': '', 'debit': flt(gl[2]), 'credit' : flt(gl[1]), 'remarks': self.doc.cancel_reason, 'voucher_type': self.doc.doctype, 'voucher_no': self.doc.name, 'transaction_date': self.doc.transaction_date, 'posting_date': self.doc.posting_date, 'fiscal_year': self.doc.fiscal_year, 'against_voucher': '', 'against_voucher_type': '', 'company': self.doc.company, 'is_opening': 'No', 'aging_date': 'self.doc.posting_date'}
      self.save_entry(fdict, is_cancel = 'Yes')

    # Update is_cancelled = 'Yes' to all gl entries for current voucher
    sql("update `tabGL Entry` set is_cancelled = 'Yes' where voucher_type = '%s' and voucher_no = '%s'" % (self.doc.doctype, self.doc.name))
