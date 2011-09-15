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
  #init function
  def __init__(self,doc,doclist=[]):
    self.doc = doc
    self.doclist = doclist  
  
  def autoname(self):
    self.doc.name = make_autoname('IT Check/' +self.doc.employee + '/.#####')
    
  #===========================================================
  #check for already exist IT Checklist for resp. Employee
  def exist_IT_Check(self):
    
    #query for return already exist IT Checklist for respective employee
    exist_ret = sql("select name from `tabIT Checklist` where is_cheklist_active = 'Yes' and employee = '%s' and name!='%s'"%(self.doc.employee,self.doc.name))
    
    # validation - if exist then raise exception 
    if exist_ret:
      msgprint("Active IT Checklist '%s' for employee '%s' exist."%(exist_ret[0][0],self.doc.employee))
      self.doc.employee = ""
      self.doc.basic = 0
      self.doc.gross_income = 0
      self.doc.pf = 0
      return 0
    else:
      flag = self.exist_sal_struct() #check for slaray structure exist or not, if exist then further action can be done.
      return flag
      
  #===========================================================
  #check for salary structure exist or not, if exist then further action can be done.
  def exist_sal_struct(self):
    #query return salary structure for particular employee exist or not
    exist_salstr=sql("select name from `tabSalary Structure` where employee = '%s' and is_active='Yes'"%self.doc.employee)
    if not exist_salstr:
      msgprint("Please first create salary structure for employee '%s'"%self.doc.employee)
      self.doc.employee = ''
      return 0
    else:
      return 1
    
  #===========================================================
  #get previous salary slip gross income and basic amount
  def get_info(self):
    ret_sal_slip = sql("select count(name), sum(gross_pay) from `tabSalary Slip` where docstatus =1 and fiscal_year = '%s' and employee = '%s'"%(self.doc.fiscal_year,self.doc.employee))
    
    sum_basic = sum_pf = 0
    
    if ret_sal_slip:
      #get name of salary slip of resp. employee 
      ret_name =convert_to_lists(sql("select name from `tabSalary Slip` where docstatus =1 and fiscal_year = '%s' and employee = '%s' "%(self.doc.fiscal_year,self.doc.employee)))
      
      if ret_name:
        for b in ret_name:
          #get earning amount of basic 
          ret_basic = sql("select e_amount from `tabSS Earning Detail` where parent = '%s' and e_type = 'Basic'"%(b[0]))
          sum_basic += ret_basic[0][0] or 0  
          
          #get deduction amount of Provident Fund
          ret_pf = sql("select d_amount from `tabSS Deduction Detail` where parent = '%s' and d_type = 'Provident Fund'"%(b[0]))
          
          sum_pf += ret_pf[0][0] or 0
                  
    ret_list = [ret_sal_slip[0][0] or 0,ret_sal_slip[0][1] or 0, sum_basic, sum_pf]
    return ret_list  
  
  #-------------------------------------------
  def get_basic_gross(self,ret_list0,ret_list1,ret_list2):
   
    self.doc.basic = self.doc.gross_income = 0
    #query return list of earning types and resp. modified amount
    ret = convert_to_lists(sql("select e.e_type, e.modified_value from `tabEarning Detail` e , `tabSalary Structure` s where s.is_active = 'Yes' and s.employee='%s' and e.parent = s.name" %(self.doc.employee)))
    hra_count=1
    if ret:
      count = 0.0
      for i in ret:
        if i[0] == 'Basic':
          if i[1] == 0:  
            msgprint("Basic is zero in salary structure")

          self.doc.basic = flt(i[1])*(12-int(ret_list0)) + flt(ret_list2)
        count += flt(i[1])
        if i[0] =='House Rent Allowance':
          hra_count = flt(i[1])
      if count == 0:
        msgprint("Gross Income is zero in salary structure")    

     
      self.doc.gross_income = count*(12-int(ret_list0)) + flt(ret_list1)

    if hra_count == 0 or hra_count == "":
      hra_count=1
          
    return hra_count
    
  #-------------------------------------------
  def get_pf(self,ret_list0,ret_list3):
    self.doc.pf = 0.0    
              
    #query returns amount 
    ret_ded = sql("select d.d_modified_amt from `tabDeduction Detail` d , `tabSalary Structure` s where s.is_active = 'Yes' and s.employee='%s' and d.parent = s.name and d.d_type = 'Provident Fund'" %(self.doc.employee))
    
    if not ret_ded:
      msgprint("PF Amount in Salary Structure is zero")
    
    ret_ded = flt(ret_ded[0][0]) or 0
        
    #annual pf = salary structure * (12 - remaining month to complete fiscal year)- previous salary slip's total pf for current fiscal year
    self.doc.pf = (ret_ded*(12 - int(ret_list0)))+flt(ret_list3)  
    
    
  #-------------------------------------------
  def set_values(self):
    hra_count=1
    if not self.doc.fiscal_year:
      msgprint("Please select Fiscal Year")
      self.doc.employee = ''
    
    elif self.doc.employee:
      
      flag = self.exist_IT_Check()   #check for already exist IT Checklist for resp. Employee
    
      if flag == 1:
     
        ename = sql("select employee_name from `tabEmployee` where name = '%s'"%self.doc.employee)[0][0]
        set(self.doc,'employee_name',cstr(ename))
        #call get_info to get values of salary slip's total basic, pf and gross income amount
        ret_list = self.get_info()

        self.get_pf(ret_list[0],ret_list[3])
      
        hra_count = self.get_basic_gross(ret_list[0],ret_list[1],ret_list[2])        
  
    return hra_count
  
  #===========================================================  
  #-------------------------------------------
  def set_tables(self, hra_count):        #set tables values
    
    self.set_exemption_table(hra_count)
    self.set_other_income_table()
    self.set_deduction_via_table()
    self.set_invest_80c_table()
    self.doc.edu_cess = self.doc.tax_tot_income = self.doc.net_tot_tax_income = self.doc.tax_per_month = 0
    self.doc.applicable_from = self.doc.rem_months=''
    msgprint("Successful")
    return ''
  
  #-------------------------------------------
  def get_month_diff(self):
    #end_month = get_defaults()['end_month']
      
    month_dict = {"January" :'01', "February" :'02',"March" :'03',"April":'04',"May":'05',"June":'06',"July":'07',"August":'08',"September":'09',"October":'10',"November":'11',"December":'12'}
    
    import datetime

    start_month =  getdate(get_defaults()['year_start_date']).month
    end_month = cint(start_month) - 1
    if end_month <= 0:
      end_month = 12
    str_end_month = cstr(end_month)
    
    if len(str_end_month)==1:
      str_end_month = '0'+str_end_month
    
    
    to_month = datetime.date.today().strftime("%B")
    to_year = datetime.date.today().strftime("%Y")
    
    fiscal_year = self.doc.fiscal_year
    
    str_fy =fiscal_year.split("-")
    
    endym=int(str_fy[1]+str_end_month)
    startym= int(to_year+month_dict[to_month])

    month_diff =sql("SELECT PERIOD_DIFF(%d,%d);" %(endym,startym))[0][0]+1
    
    return month_diff
  
  
 
  #------------------------------------------- 
  def set_exemption_values(self,ann_hra):
    ret = convert_to_lists(sql("select name, exemption_limit from `tabEarning Type` where taxable = 'No' and docstatus !=2"))
    
    if ret:
      for r in ret:

        ch = addchild(self.doc,'exe_declaration_details','Declaration Detail',0, self.doclist)
        ch.particulars1 = r[0]
        ch.under_section1 = "U/Sec 10 & 17"
        
        if r[0] == 'House Rent Allowance':
          if (self.doc.ann_rent <= 0.00):
            ch.max_limit1 = 0.00
            
          else:
            hra1=0.00
            if(self.doc.metro == 'Yes'):
              hra1 = flt(self.doc.basic)*50/100
            elif(self.doc.metro == 'No'):
              hra1 = flt(self.doc.basic)*40/100
            hra2 = flt(ann_hra)
            hra3 = flt(self.doc.ann_rent) - (flt(self.doc.basic)/10)


            if hra1 <= 0 or hra2 <=0 or hra3 <=0:
              ch.max_limit1 = 0
            else:
              ch.max_limit1=min(hra1,min(hra2,hra3))
        else:    
          ch.max_limit1 = r[1]
        
        ch.actual_amount1 = 0.00
        ch.eligible_amount1 = 0.00
        ch.modified_amount1 = 0.00
  
  #-------------------------------------------    
  def set_exemption_table(self, hra_count):
    self.doc.clear_table(self.doclist, 'exe_declaration_details',1)
    ann_hra = 0
    if (self.doc.ann_rent > 0):
    
      #query return sum of earning types amount where earning type = 'HRA'
      ret_sal_slip = sql("select sum(e.e_amount) from `tabSS Earning Detail` e , `tabSalary Slip` s where s.fiscal_year = '%s' and s.docstatus = 1 and s.employee='%s' and e.parent = s.name and e.e_type = 'House Rent Allowance'" %(self.doc.fiscal_year,self.doc.employee))
      if not ret_sal_slip:
        ret_sal_slip = 0.00
      else:
        ret_sal_slip = ret_sal_slip[0][0]      
     
      month_diff = self.get_month_diff()     
      
      #ret_sal_slip = ret_sal_slip[0][0] or 0.00
      ann_hra = (flt(hra_count)*flt(month_diff))+flt(ret_sal_slip);
      
    self.set_exemption_values(ann_hra)
 
  #-------------------------------------------     
  def set_other_income_table(self):
    self.doc.clear_table(self.doclist, 'oth_inc_decl_details',1)
    other_income =[["Income from Housing","----",0.00],["Relief on interest paid on Housing Loan","U/S 24(1)(Vi)",150000],["Any other Income","----",0.00]]
    
    for oi in other_income:
      ch1 = addchild(self.doc,'oth_inc_decl_details','Other Income Detail',0, self.doclist)
      ch1.particulars2 = oi[0]
      ch1.under_section2 = oi[1]
      ch1.max_limit2 = oi[2]
      ch1.actual_amount2 = 0.00
      ch1.eligible_amount2 = 0.00
      ch1.modified_amount2 = 0.00
  
  
  #---------------------------------------  
  def get_maxlmt_via(self):
    if(self.doc.part_sr_citizen == 'Yes'): 
      max_lmt1 = 20000
    else:
      max_lmt1 = 15000
      
    if(self.doc.per_dep_dis == "Less than 80% disability"):
      max_lmt2 = 50000
    elif(self.doc.per_dep_dis == "More than 80% disability"):
      max_lmt2 = 100000
    else:
      max_lmt2 = 0.00

    if(self.doc.per_self_dis == "Less than 80% disability"):
      max_lmt3 = 50000
    elif(self.doc.per_self_dis == "More than 80% disability"):
      max_lmt3 = 75000
    else:
      max_lmt3 = 0.00
    
    maxlmt_lst=[max_lmt1,max_lmt2,max_lmt3]
    
    return maxlmt_lst

  #---------------------------------------     
  def set_deduction_via_table(self):
    self.doc.clear_table(self.doclist, 'chap_via_decl_details',1)
    
    maxlmt_lst = self.get_maxlmt_via()

    deduct_via = [["Medical Insurance Premium","U/Sec 80D(2A)",15000],["Medical Insurance Premium for parents","U/Sec 80D(2A)", maxlmt_lst[0]],["Medical for handicapped dependents","U/Sec 80DD",maxlmt_lst[1]],["Medical for specified diseases","U/Sec 80DDB",40000],["Higher Education Loan Interest Repayment","U/Sec 80E",0.00],["*Donation to approved Fund and charities","U/sec 80G",0.00],["*Rent deduction only if HRA not received","U/sec 80GG",0.00],["Deduction for permanent disability","U/Sec 80 U",maxlmt_lst[2]],["Any other deductions","----",0.00]]
   
    
    for dv in deduct_via:
      ch = addchild(self.doc,'chap_via_decl_details','Chapter VI A Detail',0, self.doclist)
      ch.particulars3 = dv[0]
      ch.under_section3 = dv[1]
      ch.max_limit3 = dv[2]
      ch.actual_amount3 = 0.00
      ch.eligible_amount3 = 0.00
      ch.modified_amount3 = 0.00
    
   
  #----------------------------------------   
  def set_invest_80c_table(self):
    self.doc.clear_table(self.doclist, 'invest_80_decl_details',1)
    invest_lst = [["Employees Provident Fund","U/Sec 80C",0.00],["Voluntary Contribution Provident Fund","U/Sec 80C",0.00],["Investment in Pension Scheme","U/Sec 80 CCC",10000],["Housing Loan Principal Repayment","U/Sec 80C",0.00],["Public Provident Fund (PPF)","U/Sec 80C",0.00],["Life Insurance Premium Paid","U/Sec 80C",0.00],["Unit Linked Insurance Plans","U/Sec 80C",0.00],["NSC - National Saving Certificate","U/Sec 80C",0.00],["Deposite in National Saving Scheme (NSS)","U/Sec 80C",0.00],["Infrastructure Investment in approved Shares, Debentures & Bonds","U/Sec 80C",0.00],["Mutual Funds notified under Section 10 (23D)","U/Sec 80C",0.00],["Equity Link Saving Scheme (ELSS) Mutual Funds notified under Section 10 (23D)","U/Sec 80C",0.00],["Term Deposite with a SCH. Bank in a notified Scheme for a team not less than 5 years ","U/Sec 80C",0.00],["Tution Fees Paid (Only full time education tution fees paid to any Indian Univ, College, School)","U/Sec 80C","24000"],["Senior Citizen Savings Scheme Rules, 2004","U/Sec 80C",0.00],["Post Office Time Deposit Rules, 1981 for a term not less than 5 years","U/Sec 80C",0.00]]
  
  
    for il in invest_lst:
      ch = addchild(self.doc,'invest_80_decl_details','Invest 80 Declaration Detail',0, self.doclist)
      ch.particulars4 = il[0]
      ch.under_section4 = il[1]
      ch.max_limit4 = il[2]
      ch.actual_amount4 = 0.00
      ch.eligible_amount4 = 0.00
      ch.modified_amount4 = 0.00
      
      
  #---------------------------------------
  def sum_mod_val(self):
    count = count1 = count2 = 0.0
    
    for e in getlist(self.doclist,'exe_declaration_details'):
      count += flt(e.modified_amount1)
    
    count = round(flt(self.doc.gross_income)) - count
    
    for oi in getlist(self.doclist,'oth_inc_decl_details'):
      count += flt(oi.modified_amount2)
    
    for vi in getlist(self.doclist,'chap_via_decl_details'):
      count2 += flt(vi.modified_amount3)
    
    count = count - count2
    
    for inv in getlist(self.doclist,'invest_80_decl_details'):
      count1 += flt(inv.modified_amount4)
      if(count1 >= 100000):
        break
      
    if(count1>100000):
      count1=100000
      
    count_lst = [count,count1]
    return count_lst
  
  #----------------------------------------  
  def calculate_tax(self):
    
    count_lst = self.sum_mod_val()
    
    count = round(flt(count_lst[0]) - flt(count_lst[1]))
    if(count>0):
      self.doc.net_tot_tax_income = count
      
      ret_gender = sql("select gender from `tabEmployee` where name = '%s' "%self.doc.employee)[0][0]
      
      if(self.doc.sr_citizen == 'Yes'):
        self.calc_tax(count,240000)        
      elif(ret_gender == 'Male'):
        self.calc_tax(count,160000)
      elif(ret_gender == 'Female'):
        self.calc_tax(count,190000)
    else:
      self.doc.net_tot_tax_income = 0
      self.doc.tax_tot_income = 0
      self.doc.edu_cess = 0
  #-----------------------------------------------    
  def calc_tax(self,count,upper_limit):
    balance = 0
    tax = 0
    if(count> upper_limit):
      balance = count - upper_limit
      if balance > (500000 - upper_limit):
        balance = balance - (500000 - upper_limit)
        tax = round(balance/10)
        if balance > 300000:
          balance = balance - 300000
          tax = round(tax+ 60000)
          if balance > 0:
            tax = round(tax + (balance * 30 / 100))
        else:
          tax = round(balance * 20 / 100 )
      else:
        tax = round(balance /10)
    else:
      tax = 0
    
    self.doc.tax_tot_income = tax
    self.doc.edu_cess = round(tax*3/100)
    
  #-----------------------------------------------     
  def calc_tax_pm(self):
       
    ret_income_tax = 0
    ret_income_tax = sql("select sum(d.d_amount) from `tabSS Deduction Detail` d , `tabSalary Slip` s where s.docstatus = 1 and s.fiscal_year = '%s' and s.employee='%s' and d.parent = s.name and d.d_type = 'Income Tax'" %(self.doc.fiscal_year,self.doc.employee))
    
    new_tot_income = cint(self.doc.tax_tot_income) + cint(self.doc.edu_cess) - (cint(ret_income_tax[0][0]) or 0)
    
    self.doc.tax_per_month = new_tot_income/cint(self.doc.rem_months)

  # on update
  def on_update(self):
    obj = get_obj('Feed Control', 'Feed Control')
   
    obj.make_feed(self.doc)