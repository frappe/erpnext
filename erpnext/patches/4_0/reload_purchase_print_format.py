# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc('buying', 'Print Format', 'Purchase Order Classic')
	webnotes.reload_doc('buying', 'Print Format', 'Purchase Order Modern')
	webnotes.reload_doc('buying', 'Print Format', 'Purchase Order Spartan')