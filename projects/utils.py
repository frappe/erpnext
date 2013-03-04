# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

@webnotes.whitelist()
def get_time_log_list(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.get_values("Time Log", filters, ["name", "activity_type", "owner"], debug=True)