# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist
from webnotes.model.code import get_obj

sql = webnotes.conn.sql
	


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	# Get Tax Rate if account type is Tax
	# ===================================================================
	def get_rate(self, arg):
		return get_obj('Purchase Common').get_rate(arg, self)