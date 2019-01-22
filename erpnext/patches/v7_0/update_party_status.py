from __future__ import unicode_literals
import frappe

def execute():
	return
	# for party_type in ('Customer', 'Supplier'):
	# 	frappe.reload_doctype(party_type)
	#
	# 	# set all as default status
	# 	frappe.db.sql('update `tab{0}` set status=%s'.format(party_type), default_status[party_type])
	#
	# 	for doctype in status_depends_on[party_type]:
	# 		filters = get_filters_for(doctype)
	# 		parties = frappe.get_all(doctype, fields="{0} as party".format(party_type.lower()),
	# 			filters=filters, limit_page_length=1)
	#
	# 		parties = filter(None, [p.party for p in parties])
	#
	# 		if parties:
	# 			frappe.db.sql('update `tab{0}` set status="Open" where name in ({1})'.format(party_type,
	# 				', '.join(len(parties) * ['%s'])), parties)