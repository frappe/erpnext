# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

def execute():
	"""appends from __future__ import unicode_literals to py files if necessary"""
	import wnf
	wnf.append_future_import()