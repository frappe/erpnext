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
		"""	Update C-Form No on invoices"""
		
		if len(getlist(self.doclist, 'invoice_details')):
			inv = "'" + "', '".join([d.invoice_no for d in getlist(self.doclist, 'invoice_details')]) + "'"
			sql("""update `tabReceivable Voucher` set c_form_no = '%s', modified ='%s'
				where name in (%s)"""%(self.doc.name, self.doc.modified, inv))
			sql("""update `tabReceivable Voucher` set c_form_no = '', modified = %s where name not
				in (%s) and ifnull(c_form_no, '') = %s""", (self.doc.modified, self.doc.name, inv))
		else:
			msgprint("Please enter atleast 1 invoice in the table below", raise_exception=1)


	def get_invoice_details(self, invoice_no):
		"""	Pull details from invoices for referrence """

		inv = sql("""select posting_date, territory, net_total, grand_total from
			`tabReceivable Voucher` where name = %s""", invoice_no)	
		ret = {
			'invoice_date' : inv and getdate(inv[0][0]).strftime('%Y-%m-%d') or '',
			'territory'    : inv and inv[0][1] or '',
			'net_total'    : inv and flt(inv[0][2]) or '',
			'grand_total'  : inv and flt(inv[0][3]) or ''
		}
		return ret


	def validate_invoice(self):
		"""Validate invoice that c-form is applicable and no other c-form is
		received for that"""

		for d in getlist(self.doclist, 'invoice_details'):
			inv = sql("""select c_form_applicable, c_form_no from
				`tabReceivable Voucher` where name = %s""", invoice_no)
			if not inv:
				msgprint("Invoice: %s is not exists in the system, please check." % d.invoice_no, raise_exception=1)
			elif inv[0][0] != 'Yes':
				msgprint("C-form is not applicable for Invoice: %s" % d.invoice_no, raise_exception=1)
			elif inv[0][1] and inv[0][1] != self.doc.name:
				msgprint("""Invoice %s is tagged in another C-form: %s. \nIf you want to change C-form no for this invoice,
					please remove invoice no from the previous c-form and then try again""" % (d.invoice_no, inv[0][1]), raise_exception=1)
