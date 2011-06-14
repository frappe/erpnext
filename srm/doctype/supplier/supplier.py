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
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist

  def autoname(self):
    #get default naming conventional from control panel
    supp_master_name = get_defaults()['supp_master_name']

    if supp_master_name == 'Supplier Name':
    
      # filter out bad characters in name
      #supp = self.doc.supplier_name.replace('&','and').replace('.','').replace("'",'').replace('"','').replace(',','').replace('`','')
      supp = self.doc.supplier_name
      
      cust = sql("select name from `tabCustomer` where name = '%s'" % (supp))
      cust = cust and cust[0][0] or ''
    
      if cust:
        msgprint("You already have a Customer with same name")
        raise Exception
      self.doc.name = supp
      
    else:
      self.doc.name = make_autoname(self.doc.naming_series+'.#####')

  # ----------------------------------------
  # update credit days and limit in account
  # ----------------------------------------
  def update_credit_days_limit(self):
    sql("update tabAccount set credit_days = '%s' where name = '%s'" % (self.doc.credit_days, self.doc.name + " - " + self.get_company_abbr()))


  def on_update(self):
    if not self.doc.naming_series:
      self.doc.naming_series = ''

  
    # create address
    addr_flds = [self.doc.address_line1, self.doc.address_line2, self.doc.city, self.doc.state, self.doc.country, self.doc.pincode]
    address_line = "\n".join(filter(lambda x : (x!='' and x!=None),addr_flds))
    set(self.doc,'address', address_line)

    # create account head
    self.create_account_head()

		# update credit days and limit in account
    self.update_credit_days_limit()


  def check_state(self):
    return "\n" + "\n".join([i[0] for i in sql("select state_name from `tabState` where `tabState`.country='%s' " % self.doc.country)])
  
  # ACCOUNTS
  # -------------------------------------------
  def get_payables_group(self):
    g = sql("select payables_group from tabCompany where name=%s", self.doc.company)
    g = g and g[0][0] or ''
    if not g:
      msgprint("Update Company master, assign a default group for Payables")
      raise Exception
    return g

  def add_account(self, ac, par, abbr):
    arg = {'account_name':ac,'parent_account':par, 'group_or_ledger':'Group', 'company':self.doc.company,'account_type':'','tax_rate':'0'}
    t = get_obj('GL Control').add_ac(cstr(arg))
    msgprint("Created Group " + t)
  
  def get_company_abbr(self):
    return sql("select abbr from tabCompany where name=%s", self.doc.company)[0][0]
  
  def get_parent_account(self, abbr):
    if (not self.doc.supplier_type):
      msgprint("Supplier Type is mandatory")
      raise Exception
    
    if not sql("select name from tabAccount where name=%s", (self.doc.supplier_type + " - " + abbr)):

      # if not group created , create it
      self.add_account(self.doc.supplier_type, self.get_payables_group(), abbr)
    
    return self.doc.supplier_type + " - " + abbr


  def validate(self):
    #validation for Naming Series mandatory field...
    if get_defaults()['supp_master_name'] == 'Naming Series':
      if not self.doc.naming_series:
        msgprint("Series is Mandatory.")
        raise Exception
  
  
  # create accont head - in tree under zone + territory
  # -------------------------------------------------------
  def create_account_head(self):
    if self.doc.company :
      abbr = self.get_company_abbr() 
            
      if not sql("select name from tabAccount where name=%s", (self.doc.name + " - " + abbr)):
        parent_account = self.get_parent_account(abbr)
        
        arg = {'account_name':self.doc.name,'parent_account': parent_account, 'group_or_ledger':'Ledger', 'company':self.doc.company,'account_type':'','tax_rate':'0','master_type':'Supplier','master_name':self.doc.name,'address':self.doc.address}
        # create
        ac = get_obj('GL Control').add_ac(cstr(arg))
        msgprint("Created Account Head: "+ac)
        
    else : 
      msgprint("Please select Company under which you want to create account head")
      
      
  def get_contacts(self,nm):
    if nm:    
      contact_details =convert_to_lists(sql("select name, CONCAT(IFNULL(first_name,''),' ',IFNULL(last_name,'')),contact_no,email_id from `tabContact` where supplier = '%s'"%nm))
   
      return contact_details
    else:
      return ''
