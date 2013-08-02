# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	"""
		deprecate:
		* doctype - import data control
		* page - import data (old)
	"""
	import webnotes
	from webnotes.model import delete_doc
	delete_doc('DocType', 'Import Data Control')
	delete_doc('Page', 'Import Data')