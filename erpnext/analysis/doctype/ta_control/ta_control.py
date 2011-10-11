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


        # Define Globals
        # ---------------
        def define_globals(self, trans, fiscal_year):
                self.month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

                if trans == 'Purchase Receipt' or trans == 'Delivery Note' or trans == 'Payable Voucher' or trans == 'Receivable Voucher':
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
