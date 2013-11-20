# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import get_base_path
import os

def execute():
	# find out when was the file list patch run
	res = webnotes.conn.sql("""select applied_on from `__PatchLog`
		where patch='patches.december_2012.file_list_rename' order by applied_on desc limit 1""")
	if res:
		patch_date = res[0][0].date()
		files_path = os.path.join(get_base_path(), "public", "files")
		
		change_map = {}
		
		file_data_list = webnotes.conn.sql("""select name, file_name from `tabFile Data`
			where date(modified) <= %s and ifnull(file_url, '')='' and name like "%%-%%" """,
			patch_date)
			
		# print patch_date
		# print file_data_list
		# print files_path
		
		for fid, file_name in file_data_list:			
			if os.path.exists(os.path.join(files_path, fid)):
				new_fid, new_file_name = fid.replace("-", ""), file_name.replace("-", "")
				
				try:
					webnotes.conn.sql("""update `tabFile Data`
						set name=%s, file_name=%s where name=%s""", (new_fid, new_file_name, fid))
			
					os.rename(os.path.join(files_path, fid), os.path.join(files_path, new_fid))
			
					change_map[",".join((file_name, fid))] = ",".join((new_file_name, new_fid))
				except Exception, e:
					# if duplicate entry, then dont update
					if e[0]!=1062:
						raise
		
		
		changed_keys = change_map.keys()
			
		for dt in webnotes.conn.sql("""select distinct parent from tabDocField 
			where fieldname='file_list'"""):
			try:
				data = webnotes.conn.sql("""select name, file_list from `tab%s`
					where ifnull(file_list, '')!=''""" % dt[0])
				for name, file_list in data:
					new_file_list = []
					file_list = file_list.split("\n")
					for f in file_list:
						if f in changed_keys:
							new_file_list.append(change_map[f])
						else:
							new_file_list.append(f)
					if new_file_list != file_list:
						webnotes.conn.sql("""update `tab%s` set file_list=%s
							where name=%s""" % (dt[0], "%s", "%s"), 
							("\n".join(new_file_list), name))
				
			except Exception, e:
				if e[0]!=1146:
					raise
	