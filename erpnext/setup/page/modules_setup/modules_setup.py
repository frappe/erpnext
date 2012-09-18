from __future__ import unicode_literals
import webnotes

@webnotes.whitelist()
def update(arg=None):
	"""update modules"""
	webnotes.conn.set_global('modules_list', webnotes.form_dict['ml'])
	webnotes.msgprint('Updated')
	webnotes.clear_cache()