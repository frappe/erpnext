# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
def execute():
	"""
		remove control panel email settings if automail.webnotestech.com
	"""
	from webnotes.model.doc import Document
	cp = Document('Control Panel', 'Control Panel')
	if cp:
		if cp.outgoing_mail_server == 'mail.webnotestech.com':
			cp.outgoing_mail_server = None;
			cp.mail_login = None;
			cp.mail_password = None;
			cp.mail_port = None;
			cp.auto_email_id = 'automail@erpnext.com'
			cp.save()

