# Please edit this list and import only required elements
import webnotes
from webnotes.utils import add_days, cint, cstr, date_diff, default_fields, flt, getdate, now, nowdate
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj
from webnotes import  msgprint, errprint

sql = webnotes.conn.sql	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series + '.#####')

	def on_update(self):
		inv = "'" + "', '".join([d.invoice_no for d in getlist(self.doclist, 'invoice_details')]) + "'"
		sql("""update `tabReceivable Voucher` set c_form_no = '%s', modified ='%s'
				where name in (%s)"""%(self.doc.name, self.doc.modified, inv))

	def get_invoice_details(self, invoice_no):
		inv = sql("""select posting_date, territory, net_total, grand_total from
			`tabReceivable Voucher` where name = %s""", invoice_no)	
		ret = {
			'invoice_date' : inv and getdate(inv[0][0]).strftime('%Y-%m-%d') or '',
			'territory'    : inv and inv[0][1] or '',
			'net_total'    : inv and flt(inv[0][2]) or '',
			'grand_total'  : inv and flt(inv[0][3]) or ''
		}
		return ret
