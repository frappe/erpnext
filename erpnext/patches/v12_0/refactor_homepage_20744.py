# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, pymysql

def execute():
	# Structure before:
	# Homepage
	#  - Table products -> Homepage Featured Product
	#    - Link item_code -> Item
	# Homepage Section
	#  - Table section_cards -> Homepage Section Card

	# Structure after:
	# Homepage
	#  - Table page_sections -> Web Page Sections
	#    - Link section_name -> Web Page Section
	# Web Page Section
	#  - Table items -> Web Page Section Item
	#    - Select content_doctype -> [ Web Page Card, Blog Post, Item ]
	#    - Dynamic Link content_document -> content_doctype

	homepage = frappe.db.get_value('Homepage', 'Homepage', '*', as_dict=True)
	if homepage.hero_section_based_on == 'Homepage Section':
		frappe.db.set_value('Homepage', 'Homepage', 'hero_section_based_on', 'Web Page Section')

	try:
		homepage_products = frappe.db.get_all('Homepage Featured Product', fields='*', order_by='idx')
		frappe.db.delete('DocType', 'Homepage Featured Product')
	except pymysql.err.ProgrammingError:
		# Assume does not exist
		homepage_products = []

	frappe.reload_doc('Portal', 'doctype', 'Homepage')
	new_homepage = frappe.get_doc('Homepage')

	try:
		cards = frappe.db.get_all('Homepage Section Card', fields='*', order_by='parent,idx')
		frappe.rename_doc('DocType', 'Homepage Section Card', 'Web Page Card', force=True)
		frappe.reload_doc('Portal', 'doctype', 'Web Page Card')
		frappe.desk.doctype.bulk_update.bulk_update.update('Web Page Card', 'route_follow', 1)
	except pymysql.err.ProgrammingError:
		cards = []

	try:
		sections = frappe.db.get_all('Homepage Section', fields='*', order_by='section_order')
		frappe.rename_doc('DocType', 'Homepage Section', 'Web Page Section', force=True)
	except pymysql.err.ProgrammingError:
		sections = []

	frappe.reload_doc('Portal', 'doctype', 'Web Page Section')
	frappe.reload_doc('Portal', 'doctype', 'Web Page Section Item')
	frappe.reload_doc('Portal', 'doctype', 'Web Page Sections')

	for section in sections:
		new_section = frappe.get_doc('Web Page Section', section.name)
		if new_section.section_based_on == 'Cards':
			new_section.section_based_on = 'Grid'
		for card in cards:
			frappe.rename_doc('Web Page Card', card.name, card.title)
			if card.parent==section.name and card.parentfield=='section_cards' and card.parenttype=='Homepage Section':
				child = new_section.append('items', {})
				child.content_doctype = 'Web Page Card'
				child.content_document = card.title
				child.render_as = 'Vertical Card'
		new_section.save()
		child = new_homepage.append('page_sections', {})
		child.section_name = section.name
		new_homepage.save()

	if homepage_products:
		product_section = frappe.get_doc({
			'doctype': 'Web Page Section',
			'name': 'Products',
			'section_based_on': 'Grid',
			'no_of_columns': 3,
			'items': [ { 'content_doctype': 'Item',
				     'content_document': product.item_code,
				     'render_as': 'Vertical Card'
				} for product in homepage_products ]

		}).insert()
		child = new_homepage.append('page_sections', {})
		child.section_name = product_section.name
		new_homepage.save()

	frappe.db.sql_ddl("""DROP TABLE IF EXISTS `tabHomepage Featured Product`;""")
	frappe.db.sql_ddl("""ALTER TABLE `tabWeb Page Section` DROP IF EXISTS `section_order`;""")

	try:
		blogs = frappe.db.get_all('Blog Post',
			fields=['name'],
			filters={ 'published': 1 },
			order_by='published_on desc',
			limit=3
		)
		if blogs:
			blog_section = frappe.get_doc({
				'doctype': 'Web Page Section',
				'name': 'Publications',
				'section_based_on': 'Grid',
				'no_of_columns': 3,
				'items': [ { 'content_doctype': 'Blog Post',
					     'content_document': blog.name,
					     'render_as': 'Vertical Card'
					} for blog in blogs ]
			}).insert()
			child = new_homepage.append('page_sections', {})
			child.section_name = blog_section.name
			new_homepage.save()
	except frappe.DuplicateEntryError:
		pass
