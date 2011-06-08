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
  def __init__(self,d,dt):
    self.doc, self.doclist = d,dt
    
  #==========================================================================
  def get_att_list(self):
    
    lst = [['Attendance','','','Please fill columns which are Mandatory.',' Please do not modify the structure','',''],['','','','','','',''],['[Mandatory]','','[Mandatory]','[Mandatory]','[Mandatory]','[Mandatory]','[Mandatory]'],['Employee','Employee Name','Attendance Date','Status','Fiscal Year','Company','Naming Series']]
    
    dt = self.date_diff_list()          # get date list inbetween from date and to date
    
    att_dt = self.get_att_data()        # get default attendance data like fiscal yr, company, naming series
      
    fy, comp, sr = att_dt['fy'], att_dt['comp'], att_dt['sr']
   
    res = sql("select name, employee_name from `tabEmployee` where status = 'Active' and docstatus !=2") 
   
    for d in dt:
      for r in res:       
        lst.append([r[0],r[1],d,'',fy,comp,sr])

    return lst
  
  #------------------------------------------------------------------------------
  # get date list inbetween from date and to date
  def date_diff_list(self):
    import datetime
    #get from date 
    att_fr_date = self.doc.att_fr_date and self.doc.att_fr_date or ''
    
    #get to date
    att_to_date = self.doc.att_to_date and self.doc.att_to_date or ''

    if att_to_date:
      r = (getdate(self.doc.att_to_date)+datetime.timedelta(days=1)-getdate(self.doc.att_fr_date)).days
    else:
      r = 1
    dateList = [getdate(self.doc.att_fr_date)+datetime.timedelta(days=i) for i in range(0,r)]
    dt=([str(date) for date in dateList])
    
    return dt

  #------------------------------------------------------------------------------
  def get_att_data(self):
    
    fy = get_defaults()['fiscal_year']    #get default fiscal year 

    comp = get_defaults()['company']    #get default company
    
    #get naming series of attendance
    #sr = sql("select series_options from `tabNaming Series Options` where doc_type='Attendance'")
    sr = sql("select options from `tabDocField` where parent = 'Attendance' and fieldname = 'naming_series'")
    if not sr:
      msgprint("Please create naming series for Attendance.\nGo to Setup--> Manage Series.")
      raise Exception
    else:
      sr = sr and sr[0][0]
    
    return {'fy':fy,'comp':comp,'sr':sr}

  #=================================================================================  
  def import_att_data(self):
    filename = self.doc.file_list.split(',')

    if not filename:
      msgprint("Please attach a .CSV File.")
      raise Exception
    
    if filename[0].find('.csv') < 0:
      raise Exception
    
    if not filename and filename[0] and file[1]:
      msgprint("Please Attach File. ")
      raise Exception
      
    from webnotes.utils import file_manager
    fn, content = file_manager.get_file(filename[1])
    
    if not type(content) == str:
      content = content.tostring()

    import webnotes.model.import_docs
    im = webnotes.model.import_docs.CSVImport()
    out = im.import_csv(content,self.doc.import_date_format, cint(self.doc.overwrite))
    return out

