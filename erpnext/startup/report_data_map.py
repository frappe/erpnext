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

data_map = {
	"Account": {
		"columns": ["name", "parent_account", "lft", "rgt", "debit_or_credit", "is_pl_account",
			"company"],
		"order_by": "lft"
	},
	"GL Entry": {
		"columns": ["account", "posting_date", "cost_center", "debit", "credit", "is_opening",
			"company"],
		"conditions": ["ifnull(is_cancelled, 'No')='No'"],
		"order_by": "posting_date"
	},
	"Company": {
		"columns": ["name"],
		"conditions": ["docstatus < 2"]
	},
	"Fiscal Year": {
		"columns": ["name", "year_start_date", 
			"adddate(year_start_date, interval 1 year) as year_end_date"]
	}
}
