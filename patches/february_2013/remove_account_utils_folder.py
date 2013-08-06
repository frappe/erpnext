# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	from webnotes.utils import get_base_path
	import shutil
	import os
	
	utils_path = os.path.join(get_base_path(), "app", "accounts", "utils")
	if os.path.exists(utils_path):
		shutil.rmtree(utils_path)