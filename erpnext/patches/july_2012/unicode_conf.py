from __future__ import unicode_literals

def execute():
	"""appends from __future__ import unicode_literals to py files if necessary"""
	import wnf
	wnf.append_future_import()