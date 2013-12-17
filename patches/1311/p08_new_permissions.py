# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	# reset Page perms
	from core.page.permission_manager.permission_manager import reset
	reset("Page")
	
	# patch to move print, email into DocPerm
	