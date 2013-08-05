# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.code import get_obj
	gd = get_obj('Global Defaults')
	gd.doc.maintain_same_rate = 1
	gd.doc.save()
	gd.on_update()
	