from __future__ import unicode_literals

import frappe

def get_context(context):
	# do your magic here
	if context.doc:
		context.read_only = 1