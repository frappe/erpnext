from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import flt, comma_and,cstr,cint,add_days
import webnotes.defaults
from webnotes import msgprint
from webnotes.model.doc import Document, addchild
import datetime
from datetime import date,timedelta
import dateutil
import calendar
from webnotes.utils import nowdate

sql = webnotes.conn.sql

@webnotes.whitelist()
def upload():
        from webnotes.utils.datautils import read_csv_content_from_uploaded_file
        rows = read_csv_content_from_uploaded_file()
	fi = webnotes.form_dict.select_doctype
	msgprint(fi)

@webnotes.whitelist()
def upload1():
	fieldname = webnotes.form_dict.get('fieldname')
	#msgprint(fieldname)

