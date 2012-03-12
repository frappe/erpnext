# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import webnotes
def execute():
	"""
		* Create DocType Label
		* Reload Related DocTypes
	"""
	create_doctype_label()
	reload_related_doctype()


def create_doctype_label():
	"""
		Creates a DocType Label Record for Indent
	"""
	res = webnotes.conn.sql("""\
		SELECT name FROM `tabDocType Label`
		WHERE name='Indent'
	""")
	if not(res and res[0] and res[0][0]):
		from webnotes.model.doc import Document
		doclabel = Document('DocType Label')
		doclabel.dt = 'Indent'
		doclabel.dt_label = 'Purchase Requisition'
		doclabel.save(1)


def reload_related_doctype():
	"""
		Reload:
		* indent
		* purchase_order
		* po_detail
	"""
	from webnotes.modules import reload_doc
	reload_doc('buying', 'doctype', 'indent')
	reload_doc('buying', 'doctype', 'purchase_order')
	reload_doc('buying', 'doctype', 'po_detail')
