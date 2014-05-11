# -*- coding: utf-8 -*-

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

# default settings that can be made for a profile.
from __future__ import unicode_literals

import webnotes

product_name = "ERPNext"
profile_defaults = {
	"Company": "company",
	"Territory": "territory"
}

# add startup propertes
mail_footer = """<div style="padding: 7px; text-align: right; color: #888"><small>Sent via 
	<a style="color: #888" href="http://erpnext.org">ERPNext</a></div>"""
	
def get_monthly_bulk_mail_limit():
	import webnotes
	# if global settings, then 500 or unlimited
	if webnotes.conn.get_value('Email Settings', None, 'outgoing_mail_server'):
		return 999999
	else:
		return 500
