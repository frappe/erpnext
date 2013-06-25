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
import webnotes
from webnotes import _, msgprint
from webnotes.utils import cint, comma_or

def validate_status(status, options):
	if status not in options:
		msgprint(_("Status must be one of ") + comma_or(options), raise_exception=True)

def build_filter_conditions(filters):
	conditions, filter_values = [], []
	for key in filters:
		conditions.append('`' + key + '` = %s')
		filter_values.append(filters[key])

	conditions = conditions and " and " + " and ".join(conditions) or ""
	return conditions, filter_values