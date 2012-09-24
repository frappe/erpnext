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

def execute():
	"""
		* Reload Search Criteria "Customer Address Contact"
		* SET is_primary_contact=1, is_primary_address=1 WHERE not specified
	"""
	reload_sc()
	patch_primary_contact()
	patch_primary_address()

def reload_sc():
	from webnotes.modules import reload_doc
	reload_doc('selling', 'search_criteria', 'customer_address_contact')
	reload_doc('selling', 'Module Def', 'Selling')

def patch_primary_contact():
	res = webnotes.conn.sql("""
		SELECT name FROM `tabContact`
		WHERE customer IN (
			SELECT customer FROM `tabContact`
			WHERE IFNULL(customer, '')!=''
			GROUP BY customer HAVING SUM(IFNULL(is_primary_contact, 0))=0
		) OR supplier IN (
			SELECT supplier FROM `tabContact`
			WHERE IFNULL(supplier, '')!=''
			GROUP BY supplier HAVING SUM(IFNULL(is_primary_contact, 0))=0
		) OR sales_partner IN (
			SELECT sales_partner FROM `tabContact`
			WHERE IFNULL(sales_partner, '')!=''
			GROUP BY sales_partner HAVING SUM(IFNULL(is_primary_contact, 0))=0
		)
	""", as_list=1)
	names = ", ".join(['"' + unicode(r[0]) + '"' for r in res if r])
	if names: webnotes.conn.sql("UPDATE `tabContact` SET is_primary_contact=1 WHERE name IN (%s)" % names)

def patch_primary_address():
	res = webnotes.conn.sql("""
		SELECT name FROM `tabAddress`
		WHERE customer IN (
			SELECT customer FROM `tabAddress`
			WHERE IFNULL(customer, '')!=''
			GROUP BY customer HAVING SUM(IFNULL(is_primary_address, 0))=0
			AND SUM(IFNULL(is_shipping_address, 0))=0
		) OR supplier IN (
			SELECT supplier FROM `tabAddress`
			WHERE IFNULL(supplier, '')!=''
			GROUP BY supplier HAVING SUM(IFNULL(is_primary_address, 0))=0
			AND SUM(IFNULL(is_shipping_address, 0))=0
		) OR sales_partner IN (
			SELECT sales_partner FROM `tabAddress`
			WHERE IFNULL(sales_partner, '')!=''
			GROUP BY sales_partner HAVING SUM(IFNULL(is_primary_address, 0))=0
			AND SUM(IFNULL(is_shipping_address, 0))=0
		)
	""", as_list=1)
	names = ", ".join(['"' + unicode(r[0]) + '"' for r in res if r])
	if names: webnotes.conn.sql("UPDATE `tabAddress` SET is_primary_address=1 WHERE name IN (%s)" % names)
