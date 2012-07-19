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
    
  # Generate Periods
  #------------------		
  def generate_periods(self, fy):
    ml = ('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec')    

    import webnotes.utils
    from dateutil.relativedelta import relativedelta
    
    
    if not sql("select name from `tabPeriod` where fiscal_year = '%s'" % fy):
      ysd = sql("select year_start_date from `tabFiscal Year` where name = '%s'"%fy)[0][0]
      
      #create period as fiscal year record name
      #----------------------------------------------
      arg = {'pn':fy,'sd':ysd,'ed':webnotes.utils.get_last_day(ysd + relativedelta(months=11)).strftime('%Y-%m-%d'),'pt':'Year','fy':fy}
      self.create_period(arg)
            
      for i in range(12):    
        msd = ysd + relativedelta(months=i)

        arg = {'pn':ml[cint(msd.strftime('%m'))-1] + ' ' + msd.strftime('%Y'),'sd':msd.strftime('%Y-%m-%d'),'ed':webnotes.utils.get_last_day(msd).strftime('%Y-%m-%d'),'pt':'Month','fy':fy}
        self.create_period(arg)
          
  #---------------------------------------------------------
  #create period common function        
  def create_period(self,arg):
    p = Document('Period')
    p.period_name = arg['pn']
    p.start_date = arg['sd']
    p.end_date = arg['ed']
    p.period_type = arg['pt']
    p.fiscal_year = arg['fy']

    try:        
      p.save(1)  
    except NameError, e:
      msgprint('Period %s already exists' % p.period_name)
      raise Exception