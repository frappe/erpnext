from __future__ import unicode_literals
from webnotes.model import delete_doc

def execute():
	# remove search criteria
	delete_doc("Search Criteria", "trial_balance")
