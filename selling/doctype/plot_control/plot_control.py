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

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, cstr, get_defaults, now
from webnotes.model import db_exists
from webnotes.model.wrapper import copy_doclist

sql = webnotes.conn.sql
	


class DocType:
  def __init__(self,doc,doclist = []):
    self.doc ,self.doclist = doc, doclist

  #============================get monthly sales====================================================  
  def get_monthwise_amount(self,lst):
    lst = lst.split(',')
    if not lst[1]:
      ret = webnotes.conn.convert_to_lists(sql("SELECT SUM(grand_total) AMOUNT,CASE MONTH(due_date) WHEN 1 THEN 'JAN' WHEN 2 THEN 'FEB' WHEN 3 THEN 'MAR' WHEN 4 THEN 'APR' WHEN 5 THEN 'MAY' WHEN 6 THEN 'JUN' WHEN 7 THEN 'JUL' WHEN 8 THEN 'AUG' WHEN 9 THEN 'SEP' WHEN 10 THEN 'OCT' WHEN 11 THEN 'NOV' WHEN 12 THEN 'DEC' END MONTHNAME FROM `tabSales Invoice` WHERE docstatus = 1 AND fiscal_year = '%s' GROUP BY MONTH(due_date) ORDER BY MONTH(due_date)"%lst[0]))
    else:
      ret = webnotes.conn.convert_to_lists(sql("select sum(t2.amount) AMOUNT ,CASE MONTH(t1.due_date) WHEN 1 THEN 'JAN' WHEN 2 THEN 'FEB' WHEN 3 THEN 'MAR' WHEN 4 THEN 'APR' WHEN 5 THEN 'MAY' WHEN 6 THEN 'JUN' WHEN 7 THEN 'JUL' WHEN 8 THEN 'AUG' WHEN 9 THEN 'SEP' WHEN 10 THEN 'OCT' WHEN 11 THEN 'NOV' WHEN 12 THEN 'DEC' END MONTHNAME from `tabSales Invoice` t1,`tabSales Invoice Item` t2 WHERE t1.name = t2.parent and t1.docstatus = 1 and t2.item_group = '%s' AND t1.fiscal_year = '%s' GROUP BY MONTH(t1.due_date) ORDER BY MONTH(t1.due_date)"%(lst[1],lst[0])))
    
    m =cint(sql("select month('%s')"%(get_defaults()['year_start_date']))[0][0])

    lst1 = [[1,'JAN'],[2 ,'FEB'], [3,'MAR'],[4,'APR'],[5,'MAY'],[6,'JUN'],[7,'JUL'],[8,'AUG'],[9,'SEP'],[10,'OCT'],[11,'NOV'],[12,'DEC']]
    lst2=[]
    k=1

    for i in range(1,13):
      for j in lst1:
        if j[0]==m:
          lst2.append([k,j[1]])
      m +=1
      if m==13: m=1
      k +=1
    return {'msg_data':ret,'x_axis':lst2}

  #===============================get weekly sales=================================================
  def get_weekwise_amount(self,lst):
   
    lst = lst.split(',')
    
    cases = self.get_week_cases(lst[0],lst[1])
          
    if not lst[2]:
      query = "SELECT SUM(grand_total) AMOUNT,CASE WEEK(due_date)"+ cases +"END Weekly FROM `tabSales Invoice` WHERE MONTH(due_date) = %d AND docstatus = 1 AND fiscal_year = '%s' GROUP BY Weekly  ORDER BY Weekly"
      
      ret = webnotes.conn.convert_to_lists(sql(query%(cint(lst[0]),lst[1])))
    
    else:
          
      query = "SELECT SUM(t2.amount) AMOUNT,CASE WEEK(t1.due_date)" + cases + "END Weekly FROM `tabSales Invoice` t1, `tabSales Invoice Item` t2 WHERE MONTH(t1.due_date) = %d AND t1.docstatus = 1 AND t1.fiscal_year = '%s' AND t1.name = t2.parent AND t2.item_group ='%s' GROUP BY Weekly  ORDER BY Weekly"
      
      ret =webnotes.conn.convert_to_lists(sql(query%(cint(lst[0]),lst[1],lst[2])))
 
    return ret and ret or ''
  #================================================================================
  def get_week_cases(self,m1,fy):
    d1 = self.make_date("%s,%s"%(cstr(m1),fy))
     
    w = sql("select week('%s'),week(last_day('%s'))"%(d1,d1))
    w1 = cint(w[0][0]) 
    w2 = cint(w[0][1])
   
    w3 = []
    str1 = " "
    for i in range(1,7):
      if(w1 <= w2):
        w3.append(w1)
        str1 += "WHEN "+ cstr(w1) +" THEN 'Week"+cstr(i) +"' "
        w1 += 1
    
    return str1
      
  #===============================get yearly weekwise sales=================================================
  def get_year_weekwise_amount(self,lst):
    
    lst = lst.split(',')
    yr_st = get_defaults()['year_start_date']
    
    fy = lst[0]
    m1 = cint(yr_st.split('-')[1])

    cases = ' '
    for i in range(1,13):
      cases += self.get_week_cases(m1,fy)
      m1 +=1
      if(m1 == 13): m1 = 1 
    
    if not lst[1]:
      query = "SELECT SUM(grand_total) AMOUNT,CASE WEEK(due_date)"+cases+"END Weekly, month(due_date) month FROM `tabSales Invoice` WHERE docstatus = 1 AND fiscal_year = '%s' GROUP BY `month`,weekly ORDER BY `month`,weekly"
      ret = webnotes.conn.convert_to_lists(sql(query%lst[0]))
    
    else:
    
      query = "SELECT SUM(t2.amount) AMOUNT,CASE WEEK(t1.due_date)" + cases + "END Weekly, month(due_date) month FROM `tabSales Invoice` t1, `tabSales Invoice Item` t2 WHERE t1.docstatus = 1 AND t1.fiscal_year = '%s' AND t1.name = t2.parent AND t2.item_group ='%s' GROUP BY Weekly  ORDER BY Weekly"
      ret = webnotes.conn.convert_to_lists(sql(query%(lst[0],lst[1])))
      
    
    return ret and ret or ''
  

  #====================================make yearly weekwise dates================================================
  def yr_wk_dates(self,fy):
    
    from datetime import date
    yr_st = get_defaults()['year_start_date']
    yr_en = get_defaults()['year_end_date']
    
    fy = fy.split('-')
    y1 = yr_st.split('-')
    date1 = date(cint(fy[0]),cint(y1[1]),cint(y1[2]))
    
    y2 = yr_en.split('-')
    date2 = date(cint(fy[1]),cint(y2[1]),cint(y2[2]))
    
    

    date_lst = [[1,self.get_months(cint(y1[1]))]]
    m1=cint(y1[1])+1
    x_axis_lst = [[1,'Week1',cint(y1[1])]]
    
    from datetime import date, timedelta
    d =dt= date1

    week=k=1
    for i in range(0,53): 

      if dt <= date2:
        
        if(d.weekday()>3):
          d = d+timedelta(7-d.weekday())
        else:
          d = d - timedelta(d.weekday())
        dlt = timedelta(days = (week-1)*7)
        dt = d + dlt + timedelta(days=6)
        
        m2 = cint(sql("Select month('%s')"%dt)[0][0])
        
        if(m1 == m2):
          date_lst.append([i+2,self.get_months(m2)])
          x_axis_lst.append([i+2,'Week1',m2])
          k=1
          m1 += 1 
          if(m1==13): m1 =1
        else:
          date_lst.append([i+2,' '])
          x_axis_lst.append([i+2,'Week%d'%k,m2])
        week += 1
        k +=1
        
               
    return [date_lst,x_axis_lst]
  #===================================================================================

  def get_months(self,m):
    m_lst = {1:'JAN',2:'FEB',3:'MAR',4:'APR',5:'MAY',6:'JUN',7:'JUL',8:'AUG',9:'SEP',10:'OCT',11:'NOV',12:'DEC'}
    return m_lst[m]

  
    
  def get_weekdates(self,lst):
    from datetime import date, timedelta
  
    d = dt = self.make_date(lst)
    date_lst = [[1,cstr(d.strftime("%d/%m/%y"))]]
    week=flag =1
    j=1
    last_day = sql("select last_day('%s')"%d)[0][0]
    lst_m = cint(lst.split(',')[0])
    for i in range(2,8):
      f=0
      if(dt < last_day):
        #if(d.weekday()>4):
        #d = d+timedelta(7-d.weekday()) 
        #else:
        d = d - timedelta(d.weekday()-1)
        dlt = timedelta(days = (week-1)*7)
        dt = d + dlt + timedelta(days=6)
        
        if(cint(sql("select month('%s')"%dt)[0][0]) == lst_m and dt!=last_day):
          for k in date_lst:      
            if(cstr(dt.strftime("%d/%m/%y")) == k[1]):
              f = 1
          if f == 0:   
            date_lst.append([i,cstr(dt.strftime("%d/%m/%y"))])
          
        elif(dt==last_day and flag ==1):
          date_lst.append([i,cstr(last_day.strftime("%d/%m/%y"))])
          flag = 0
      
        elif(flag == 1):
          date_lst.append([i,cstr(last_day.strftime("%d/%m/%y"))])
        week += 1
       
    return date_lst and date_lst or ''
        
          
  def make_date(self,lst):
    
    from datetime import date, timedelta
    lst = lst.split(',')
    year = lst[1].split('-')
    if(len(lst[0])==1):  month = '0'+lst[0]
    else: month = lst[0]
    if(1<=cint(month)<=3): year = year[1]    
    elif(4<=cint(month)<=12): year = year[0]
    
    d = date(cint(year),cint(month),1)
    
    return d 
    
  def get_item_groups(self):
    ret = webnotes.conn.convert_to_lists(sql("select name from `tabItem Group` where docstatus != 2 and is_group = 'No'"))
    #ret = webnotes.conn.convert_to_lists(sql("select item_group from `tabItem` where is_sales_item='Yes' and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >  now()) and item_group !=''"))
    return ret and ret or ''
    
  def get_fiscal_year(self):
    ret = webnotes.conn.convert_to_lists(sql("select name from `tabFiscal Year` where docstatus =0"))
    return ret and ret or ''