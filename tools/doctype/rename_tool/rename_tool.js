// over-ride the link query to return relevant link names

cur_frm.fields_dict.document_to_rename.get_query = function(doc, dt, dn) {
	return "SELECT name FROM `tab"+doc.select_doctype+"` WHERE docstatus<2 AND name LIKE '%s' LIMIT 50";
}