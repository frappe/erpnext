class DocType:
  def __init__(self,d,dl):
    self.doc, self.doclist = d, dl
    
  # Get monthly budget
  #-------------------
  def get_monthly_budget(self, distribution_id, cfy, st_date, post_dt, budget_allocated):
    
    # get month_list
    st_date, post_dt = getdate(st_date), getdate(post_dt)
    
    if distribution_id:
      if st_date.month <= post_dt.month:
        tot_per_allocated = sql("select ifnull(sum(percentage_allocation),0) from `tabBudget Distribution Detail` where parent='%s' and idx between '%s' and '%s'" % (distribution_id, st_date.month, post_dt.month))[0][0]

      if st_date.month > post_dt.month:
    
        tot_per_allocated = flt(sql("select ifnull(sum(percentage_allocation),0) from `tabBudget Distribution Detail` where parent='%s' and idx between '%s' and '%s'" % (distribution_id, st_date.month, 12 ))[0][0])
        tot_per_allocated = flt(tot_per_allocated)  + flt(sql("select ifnull(sum(percentage_allocation),0) from `tabBudget Distribution Detail` where parent='%s' and idx between '%s' and '%s'" % (distribution_id, 1, post_dt.month))[0][0])
     
      return (flt(budget_allocated) * flt(tot_per_allocated)) / 100
    period_diff = sql("select PERIOD_DIFF('%s','%s')" % (post_dt.strftime('%Y%m'), st_date.strftime('%Y%m')))
    
    return (flt(budget_allocated) * (flt(period_diff[0][0]) + 1)) / 12
    
  def validate_budget(self, acct, cost_center, actual, budget, action):
    # action if actual exceeds budget
    if flt(actual) > flt(budget):
      msgprint("Your monthly expense "+ cstr((action == 'stop') and "will exceed" or "has exceeded") +" budget for <b>Account - "+cstr(acct)+" </b> under <b>Cost Center - "+ cstr(cost_center) + "</b>"+cstr((action == 'Stop') and ", you can not have this transaction." or "."))
      if action == 'Stop': raise Exception

  def check_budget(self,le_list,cancel):
    # get value from record
    acct, cost_center, debit, credit, post_dt, cfy, company  = le_list

    # get allocated budget
    bgt = sql("select t1.budget_allocated, t1.actual, t2.distribution_id from `tabBudget Detail` t1, `tabCost Center` t2 where t1.account='%s' and t1.parent=t2.name and t2.name = '%s' and t1.fiscal_year='%s'" % (acct,cost_center,cfy), as_dict =1)
    curr_amt = ((cancel and -1  or 1) * flt(debit)) + ((cancel and 1  or -1) *  flt(credit))
    
    if bgt and bgt[0]['budget_allocated']:
      # check budget flag in Company
      bgt_flag = sql("select yearly_bgt_flag, monthly_bgt_flag from `tabCompany` where name = '%s'" % company, as_dict =1)
      
      if bgt_flag and bgt_flag[0]['monthly_bgt_flag'] in ['Stop', 'Warn']:
        # get start date and last date
        st_date = get_value('Fiscal Year', cfy, 'year_start_date').strftime('%Y-%m-%d')
        lt_date = sql("select LAST_DAY('%s')" % post_dt)
        
        # get Actual
        actual = get_obj('GL Control').get_period_difference(acct + '~~~' + cstr(st_date) + '~~~' + cstr(lt_date[0][0]), cost_center)
      
        # Get Monthly  budget
        budget = self.get_monthly_budget(bgt and bgt[0]['distribution_id'] or '' , cfy, st_date, post_dt, bgt[0]['budget_allocated'])
      
        # validate monthly budget
        self.validate_budget(acct, cost_center, flt(actual) + flt(curr_amt), budget, 'monthly_bgt_flag')

      # update actual against budget allocated in cost center
      sql("update `tabBudget Detail` set actual = ifnull(actual,0) + %s where account = '%s' and fiscal_year = '%s' and parent = '%s'" % (curr_amt,cstr(acct),cstr(cfy),cstr(cost_center)))