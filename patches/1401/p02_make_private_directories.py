# Copyright (c) 2014, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import os
import errno
from webnotes.utils import get_site_path

def execute():
	private_path = get_site_path(webnotes.local.conf.get('private_path', 'private'))
	backup_path = get_site_path(webnotes.local.conf.get('backup_path', 'private/backup'))
	try:
		os.makedirs(private_path)
	except OSError, e:
		if not e.errno == errno.EEXIST:
			raise
	try:
		os.makedirs(backup_path)
	except OSError, e:
		if not e.errno == errno.EEXIST:
			raise
