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

from webnotes.utils import add_days, add_months, cint, cstr
from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist

sql = webnotes.conn.sql
	

class DocType:
        def __init__(self, d, dl):
                self.doc, self.doclist = d, dl


        # Define Globals
        # ---------------
        def define_globals(self, trans, fiscal_year):
                self.month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

                if trans == 'Purchase Receipt' or trans == 'Delivery Note' or trans == 'Purchase Invoice' or trans == 'Sales Invoice':
                        self.trans_date = 'posting_date'
                else:
                        self.trans_date = 'transaction_date'
                
                ysd = sql("select year_start_date from `tabFiscal Year` where name = %s",fiscal_year)[0][0]
                self.year_start_date = ysd.strftime('%Y-%m-%d')
                self.start_month = cint(self.year_start_date.split('-')[1])


        # Get Column Names and Query for Annual Trend
        # ---------------------------------------------
        def get_annual_trend_details(self, fiscal_year):
                col_names = [fiscal_year+' (Qty)', fiscal_year+' (Amt)']
                query_val = 'SUM(t2.qty) ,SUM(t2.amount),'
                return col_names, query_val


        # Get Column Names and Query for Half Yearly Trend
        # --------------------------------------------------
        def get_half_yearly_trend_details(self):
                first_half_start = self.year_start_date
                first_half_end = add_days(add_months(first_half_start,6),-1)
                second_half_start = add_days(first_half_end,1)
                second_half_end = add_days(add_months(second_half_start,6),-1)
                
                col_names = ['First Half (Qty)', 'First Half (Amt)', 'Second Half (Qty)', 'Second Half (Amt)']
               
                query_val = 'SUM(CASE WHEN t1.'+self.trans_date+' BETWEEN "'+first_half_start+'" AND "'+first_half_end+'" THEN t2.qty ELSE NULL END), SUM(CASE WHEN t1.'+self.trans_date+' BETWEEN "'+first_half_start+'" AND "'+first_half_end+'" THEN t2.amount ELSE NULL END), SUM(CASE WHEN t1.'+self.trans_date+' BETWEEN "'+second_half_start+'" AND "'+second_half_end+'" THEN t2.qty ELSE NULL END), SUM(CASE WHEN t1.'+self.trans_date+' BETWEEN "'+second_half_start+'" AND "'+second_half_end+'" THEN t2.amount ELSE NULL END),'

                return col_names, query_val


        # Get Column Names and Query for Quarterly Trend
        # ------------------------------------------------
        def get_quarterly_trend_details(self):
                first_qsd, second_qsd, third_qsd, fourth_qsd = self.year_start_date, add_months(self.year_start_date,3), add_months(self.year_start_date,6), add_months(self.year_start_date,9)

                first_qed, second_qed, third_qed, fourth_qed = add_days(add_months(first_qsd,3),-1), add_days(add_months(second_qsd,3),-1), add_days(add_months(third_qsd,3),-1), add_days(add_months(fourth_qsd,3),-1)

                col_names = ['Q1 (Qty)','Q1 (Amt)','Q2 (Qty)','Q2 (Amt)','Q3 (Qty)','Q3 (Amt)','Q4 (Qty)','Q4 (Amt)']
                query_val = ''
                bet_dates = [[first_qsd,first_qed],[second_qsd,second_qed],[third_qsd,third_qed],[fourth_qsd,fourth_qed]]

                for d in bet_dates:
                        query_val += 'SUM(CASE WHEN t1.'+self.trans_date+' BETWEEN "'+d[0]+'" AND "'+d[1]+'" THEN t2.qty ELSE NULL END), SUM(CASE WHEN t1.'+self.trans_date+' BETWEEN "'+d[0]+'" AND "'+d[1]+'" THEN t2.amount ELSE NULL END),'
                
                return col_names, query_val


        # Get Column Names and Query for Monthly Trend
        # -----------------------------------------------
        def get_monthly_trend_details(self):
                col_names, query_val = [], ''
                for i in range(self.start_month-1, len(self.month_name)):
                        col_names.append(self.month_name[i]+' (Qty)')
                        col_names.append(self.month_name[i]+' (Amt)')
                        query_val += 'SUM(CASE WHEN MONTH(t1.'+self.trans_date+') = '+cstr(i+1)+' THEN t2.qty ELSE NULL END), SUM(CASE WHEN MONTH(t1.'+self.trans_date+') = '+cstr(i+1)+' THEN t2.amount ELSE NULL END),'

                for i in range(0, self.start_month-1):
                        col_names.append(self.month_name[i]+' (Qty)')
                        col_names.append(self.month_name[i]+' (Amt)')
                        query_val += 'SUM(CASE WHEN MONTH(t1.'+self.trans_date+') = '+cstr(i+1)+' THEN t2.qty ELSE NULL END), SUM(CASE WHEN MONTH(t1.'+self.trans_date+') = '+cstr(i+1)+' THEN t2.amount ELSE NULL END),'
                
                return col_names, query_val


        # Get Single Year Trend's Query and Columns
        # -------------------------------------------
        def get_single_year_query_value(self, fiscal_year, period, trans, trans_det):
                self.define_globals(trans, fiscal_year)
                if period == 'Annual':
                        return self.get_annual_trend_details(fiscal_year)
                elif period == 'Half Yearly':
                        return self.get_half_yearly_trend_details()
                elif period == 'Quarterly':
                        return self.get_quarterly_trend_details()
                elif period == 'Monthly':
                        return self.get_monthly_trend_details()
