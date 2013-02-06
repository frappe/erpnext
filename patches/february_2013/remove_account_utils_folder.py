def execute():
	from webnotes.utils import get_base_path
	import shutil
	import os
	
	shutil.rmtree(os.path.join(get_base_path(), "app", "accounts", "utils"))