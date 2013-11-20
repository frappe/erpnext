# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "stock_ledger_entry")
	webnotes.reload_doc("stock", "doctype", "stock_reconciliation")
	
	rename_fields()
	move_remarks_to_comments()
	store_stock_reco_json()
	
def rename_fields():
	args = [["Stock Ledger Entry", "bin_aqat", "qty_after_transaction"], 
		["Stock Ledger Entry", "fcfs_stack", "stock_queue"],
		["Stock Reconciliation", "reconciliation_date", "posting_date"],
		["Stock Reconciliation", "reconciliation_time", "posting_time"]]
	for doctype, old_fieldname, new_fieldname in args:
		webnotes.conn.sql("""update `tab%s` set `%s`=`%s`""" % 
			(doctype, new_fieldname, old_fieldname))
			
def move_remarks_to_comments():
	from webnotes.utils import get_fullname
	result = webnotes.conn.sql("""select name, remark, modified_by from `tabStock Reconciliation`
		where ifnull(remark, '')!=''""")
	fullname_map = {}
	for reco, remark, modified_by in result:
		webnotes.bean([{
			"doctype": "Comment",
			"comment": remark,
			"comment_by": modified_by,
			"comment_by_fullname": fullname_map.setdefault(modified_by, get_fullname(modified_by)),
			"comment_doctype": "Stock Reconciliation",
			"comment_docname": reco
		}]).insert()
			
def store_stock_reco_json():
	import os
	import json
	from webnotes.utils.datautils import read_csv_content
	from webnotes.utils import get_base_path
	files_path = os.path.join(get_base_path(), "public", "files")
	
	list_of_files = os.listdir(files_path)
	replaced_list_of_files = [f.replace("-", "") for f in list_of_files]
	
	for reco, file_list in webnotes.conn.sql("""select name, file_list 
			from `tabStock Reconciliation`"""):
		if file_list:
			file_list = file_list.split("\n")
			stock_reco_file = file_list[0].split(",")[1]
			stock_reco_file_path = os.path.join(files_path, stock_reco_file)
			if not os.path.exists(stock_reco_file_path):
				if stock_reco_file in replaced_list_of_files:
					stock_reco_file_path = os.path.join(files_path,
						list_of_files[replaced_list_of_files.index(stock_reco_file)])
				else:
					stock_reco_file_path = ""
			
			if stock_reco_file_path:
				with open(stock_reco_file_path, "r") as open_reco_file:
					content = open_reco_file.read()
					try:
						content = read_csv_content(content)
						reconciliation_json = json.dumps(content, separators=(',', ': '))
						webnotes.conn.sql("""update `tabStock Reconciliation`
							set reconciliation_json=%s where name=%s""", 
							(reconciliation_json, reco))
					except Exception:
						# if not a valid CSV file, do nothing
						pass
	