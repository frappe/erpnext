from __future__ import unicode_literals
import frappe
from collections import defaultdict

def execute():
	def set_document_detail_in_return_document(doctype):
		frappe.reload_doctype("{0} Item".format(doctype))
		return_document_map = defaultdict(list)
		mapped = []
		detail_field = "purchase_receipt_item" if doctype=="Purchase Receipt" else "dn_detail"

		def make_return_document_map(doctype, return_document_map):
			'''Returns a map of the format:
			{ 'document' : ['return_document_1','return_document_2'] }'''

			return_againts_documents = frappe._dict(frappe.db.sql("""
				SELECT
					return_against as document, name as return_document
				FROM `tab{0}`
				WHERE
					is_return = 1 and docstatus = 1""".format(doctype),as_dict=1))

			for entry in return_againts_documents:
				return_document_map[entry.document].append(entry.return_document)

			return return_document_map

		def row_is_mappable(doc_row, return_doc_row, detail_field):
			if doc_row.item_code == return_doc_row.item_code and not return_doc_row.get(detail_field):
				if doc_row.get('batch_no') and return_doc_row.get('batch_no') and doc_row.batch_no == return_doc_row.batch_no:
					return True

				elif doc_row.get('serial_no') and return_doc_row.get('serial_no'):
					doc_sn, return_doc_sn = doc_row.serial_no.split('\n'), return_doc_row.serial_no.split('\n')
					if set(doc_sn) & set(return_doc_sn):
						return True

				elif doc_row.rate == return_doc_row.rate:
					return True
			else:
				return False

		def map_rows(doc_row, return_doc_row, detail_field, doctype):
			frappe.db.sql(""" UPDATE `tab{0} Item` set {1} = '{2}' where name = '{3}'""" \
				.format(doctype, detail_field, doc_row.get('name'), return_doc_row.get('name')))


		#map each row of return document to the original document
		return_document_map = make_return_document_map(doctype, return_document_map)

		#iterate through original documents and its return documents
		for docname in return_document_map:
			doc_items = frappe.get_doc(doctype, docname).get("items")
			for return_doc in return_document_map[docname]:
				return_doc_items = frappe.get_doc(doctype, return_doc).get("items")

				#iterate through return document items and original document items for mapping
				for return_item in return_doc_items:
					for doc_item in doc_items:
						if row_is_mappable(doc_item, return_item, detail_field) and doc_item.get('name') not in mapped:
							map_rows(doc_item, return_item, detail_field, doctype)
							mapped.append(doc_item.get('name'))
							break
						else:
							continue

	set_document_detail_in_return_document("Purchase Receipt")
	set_document_detail_in_return_document("Delivery Note")
	frappe.db.commit()



