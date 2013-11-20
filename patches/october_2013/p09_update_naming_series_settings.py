# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	# reset property setters for series
	for name in ("Stock Settings", "Selling Settings", "Buying Settings", "HR Settings"):
		webnotes.bean(name, name).save()