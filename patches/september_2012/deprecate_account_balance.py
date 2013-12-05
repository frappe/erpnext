# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.model import delete_doc

def execute():
	# remove doctypes
	for dt in ["Period", "Account Balance", "Multi Ledger Report", 
			"Multi Ledger Report Detail", "Period Control", "Reposting Tool", 
			"Lease Agreement", "Lease Installment"]:
		delete_doc("DocType", dt)