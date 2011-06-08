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
    def __init__(self,d,dl):
        self.doc, self.doclist = d, dl
        
    def show_my_rating(self,arg):
        arg = eval(arg)
        ret = {}
        ret['total_stars'] = convert_to_lists(sql("select total_stars from `tabRating Template` where name = %s", arg['template']))
        ret['avg_rating'] = convert_to_lists(sql("select count(name),round(sum(rating_stars)/count(name)) from `tabRating Widget Record` where rating_doctype = %s and rating_docname = %s and rating_template = %s",(arg['dt'], arg['dn'], arg['template'])))
        rating_details = convert_to_lists(sql("select name, rating_stars, rating_description, rating_template, rating_by, rating_to, rating_date, rating_time, rating_doctype, rating_docname from `tabRating Widget Record` where rating_by = %s and rating_doctype = %s and rating_docname = %s and rating_template = %s",(arg['by'], arg['dt'], arg['dn'], arg['template'])))
        if rating_details:
            ret['rating_details'] = rating_details or ''
            ret['flag'] = 1
        else:
            ret['rating_desc'] = convert_to_lists(sql("select rating, description from `tabRating Template Detail` where parent = %s", arg['template']))
            ret['flag'] = 0
        return ret
        
    def add_rating(self,arg):
        import time
        arg = eval(arg)
        rw = Document('Rating Widget Record')
        rw.rating_stars = arg['rating']
        rw.rating_description = arg['desc']
        rw.rating_template = arg['template']
        rw.rating_by = arg['rating_by']
        rw.rating_to = Document(arg['dt'],arg['dn']).owner
        rw.rating_date = nowdate()
        rw.rating_time = time.strftime('%H:%M')
        rw.rating_doctype = arg['dt']
        rw.rating_docname = arg['dn']
        rw.save(1)