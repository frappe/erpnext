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

if not filter_values['account']:
  msgprint("Please Enter filter value for Account")
  raise Exception

colwidths[col_idx['Fiscal Month']] = '120px'
colwidths[col_idx['Debit']] = '120px'
colwidths[col_idx['Credit']] = '120px'


month_lst={'1':'Jan','2':'Feb','3':'Mar','4':'Apr','5':'May','6':'Jun','7':'Jul','8':'Aug','9':'Sept','10':'Oct','11':'Nov','12':'Dec'}
for r in res:
  mnt = '%s'%r[col_idx['Fiscal Month']]
  r[col_idx['Fiscal Month']]=month_lst[mnt]