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

from __future__ import unicode_literals
import webnotes
from webnotes.modules import reload_doc
	
def execute():
	"""
		* Reload Sales Taxes and Charges
		* Reload Support Ticket
		* Run Install Print Format Patch
		* Reload Customize Form
	"""
	reload_doc('accounts', 'doctype', 'rv_tax_detail')
	reload_doc('support', 'doctype', 'support_ticket')
	reload_print_formats()
	reload_doc('core', 'doctype', 'doclayer')

def reload_print_formats():
	"""
		Reloads the following print formats:
		* Sales Invoice Classic/Modern/Spartan
		* Sales Order Classic/Modern/Spartan
		* Delivery Note Classic/Modern/Spartan
		* Quotation Classic/Modern/Spartan
	"""
	reload_doc('accounts', 'Print Format', 'Sales Invoice Classic')
	reload_doc('accounts', 'Print Format', 'Sales Invoice Modern')
	reload_doc('accounts', 'Print Format', 'Sales Invoice Spartan')

	reload_doc('selling', 'Print Format', 'Sales Order Classic')
	reload_doc('selling', 'Print Format', 'Sales Order Modern')
	reload_doc('selling', 'Print Format', 'Sales Order Spartan')

	reload_doc('selling', 'Print Format', 'Quotation Classic')
	reload_doc('selling', 'Print Format', 'Quotation Modern')
	reload_doc('selling', 'Print Format', 'Quotation Spartan')

	reload_doc('stock', 'Print Format', 'Delivery Note Classic')
	reload_doc('stock', 'Print Format', 'Delivery Note Modern')
	reload_doc('stock', 'Print Format', 'Delivery Note Spartan')
