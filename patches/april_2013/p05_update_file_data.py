# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes, webnotes.utils, os

def execute():
	webnotes.reload_doc("core", "doctype", "file_data")
	webnotes.reset_perms("File Data")
	
	singles = get_single_doctypes()
	
	for doctype in webnotes.conn.sql_list("""select parent from tabDocField where 
		fieldname='file_list'"""):
		# the other scenario is handled in p07_update_file_data_2
		if doctype in singles:
			update_file_list(doctype, singles)
		
		# export_to_files([["DocType", doctype]])
		
def get_single_doctypes():
	return webnotes.conn.sql_list("""select name from tabDocType
			where ifnull(issingle,0)=1""")
		
def update_file_list(doctype, singles):
	if doctype in singles:
		doc = webnotes.doc(doctype, doctype)
		if doc.file_list:
			update_for_doc(doctype, doc)
			webnotes.conn.set_value(doctype, None, "file_list", None)
	else:
		try:
			for doc in webnotes.conn.sql("""select name, file_list from `tab%s` where 
				ifnull(file_list, '')!=''""" % doctype, as_dict=True):
				update_for_doc(doctype, doc)
			webnotes.conn.commit()
			webnotes.conn.sql("""alter table `tab%s` drop column `file_list`""" % doctype)
		except Exception, e:
			print webnotes.getTraceback()
			if (e.args and e.args[0]!=1054) or not e.args:
				raise

def update_for_doc(doctype, doc):
	for filedata in doc.file_list.split("\n"):
		if not filedata:
			continue
			
		filedata = filedata.split(",")
		if len(filedata)==2:
			filename, fileid = filedata[0], filedata[1] 
		else:
			continue
		
		exists = True
		if not (filename.startswith("http://") or filename.startswith("https://")):
			if not os.path.exists(webnotes.utils.get_site_path(webnotes.conf.files_path, filename)):
				exists = False

		if exists:
			if webnotes.conn.exists("File Data", fileid):
				try:
					fd = webnotes.bean("File Data", fileid)
					if not (fd.doc.attached_to_doctype and fd.doc.attached_to_name):
						fd.doc.attached_to_doctype = doctype
						fd.doc.attached_to_name = doc.name
						fd.save()
					else:
						fd = webnotes.bean("File Data", copy=fd.doclist)
						fd.doc.attached_to_doctype = doctype
						fd.doc.attached_to_name = doc.name
						fd.doc.name = None
						fd.insert()
				except webnotes.DuplicateEntryError:
					pass
		else:
			webnotes.conn.sql("""delete from `tabFile Data` where name=%s""",
				fileid)
