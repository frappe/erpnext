# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def set_as_default(self):
		webnotes.conn.set_value("Global Defaults", None, "current_fiscal_year", self.doc.name)
		webnotes.get_obj("Global Defaults").on_update()
		
		# clear cache
		webnotes.clear_cache()
		
		msgprint(self.doc.name + _(""" is now the default Fiscal Year. \
			Please refresh your browser for the change to take effect."""))