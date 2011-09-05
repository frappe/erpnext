class DocType:
  def __init__(self,d,dl):
    self.doc, self.doclist = d, dl

  # Validate mandatory
  #-------------------
  def check_mandatory(self):
    # Following fields are mandatory in GL Entry
    mandatory = ['account','remarks','voucher_type','voucher_no','fiscal_year','company']
    for k in mandatory:
      if not self.doc.fields.get(k):
        msgprint("%s is mandatory for GL Entry" % k)
        raise Exception
        
    # Zero value transaction is not allowed
    if not (flt(self.doc.debit) or flt(self.doc.credit)):
      msgprint("GL Entry: Debit or Credit amount is mandatory for %s" % self.doc.account)
      raise Exception
      
    # Debit and credit can not done at the same time
    if flt(self.doc.credit) != 0 and flt(self.doc.debit) != 0:
      msgprint("Sorry you cannot credit and debit under same account head.")
      raise Exception, "Validation Error."
    
  # Cost center is required only if transaction made against pl account
  #--------------------------------------------------------------------
  def pl_must_have_cost_center(self):
    if sql("select name from tabAccount where name=%s and is_pl_account='Yes'", self.doc.account):
      if not self.doc.cost_center and not self.doc.voucher_type != 'Period Closing Entry':
        msgprint("Error: Cost Center must be specified for PL Account: %s" % self.doc.account_name)
        raise Exception
    else: # not pl
      if self.doc.cost_center:
        self.doc.cost_center = ''
    
  # Account must be ledger, active and not freezed
  #-----------------------------------------------
  def validate_account_details(self, adv_adj):
    ret = sql("select group_or_ledger, docstatus, freeze_account, company from tabAccount where name=%s", self.doc.account)
    
    # 1. Checks whether Account type is group or ledger
    if ret and ret[0][0]=='Group':
      msgprint("Error: All accounts must be Ledgers. Account %s is a group" % self.doc.account)
      raise Exception

    # 2. Checks whether Account is active
    if ret and ret[0][1]==2:
      msgprint("Error: All accounts must be Active. Account %s moved to Trash" % self.doc.account)
      raise Exception
      
    # 3. Account has been freezed for other users except account manager
    if ret and ret[0][2]== 'Yes' and not adv_adj and not 'Accounts Manager' in session['data']['roles']:
      msgprint("Error: Account %s has been freezed. Only Accounts Manager can do transaction against this account." % self.doc.account)
      raise Exception
      
    # 4. Check whether account is within the company
    if ret and ret[0][3] != self.doc.company:
      msgprint("Account: %s does not belong to the company: %s" % (self.doc.account, self.doc.company))
      raise Exception
      
  # Posting date must be in selected fiscal year and fiscal year is active
  #-------------------------------------------------------------------------
  def validate_posting_date(self):
    fy = sql("select docstatus, year_start_date from `tabFiscal Year` where name=%s ", self.doc.fiscal_year)
    ysd = fy[0][1]
    yed = get_last_day(get_first_day(ysd,0,11))
    pd = getdate(self.doc.posting_date)
    if fy[0][0] == 2:
      msgprint("Fiscal Year is not active. You can restore it from Trash")
      raise Exception
    if pd < ysd or pd > yed:
      msgprint("Posting date must be in the Selected Financial Year")
      raise Exception
      
  
  # Nobody can do GL Entries where posting date is before freezing date except 'Accounts Manager'
  #----------------------------------------------------------------------------------------------
  def check_freezing_date(self, adv_adj):
    if not adv_adj:
      pd,fd = getdate(self.doc.posting_date),0
      acc_frozen_upto = get_obj(dt = 'Manage Account').doc.acc_frozen_upto or ''
      if acc_frozen_upto:
        fd = getdate(acc_frozen_upto)
      
      bde_auth_role = get_value( 'Manage Account', None,'bde_auth_role')
      if fd and pd <= fd and (bde_auth_role and not bde_auth_role in session['data']['roles']):
        msgprint("Message:You are not authorized to do back dated entries for account: %s before %s." % (self.doc.account, str(fd)))
        raise Exception

  # create new bal if not exists
  #-----------------------------
  def create_new_balances(self, ac_obj, p, amt):
    ac = addchild(ac_obj.doc, 'account_balances', 'Account Balance', 1)
    ac.period = p[0]
    ac.start_date = p[1].strftime('%Y-%m-%d')
    ac.end_date = p[2].strftime('%Y-%m-%d')
    ac.fiscal_year = p[3]
    ac.opening = 0
    ac.balance = amt
    ac.save()

  # Post Balance
  # ------------
  def post_balance(self, acc):
    # get details
    lft = sql("select lft, rgt, debit_or_credit from `tabAccount` where name='%s'" % acc)

    # amount to debit
    amt = flt(self.doc.debit) - flt(self.doc.credit)
    if lft[0][2] == 'Credit': amt = -amt

    # get periods
    periods = self.get_period_list(self.doc.posting_date, self.doc.fiscal_year)
    
    acc_obj = get_obj('Account', self.doc.account)
    for p in periods:
      if not sql("select name from `tabAccount Balance` where parent=%s and period=%s", (self.doc.account, p[0])):
        self.create_new_balances(acc_obj, p, amt)
      else:
        # update current
        pl = sql("update `tabAccount Balance` t1, `tabAccount` t2 set t1.balance = t1.balance + %s where t2.lft<=%s and t2.rgt>=%s and t1.parent = t2.name and t1.period = '%s'" % (amt, cint(lft[0][0]), cint(lft[0][1]), p[0]))

    # update opening
    if self.doc.is_opening=='Yes':
      pl = sql("update `tabAccount Balance` t1, `tabAccount` t2 set t1.opening = ifnull(t1.opening,0) + %s where t2.lft<=%s and t2.rgt>=%s and t1.parent = t2.name and t1.period = '%s'" % (amt, cint(lft[0][0]), cint(lft[0][1]), self.doc.fiscal_year))
    
  # Get periods(month and year)
  #-----------------------------
  def get_period_list(self, dt, fy):
    pl = sql("SELECT name, start_date, end_date, fiscal_year FROM tabPeriod WHERE end_date >='%s' and fiscal_year = '%s' and period_type in ('Month', 'Year')" % (dt,fy))
    return pl

  # Voucher Balance
  # ---------------  
  def update_outstanding_amt(self):
    # get final outstanding amt
    bal = flt(sql("select sum(debit)-sum(credit) from `tabGL Entry` where against_voucher=%s and against_voucher_type=%s and ifnull(is_cancelled,'No') = 'No'", (self.doc.against_voucher, self.doc.against_voucher_type))[0][0] or 0.0)
    tds = 0
    
    if self.doc.against_voucher_type=='Payable Voucher':
      # amount to debit
      bal = -bal
      
      # Check if tds applicable
      tds = sql("select total_tds_on_voucher from `tabPayable Voucher` where name = '%s'" % self.doc.against_voucher)
      tds = tds and flt(tds[0][0]) or 0
    
    # Validation : Outstanding can not be negative
    if bal < 0 and not tds and self.doc.is_cancelled == 'No':
      msgprint("Outstanding for Voucher %s will become %s. Outstanding cannot be less than zero. Please match exact outstanding." % (self.doc.against_voucher, fmt_money(bal)))
      raise Exception
      
    # Update outstanding amt on against voucher
    sql("update `tab%s` set outstanding_amount=%s where name='%s'"% (self.doc.against_voucher_type,bal,self.doc.against_voucher))
    
          
  # Total outstanding can not be greater than credit limit for any time for any customer
  #---------------------------------------------------------------------------------------------
  def check_credit_limit(self):
    #check for user role Freezed
    master_type=sql("select master_type from `tabAccount` where name='%s' " %self.doc.account)
    tot_outstanding = 0  #needed when there is no GL Entry in the system for that acc head
    if (self.doc.voucher_type=='Journal Voucher' or self.doc.voucher_type=='Receivable Voucher') and (master_type and master_type[0][0]=='Customer'):
      dbcr=sql("select sum(debit),sum(credit) from `tabGL Entry` where account = '%s' and is_cancelled='No'" % self.doc.account)
      if dbcr:
        tot_outstanding = flt(dbcr[0][0])-flt(dbcr[0][1])+flt(self.doc.debit)-flt(self.doc.credit)
      get_obj('Account',self.doc.account).check_credit_limit(self.doc.account, self.doc.company, tot_outstanding)
  
  #for opening entry account can not be pl account
  #-----------------------------------------------
  def check_pl_account(self):
    if self.doc.is_opening=='Yes':
      is_pl_account=sql("select is_pl_account from `tabAccount` where name='%s'"%(self.doc.account))
      if is_pl_account and is_pl_account[0][0]=='Yes':
        msgprint("For opening balance entry account can not be a PL account")
        raise Exception

  # Validate
  # --------
  def validate(self):  # not called on cancel
    self.check_mandatory()
    self.pl_must_have_cost_center()
    self.validate_posting_date()
    self.doc.is_cancelled = 'No' # will be reset by GL Control if cancelled
    self.check_credit_limit()
    self.check_pl_account()

  # On Update
  #----------
  def on_update(self,adv_adj):
    # Account must be ledger, active and not freezed
    self.validate_account_details(adv_adj)
    
    # Posting date must be after freezing date
    self.check_freezing_date(adv_adj)
    
    # Update current account balance
    self.post_balance(self.doc.account)
    
    # Update outstanding amt on against voucher
    if self.doc.against_voucher:
      self.update_outstanding_amt()