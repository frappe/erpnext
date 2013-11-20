# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes, os

def execute():
	import shutil
	from webnotes.utils import get_base_path
	
	for dt in ("item_price", "price_list"):
		path = os.path.join(get_base_path(), "app", "setup", "doctype", dt)
		if os.path.exists(path):
			shutil.rmtree(path)
