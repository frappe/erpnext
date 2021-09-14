from __future__ import unicode_literals

from collections import defaultdict

import frappe


def execute():

	frappe.reload_doc('stock', 'doctype', 'delivery_note_item', force=True)
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt_item', force=True)

	def map_rows(doc_row, return_doc_row, detail_field, doctype):
		"""Map rows after identifying similar ones."""

		frappe.db.sql(""" UPDATE `tab{doctype} Item` set {detail_field} = '{doc_row_name}'
				where name = '{return_doc_row_name}'""" \
			.format(doctype=doctype,
					detail_field=detail_field,
					doc_row_name=doc_row.get('name'),
					return_doc_row_name=return_doc_row.get('name'))) #nosec

	def row_is_mappable(doc_row, return_doc_row, detail_field):
		"""Checks if two rows are similar enough to be mapped."""

		if doc_row.item_code == return_doc_row.item_code and not return_doc_row.get(detail_field):
			if doc_row.get('batch_no') and return_doc_row.get('batch_no') and doc_row.batch_no == return_doc_row.batch_no:
				return True

			elif doc_row.get('serial_no') and return_doc_row.get('serial_no'):
				doc_sn = doc_row.serial_no.split('\n')
				return_doc_sn = return_doc_row.serial_no.split('\n')

				if set(doc_sn) & set(return_doc_sn):
					# if two rows have serial nos in common, map them
					return True

			elif doc_row.rate == return_doc_row.rate:
				return True
		else:
			return False

	def make_return_document_map(doctype, return_document_map):
		"""Returns a map of documents and it's return documents.
		Format => { 'document' : ['return_document_1','return_document_2'] }"""

		return_against_documents = frappe.db.sql("""
			SELECT
				return_against as document, name as return_document
			FROM `tab{doctype}`
			WHERE
				is_return = 1 and docstatus = 1""".format(doctype=doctype),as_dict=1) #nosec

		for entry in return_against_documents:
			return_document_map[entry.document].append(entry.return_document)

		return return_document_map

	def set_document_detail_in_return_document(doctype):
		"""Map each row of the original document in the return document."""
		mapped = []
		return_document_map = defaultdict(list)
		detail_field = "purchase_receipt_item" if doctype=="Purchase Receipt" else "dn_detail"

		child_doc = frappe.scrub("{0} Item".format(doctype))
		frappe.reload_doc("stock", "doctype", child_doc)

		return_document_map = make_return_document_map(doctype, return_document_map)

		count = 0

		#iterate through original documents and its return documents
		for docname in return_document_map:
			doc_items = frappe.get_cached_doc(doctype, docname).get("items")
			for return_doc in return_document_map[docname]:
				return_doc_items = frappe.get_cached_doc(doctype, return_doc).get("items")

				#iterate through return document items and original document items for mapping
				for return_item in return_doc_items:
					for doc_item in doc_items:
						if row_is_mappable(doc_item, return_item, detail_field) and doc_item.get('name') not in mapped:
							map_rows(doc_item, return_item, detail_field, doctype)
							mapped.append(doc_item.get('name'))
							break
						else:
							continue

			# commit after every 100 sql updates
			count += 1
			if count%100 == 0:
				frappe.db.commit()

	set_document_detail_in_return_document("Purchase Receipt")
	set_document_detail_in_return_document("Delivery Note")
	frappe.db.commit()
