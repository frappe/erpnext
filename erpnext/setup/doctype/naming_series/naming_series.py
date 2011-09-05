# Please edit this list and import only required elements
import webnotes

from webnotes.utils import cint, cstr
from webnotes import msgprint, errprint

sql = webnotes.conn.sql
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	#-----------------------------------------------------------------------------------------------------------------------------------
	def get_transactions(self):
		return "\n".join([''] + [i[0] for i in sql("SELECT `tabDocField`.`parent` FROM `tabDocField`, `tabDocType` WHERE `tabDocField`.`fieldname` = 'naming_series' and `tabDocType`.module !='Recycle Bin' and `tabDocType`.name=`tabDocField`.parent order by `tabDocField`.parent")])
	
	#-----------------------------------------------------------------------------------------------------------------------------------
	def get_options_for(self, doctype):
		sr = sql("select options from `tabDocField` where parent='%s' and fieldname='naming_series'" % (doctype))
		if sr and sr[0][0]:
			return sr[0][0].split("\n")
		else:
			return []
	
	def scrub_options_list(self, ol):
		options = filter(lambda x: x, [cstr(n.upper()).strip() for n in ol])
		return options
	
	#-----------------------------------------------------------------------------------------------------------------------------------
	def set_series_for(self, doctype, ol):
		options = self.scrub_options_list(ol)
		
		# validate names
		[self.validate_series_name(i) for i in options]
		
		if self.doc.user_must_always_select:
			options = [''] + options
			default = ''
		else:
			default = options[0]
		
		# update
		sql("update tabDocField set `options`=%s, `default`=%s where parent=%s and fieldname='naming_series'", ("\n".join(options), default, doctype))
		self.doc.set_options = "\n".join(options)
	
	#-----------------------------------------------------------------------------------------------------------------------------------
	def update_series(self):
			self.check_duplicate()
			self.set_series_for(self.doc.select_doc_for_series, self.doc.set_options.split("\n"))
			msgprint('Series Updated')			
			
	#-----------------------------------------------------------------------------------------------------------------------------------
	def check_duplicate(self):
		from core.doctype.doctype.doctype import DocType
		dt = DocType()
	
		sr = sql("select options, parent from `tabDocField` where fieldname='naming_series' and parent != %s", self.doc.select_doc_for_series)
		options = self.scrub_options_list(self.doc.set_options.split("\n"))
		for series in options:
			dt.validate_series(series, self.doc.select_doc_for_series)
			for i in sr:
				if i[0]:
					if series in i[0].split("\n"):
						msgprint("Oops! Series name %s is already in use in %s. Please select a new one" % (series, i[1]), raise_exception=1)
			
	#-----------------------------------------------------------------------------------------------------------------------------------
	def validate_series_name(self, n):
		import re
		if not re.match('[a-zA-Z0-9]+(([-/][a-zA-Z0-9])?[-/][a-zA-Z0-9]*)*',n):
			msgprint('Special Characters except "-" and "/" not allowed in naming series')
			raise Exception
		
	#-----------------------------------------------------------------------------------------------------------------------------------
	def get_options(self, arg=''):
		so = sql("select options from `tabDocField` where parent=%s and fieldname='naming_series'", self.doc.select_doc_for_series)
		if so:
			return so[0][0] or ''


	#-----------------------------------------------------------------------------------------------------------------------------------
	def update_series_start(self):
		ser_det = sql("select name from `tabSeries` where name = %s", self.doc.prefix)
		if ser_det:
			sql("update `tabSeries` set current = '%s' where name = '%s'" % (self.doc.starts_from-1,self.doc.prefix))
		else:
			sql("insert into tabSeries (name, current) values (%s,%s)",(cstr(self.doc.prefix),cint(self.doc.starts_from)-1))
		msgprint("Series Updated Successfully")
