# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("setup", "doctype", "features_setup")
	fs = webnotes.bean("Features Setup")
	fs.doc.fs_pos_view = 1
	fs.save()