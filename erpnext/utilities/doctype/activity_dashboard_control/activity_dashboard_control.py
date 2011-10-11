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
    
    
    # get dashboard counts
    # --------------------
    def get_dashboard_counts(self, dt):
        dtl = eval(dt)
        dt = {}
        
        for d in dtl:
            # if Lead
            if d=='Lead':
                dt[d] = {'To follow up':sql("select count(name) from tabLead where status!='Converted' and docstatus=1")[0][0] or 0}
                
            # if Enquiry
            elif d=='Enquiries':
                args = {}
                args['Quotations to be sent'] = sql("select count(distinct(t2.name)) from `tabQuotation`t1, `tabEnquiry`t2 where t1.enq_no!=t2.name and t2.docstatus=1")[0][0] or 0
                args['To follow up'] = sql("select count(name) from `tabQuotation` where docstatus=0")[0][0] or 0       #Draft
                dt[d] = args
                
            # if Sales Order
            elif d=='Sales Order':
                args = {}
                args['To be delivered'] = sql("select count(name) from `tabSales Order` where per_delivered<100 and delivery_date>now() and docstatus=1")[0][0] or 0
                args['To be billed'] = sql("select count(name) from `tabSales Order` where per_billed<100 and docstatus=1")[0][0] or 0  
                args['Overdue'] = sql("select count(name) from `tabSales Order` where per_delivered<100 and delivery_date<now() and docstatus=1")[0][0] or 0
                args['To be submitted'] = sql("select count(name) from `tabSales Order` where status='Draft'")[0][0] or 0       #Draft
                dt[d] = args
            
            # if Invoice
            elif d=='Invoices':
                args = {}
                args['To receive payment'] = sql("select count(name) from `tabReceivable Voucher` where docstatus=1 and due_date>now() and outstanding_amount!=0")[0][0] or 0
                args['Overdue'] = sql("select count(name) from `tabReceivable Voucher` where docstatus=1 and due_date<now() and outstanding_amount!=0")[0][0] or 0  
                args['To be submitted'] = sql("select count(name) from `tabReceivable Voucher` where docstatus=0")[0][0] or 0       #Draft
                dt[d] = args
            
            # if Indent 
            elif d=='Indent':
                args = {}
                args['Purchase Order to be made'] = sql("select count(name) from `tabIndent` where per_ordered<100 and docstatus=1")[0][0] or 0
                args['To be submitted'] = sql("select count(name) from `tabIndent` where status='Draft'")[0][0] or 0       #Draft
                dt[d] = args
                
            # if Purchase Order    
            elif d=='Purchase Order':
                args = {}
                args['To receive items'] = sql("select count(name) from `tabPurchase Order` where per_received<100 and docstatus=1")[0][0] or 0
                args['To be billed'] = sql("select count(name) from `tabPurchase Order` where per_billed<100 and docstatus=1")[0][0] or 0
                args['To be submitted'] = sql("select count(name) from `tabPurchase Order` where status='Draft'")[0][0] or 0        #Draft
                dt[d] = args
            
            # if Bills
            elif d=='Bills':
                args = {}
                args['To be payed'] = sql("select count(name) from `tabPayable Voucher` where docstatus=1 and outstanding_amount!=0")[0][0] or 0
                args['To be submitted'] = sql("select count(name) from `tabPayable Voucher` where docstatus=0")[0][0] or 0       #Draft
                dt[d] = args
                
            # if Tasks
            elif d=='Tasks':
                dt[d] = {'Open': sql("select count(name) from `tabTicket` where status='Open'")[0][0] or 0}
                
            # if Maintenance
            elif d=='Serial No':
              args = {}
              args['AMC to expire this month'] = sql("select count(name) from `tabSerial No` where docstatus=1 and month(getdate()) = month(amc_expiry_date) and year(getdate()) = year(amc_expiry_date)")[0][0] or 0
              args['Warranty to expire this month'] = ql("select count(name) from `tabSerial No` where docstatus=1 and month(getdate()) = month(warranty_expiry_date) and year(getdate())=year(warranty_expiry_date)")[0][0] or 0
              dt[d] = args
              
        msgprint(dt)
        return dt