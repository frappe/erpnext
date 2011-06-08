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

  def get_bal(self,arg):
    bal = sql("select `tabAccount Balance`.balance,`tabAccount`.debit_or_credit from `tabAccount`,`tabAccount Balance` where `tabAccount Balance`.account=%s and `tabAccount Balance`.period=%s and `tabAccount Balance`.account=`tabAccount`.name ",(arg,self.doc.current_fiscal_year))
    if bal:
      return fmt_money(flt(bal[0][0])) + ' ' + bal[0][1]
    else:
      return ''
  
  def get_series(self):
    self.doc.clear_table(self.doclist, 'series_details')
    
    if self.doc.select_doctype:
      sr= sql("Select options from `tabDocField` where fieldname='voucher_series' and parent='%s'"%(self.doc.select_doctype))
      if sr:
        sr_list=sr[0][0].split("\n")
        
        for x in sr_list:
          if cstr(x)!='':
            c = addchild(self.doc, 'series_details', 'Series Detail', 1, self.doclist)
            c.series=cstr(x)
      
      else:
        msgprint("No series is mentioned")
    else :
      msgprint("Please select Doctype")
  
  def remove_series(self):
    if not getlist(self.doclist, 'series_details'):
      msgprint("Please pull already existed series for the selected doctype and check the series that you want to remove")
    else:
      sr= sql("Select options from `tabDocField` where fieldname='voucher_series' and parent='%s'"%(self.doc.select_doctype))
      if sr:
        sr_list=sr[0][0].split("\n")
      
      for d in getlist(self.doclist, 'series_details'):
        if d.remove == 1:
          sr_list.remove(d.series)
      sql("update `tabDocField` set options='%s' where fieldname='voucher_series' and parent='%s'"%("\n".join(sr_list),self.doc.select_doctype))
      self.get_series()

  def add_series(self):
    if not self.doc.select_doctype or not self.doc.new_series:
      msgprint("Please select Doctype and series name for which series will be added")
      raise Exception
    else:
      sr_list = []
      sr= sql("select options from `tabDocField` where fieldname='voucher_series' and parent='%s'"% (self.doc.select_doctype))
      if sr[0][0]:
        sr_list=sr[0][0].split("\n")
      self.check_duplicate()
      if not sr_list:
        sr_list.append('')
        sr_list.append(self.get_new_series())
      else:
        sr_list.append(self.get_new_series())
      sql("update `tabDocField` set options='%s' where fieldname='voucher_series' and parent='%s'"%("\n".join(sr_list),self.doc.select_doctype))
      self.get_series()
      
  def check_duplicate(self):
    sr_list = sql("Select options from `tabDocField` where fieldname='voucher_series' group by parent")
    nw_sr = self.get_new_series()
    #msgprint(sr_list)
    for sr in sr_list:
      if nw_sr in sr[0]:
        idx=sql("Select current from `tabSeries` where name='%s'"% (nw_sr + '/'))
        msgprint("Series name already exist with index '%s'" %(idx[0][0]))
        raise Exception  
        
  def get_new_series(self):
    if 'FY' in cstr((self.doc.new_series).upper()):
      abb=sql("select abbreviation from `tabFiscal Year` where name='%s'"%(self.doc.current_fiscal_year))
      if not abb:
        msgprint("Abbreviation is not mentioned in Fiscal Year")
        raise Exception
      else:
        return cstr((self.doc.new_series).upper()).strip().replace('FY',abb[0][0])
    else:
      return cstr((self.doc.new_series).upper()).strip()

  def on_update(self):

    # fiscal year
    set_default('fiscal_year', self.doc.current_fiscal_year)
    ysd = sql("select year_start_date from `tabFiscal Year` where name=%s", self.doc.current_fiscal_year, as_dict = 1)
    set_default('year_start_date', ysd[0]['year_start_date'].strftime('%Y-%m-%d'))
    set_default('year_end_date', get_last_day(get_first_day(ysd[0]['year_start_date'],0,11)).strftime('%Y-%m-%d'))

    # company
    set_default('company', self.doc.default_company)

    set_default('stock_valuation', self.doc.stock_valuation or 'Moving Average')
    set_default('default_currency', self.doc.default_currency or 'INR')

    # Purchase in transit
    if self.doc.purchase_in_transit_account:
      set_default('purchase_in_transit_account', self.doc.purchase_in_transit_account)
  
  def get_default_bank_account(self, company):
    return sql("select default_bank_account from tabCompany where name = '%s'" % company)[0][0]

  def get_bank_defaults(self, arg):
    arg = eval(arg)
    return {
      'def_bv_type': self.doc.default_bank_voucher_type or '',
      'def_bv_series': self.doc.default_bank_voucher_series or '',
      'def_bank_account': self.get_default_bank_account(arg['company']) or '',
      'bank_balance': self.get_bal(self.get_default_bank_account(arg['company'])) or 0.0,
      'acc_balance': self.get_bal(arg['credit_to']) or 0.0
    }
