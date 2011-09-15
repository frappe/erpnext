# Please edit this list and import only required elements
import webnotes

from webnotes.utils import cint, cstr, flt, fmt_money, formatdate, getTraceback, get_defaults, getdate, has_common, month_name, now, nowdate, sendmail, set_default, str_esc_quote, user_format, validate_email_add
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
from utilities.transaction_base import TransactionBase

class DocType:
  def __init__(self,d,dl):
    self.doc, self.doclist = d,dl
    self.master_type = {}
    self.credit_days_for = {}
    self.credit_days_global = -1
    self.is_approving_authority = -1

  #--------------------------------------------------------------------------------------------------------
  # Autoname
  #--------------------------------------------------------------------------------------------------------
  def autoname(self):
    self.doc.name = make_autoname(self.doc.naming_series+'.#####')

  #--------------------------------------------------------------------------------------------------------
  # Fetch outstanding amount from RV/PV
  #--------------------------------------------------------------------------------------------------------
  def get_outstanding(self, args):
    args = eval(args)
    o_s = sql("select outstanding_amount from `tab%s` where name = '%s'" % (args['doctype'],args['docname']))
    if args['doctype'] == 'Payable Voucher':
      return {'debit': o_s and flt(o_s[0][0]) or 0}
    if args['doctype'] == 'Receivable Voucher':
      return {'credit': o_s and flt(o_s[0][0]) or 0}

  #--------------------------------------------------------------------------------------------------------
  # Create remarks
  #--------------------------------------------------------------------------------------------------------
  def create_remarks(self):
    r = []
    if self.doc.cheque_no :
      if self.doc.cheque_date:
        r.append('Via cheque #%s dated %s' % (self.doc.cheque_no, formatdate(self.doc.cheque_date)))
      else :
        msgprint("Please enter cheque date")
        raise Exception
    
    for d in getlist(self.doclist, 'entries'):
      if d.against_invoice and d.credit:
        currency = sql("select currency from `tabReceivable Voucher` where name = '%s'" % d.against_invoice)
        currency = currency and currency[0][0] or ''
        r.append('%s %s against Invoice: %s' % (cstr(currency), fmt_money(flt(d.credit)), d.against_invoice))
      if d.against_voucher and d.debit:
        bill_no = sql("select bill_no, bill_date, currency from `tabPayable Voucher` where name=%s", d.against_voucher)
        if bill_no and bill_no[0][0] and bill_no[0][0].lower().strip() not in ['na', 'not applicable', 'none']:
          bill_no = bill_no and bill_no[0]
          r.append('%s %s against Bill %s dated %s' % (bill_no[2] and cstr(bill_no[2]) or '', fmt_money(flt(d.debit)), bill_no[0], bill_no[1] and formatdate(bill_no[1].strftime('%Y-%m-%d')) or ''))
    if self.doc.ded_amount:
      r.append("TDS Amount: %s" % self.doc.ded_amount)
  
    if self.doc.user_remark:
      r.append("User Remark : %s"%self.doc.user_remark)

    if r:
      self.doc.remark = ("\n").join(r)
  
  # --------------------------------------------------------------------------------------------------------
  # Check user role for approval process
  # --------------------------------------------------------------------------------------------------------
  def get_authorized_user(self):
    if self.is_approving_authority==-1:
      self.is_approving_authority = 0

      # Fetch credit controller role
      approving_authority = sql("select value from `tabSingles` where field='credit_controller' and doctype='Manage Account'")
      approving_authority = approving_authority and approving_authority[0][0] or ''
	    
      # Check logged-in user is authorized
      if approving_authority in webnotes.user.get_roles():
        self.is_approving_authority = 1
	      
	return self.is_approving_authority
      
  # get master type
  # ---------------
  def get_master_type(self, ac):
    if not self.master_type.get(ac):
      self.master_type[ac] = sql("select master_type from `tabAccount` where name=%s", ac)[0][0] or 'None'
    return self.master_type[ac]
  
  # get credit days for
  # -------------------
  def get_credit_days_for(self, ac):

    if not self.credit_days_for.has_key(ac):
      self.credit_days_for[ac] = sql("select credit_days from `tabAccount` where name='%s'" % ac)[0][0] or 0

    if not self.credit_days_for[ac]:
      if self.credit_days_global==-1:
        self.credit_days_global = sql("select credit_days from `tabCompany` where name='%s'" % self.doc.company)[0][0] or 0
      return self.credit_days_global
    else:
      return self.credit_days_for[ac]
  
  
  # --------------------------------------------------------------------------------------------------------
  # Check Credit Days - Cheque Date can not after (Posting date + Credit Days)
  # --------------------------------------------------------------------------------------------------------
  def check_credit_days(self):
    date_diff = 0
    if self.doc.cheque_date:
      date_diff = (getdate(self.doc.cheque_date)-getdate(self.doc.posting_date)).days
    
    if date_diff <= 0: return
    
    # Get List of Customer Account
    acc_list = filter(lambda d: self.get_master_type(d.account)=='Customer', getlist(self.doclist,'entries'))
    
    for d in acc_list:
      credit_days = self.get_credit_days_for(d.account)
      
      # Check credit days
      if credit_days > 0 and not self.get_authorized_user() and cint(date_diff) > credit_days:
        msgprint("Credit Not Allowed: Cannot allow a check that is dated more than %s days after the posting date" % credit_days)
        raise Exception
          
  #--------------------------------------------------------------------------------------------------------
  # validation of debit/credit account with Debit To Account(RV) or Credit To Account (PV)
  #--------------------------------------------------------------------------------------------------------
  def check_account_against_entries(self):
    for d in getlist(self.doclist,'entries'):
      if d.against_invoice:
        acc=sql("select debit_to from `tabReceivable Voucher` where name='%s'"%d.against_invoice)
        if acc and acc[0][0] != d.account:
          msgprint("Debit account is not matching with receivable voucher")
          raise Exception
      
      if d.against_voucher:
        acc=sql("select credit_to from `tabPayable Voucher` where name='%s'"%d.against_voucher)
        if acc and acc[0][0] != d.account:
          msgprint("Credit account is not matching with payable voucher")
          raise Exception
          
  #--------------------------------------------------------------------------------------------------------
  # Validate Cheque Info: Mandatory for Bank/Contra voucher
  #--------------------------------------------------------------------------------------------------------  
  def validate_cheque_info(self):
    if self.doc.voucher_type in ['Bank Voucher']:
      if not self.doc.cheque_no or not self.doc.cheque_date:
        msgprint("Cheque No & Cheque Date is required for " + cstr(self.doc.voucher_type))
        raise Exception
        
    if self.doc.cheque_date and not self.doc.cheque_no:
      msgprint("Cheque No is mandatory if you entered Cheque Date")
      raise Exception
      
  #--------------------------------------------------------------------------------------------------------
  # Gives reminder for making is_advance = 'Yes' in Advance Entry
  #--------------------------------------------------------------------------------------------------------
  def validate_entries_for_advance(self):
    for d in getlist(self.doclist,'entries'):
      if not d.is_advance and not d.against_voucher and not d.against_invoice and d.against_jv:
        master_type = self.get_master_type(d.account)
        if (master_type == 'Customer' and flt(d.credit) > 0) or (master_type == 'Supplier' and flt(d.debit) > 0):
          msgprint("Message: Please check Is Advance as 'Yes' against Account %s if this is an advance entry." % d.account)
      
  #--------------------------------------------------------------------------------------------------------
  # TDS: Validate tds related fields
  #--------------------------------------------------------------------------------------------------------
  def get_tds_category_account(self):
    for d in getlist(self.doclist,'entries'):
      if flt(d.debit) > 0 and not d.against_voucher and d.is_advance == 'Yes':
        acc = sql("select tds_applicable from `tabAccount` where name = '%s'" % d.account)
        acc_tds_applicable = acc and acc[0][0] or 'No'
        if acc_tds_applicable == 'Yes':
          # TDS applicable field become mandatory for advance payment towards supplier or related party
          if not self.doc.tds_applicable:
            msgprint("Please select TDS Applicable or Not")
            raise Exception
            
          # If TDS applicable, category and supplier account bocome mandatory
          elif self.doc.tds_applicable == 'Yes':
            self.validate_category_account(d.account)
            if self.doc.ded_amount and not self.doc.tax_code:
              msgprint("Please enter Tax Code in TDS section")
              raise Exception

          #If TDS not applicable, all related fields should blank
          else:
            self.set_fields_null()
            
        # If tds amount but tds applicability not mentioned in account master
        elif self.doc.ded_amount:
          msgprint("Please select TDS Applicable = 'Yes' in account head: '%s' if you want to deduct TDS." % self.doc.supplier_account)
          raise Exception
    
    

  #--------------------------------------------------------------------------------------------------------
  # If TDS applicable , TDS category and supplier account should be mandatory
  #--------------------------------------------------------------------------------------------------------
  def validate_category_account(self, credit_account):
    if not self.doc.tds_category:
      msgprint("Please select TDS Category")
      raise Exception
      
    if not self.doc.supplier_account:
      self.doc.supplier_account = credit_account
    elif self.doc.supplier_account and self.doc.supplier_account != credit_account:
      msgprint("Supplier Account is not matching with the account mentioned in the table. Please select proper Supplier Account and click on 'Get TDS' button.")
      raise Exception
    

  #--------------------------------------------------------------------------------------------------------
  # If TDS is not applicable , all related fields should blank
  #--------------------------------------------------------------------------------------------------------
  def set_fields_null(self):
    self.doc.ded_amount = 0
    self.doc.rate = 0
    self.doc.tax_code = ''
    self.doc.tds_category = ''
    self.doc.supplier_account = ''
    
  #--------------------------------------------------------------------------------------------------------
  # Get TDS amount
  #--------------------------------------------------------------------------------------------------------
  def get_tds(self):
    if cstr(self.doc.is_opening) != 'Yes':
      if self.doc.total_debit > 0:
        self.get_tds_category_account()
        if self.doc.supplier_account and self.doc.tds_category:
          get_obj('TDS Control').get_tds_amount(self)          

        
  #--------------------------------------------------------------------------------------------------------
  # Insert new row to balance total debit and total credit
  #--------------------------------------------------------------------------------------------------------
  def get_balance(self):
    if not getlist(self.doclist,'entries'):
      msgprint("Please enter atleast 1 entry in 'GL Entries' table")
    else:
      flag, self.doc.total_debit, self.doc.total_credit = 0,0,0
      diff = flt(self.doc.difference)
      
      # If any row without amount, set the diff on that row
      for d in getlist(self.doclist,'entries'):
        if (d.credit==0 or d.credit is None) and (d.debit==0 or d.debit is None) and (flt(diff) != 0):
          if diff>0:
            d.credit = flt(diff)
          elif diff<0:
            d.debit = flt(diff)
          flag = 1
          
      # Set the diff in a new row
      if flag == 0 and (flt(diff) != 0):
        jd = addchild(self.doc, 'entries', 'Journal Voucher Detail', 1, self.doclist)
        if diff>0:
          jd.credit = flt(diff)
        elif diff<0:
          jd.debit = flt(diff)
          
      # Set the total debit, total credit and difference
      for d in getlist(self.doclist,'entries'):
        self.doc.total_debit += flt(d.debit)
        self.doc.total_credit += flt(d.credit)

      if self.doc.tds_applicable == 'Yes':
        self.doc.total_credit = flt(self.doc.total_credit) + flt(self.doc.ded_amount)

      self.doc.difference = flt(self.doc.total_debit) - flt(self.doc.total_credit)
      
  #--------------------------------------------------------------------------------------------------------
  # Set against account
  #--------------------------------------------------------------------------------------------------------
  def get_against_account(self):
    # Debit = Credit
    debit, credit = 0.0, 0.0
    debit_list, credit_list = [], []
    for d in getlist(self.doclist, 'entries'):
      debit += flt(d.debit)
      credit += flt(d.credit)
      if flt(d.debit)>0 and (d.account not in debit_list): debit_list.append(d.account)
      if flt(d.credit)>0 and (d.account not in credit_list): credit_list.append(d.account)

    self.doc.total_debit = debit
    if self.doc.tds_applicable == 'Yes':
      self.doc.total_credit = credit + flt(self.doc.ded_amount)
    else:
      self.doc.total_credit = credit

    if abs(self.doc.total_debit-self.doc.total_credit) > 0.001:
      msgprint("Debit must be equal to Credit. The difference is %s" % (self.doc.total_debit-self.doc.total_credit))
      raise Exception
    
    # update against account
    for d in getlist(self.doclist, 'entries'):
      if flt(d.debit) > 0: d.against_account = ', '.join(credit_list)
      if flt(d.credit) > 0: d.against_account = ', '.join(debit_list)


  # set aging date
  #---------------
  def set_aging_date(self):
    if self.doc.is_opening != 'Yes':
      self.doc.aging_date = self.doc.posting_date
    else:
      # check account type whether supplier or customer
      exists = ''
      for d in getlist(self.doclist, 'entries'):
        exists = sql("select name from tabAccount where account_type in ('Supplier', 'Customer') and name = '%s'" % d.account)
        if exists:
          break

      # If cus/supp aging dt is mandatory
      if exists and not self.doc.aging_date: 
        msgprint("Aging Date is mandatory for opening entry")
        raise Exception
      # otherwise aging dt = posting dt
      else:
        self.doc.aging_date = self.doc.posting_date

  # ------------------------
  # set print format fields
  # ------------------------
  def set_print_format_fields(self):
    for d in getlist(self.doclist, 'entries'):
      #msgprint(self.doc.company)
      chk_type = sql("select master_type, account_type from `tabAccount` where name='%s'" % d.account)
      master_type, acc_type = chk_type and cstr(chk_type[0][0]) or '', chk_type and cstr(chk_type[0][1]) or ''
      if master_type in ['Supplier', 'Customer']:
        if not self.doc.pay_to_recd_from:
          self.doc.pay_to_recd_from = get_value(master_type, ' - '.join(d.account.split(' - ')[:-1]), master_type == 'Customer' and 'customer_name' or 'supplier_name')
      
      if acc_type == 'Bank or Cash':
        dcc = TransactionBase().get_company_currency(self.doc.company)
        amt = cint(d.debit) and d.debit or d.credit	
        self.doc.total_amount = dcc +' '+ cstr(amt)
        self.doc.total_amount_in_words = get_obj('Sales Common').get_total_in_words(dcc, cstr(amt))


  # --------------------------------
  # get outstanding invoices values
  # --------------------------------
  def get_values(self):
    cond = (flt(self.doc.write_off_amount) > 0) and ' and outstanding_amount <= '+self.doc.write_off_amount or ''
    if self.doc.write_off_based_on == 'Accounts Receivable':
      return sql("select name, debit_to, outstanding_amount from `tabReceivable Voucher` where docstatus = 1 and company = '%s' and outstanding_amount > 0 %s" % (self.doc.company, cond))
    elif self.doc.write_off_based_on == 'Accounts Payable':
      return sql("select name, credit_to, outstanding_amount from `tabPayable Voucher` where docstatus = 1 and company = '%s' and outstanding_amount > 0 %s" % (self.doc.company, cond))


  # -------------------------
  # get outstanding invoices
  # -------------------------
  def get_outstanding_invoices(self):
    self.doc.clear_table(self.doclist, 'entries')
    total = 0
    for d in self.get_values():
      total += flt(d[2])
      jd = addchild(self.doc, 'entries', 'Journal Voucher Detail', 1, self.doclist)
      jd.account = cstr(d[1])
      if self.doc.write_off_based_on == 'Accounts Receivable':
        jd.credit = flt(d[2])
        jd.against_invoice = cstr(d[0])
      elif self.doc.write_off_based_on == 'Accounts Payable':
        jd.debit = flt(d[2])
        jd.against_voucher = cstr(d[0])
      jd.save(1)
    jd = addchild(self.doc, 'entries', 'Journal Voucher Detail', 1, self.doclist)
    if self.doc.write_off_based_on == 'Accounts Receivable':
      jd.debit = total
    elif self.doc.write_off_based_on == 'Accounts Payable':
      jd.credit = total
    jd.save(1)


  #--------------------------------------------------------------------------------------------------------
  # VALIDATE
  #--------------------------------------------------------------------------------------------------------
  def validate(self):
    if not self.doc.is_opening:
      self.doc.is_opening='No'
    self.get_against_account()
    self.validate_cheque_info()
    self.create_remarks()
    # tds
    get_obj('TDS Control').validate_first_entry(self)
    self.get_tds_category_account()

    self.validate_entries_for_advance()
    self.set_aging_date()
    
    self.validate_against_jv()
    self.set_print_format_fields()

    #FY and Date validation
    get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.posting_date,'Posting Date')

  #--------------------------------------------------------------------------------------------------------
  # On Update - Update Feed
  #--------------------------------------------------------------------------------------------------------
  def on_update(self):
    pass
        
  #--------------------------------------------------------------------------------------------------------
  # On submit
  #--------------------------------------------------------------------------------------------------------
  def on_submit(self):
    if self.doc.voucher_type in ['Bank Voucher', 'Contra Voucher', 'Journal Entry']:
      self.check_credit_days()
    self.check_account_against_entries()
    get_obj(dt='GL Control').make_gl_entries(self.doc, self.doclist)


  # validate against jv no
  def validate_against_jv(self):
    for d in getlist(self.doclist, 'entries'):
      if d.against_jv:
        if d.against_jv == self.doc.name:
          msgprint("You can not enter current voucher in 'Against JV' column")
          raise Exception
        elif not sql("select name from `tabJournal Voucher Detail` where account = '%s' and docstatus = 1 and parent = '%s'" % (d.account, d.against_jv)):
          msgprint("Against JV: "+ d.against_jv + " is not valid. Please check")
          raise Exception
          
  #--------------------------------------------------------------------------------------------------------
  # On cancel reverse gl entry
  #--------------------------------------------------------------------------------------------------------
  def on_cancel(self):
    self.check_tds_payment_voucher()
    get_obj(dt='GL Control').make_gl_entries(self.doc, self.doclist, cancel=1)

  # Check whether tds payment voucher has been created against this voucher
  #---------------------------------------------------------------------------
  def check_tds_payment_voucher(self):
    tdsp =  sql("select parent from `tabTDS Payment Detail` where voucher_no = '%s' and docstatus = 1 and parent not like 'old%'")
    if tdsp:
      msgprint("TDS Payment voucher '%s' has been made against this voucher. Please cancel the payment voucher to proceed." % (tdsp and tdsp[0][0] or ''))
      raise Exception
