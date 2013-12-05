# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	from patches.january_2013 import rebuild_tree
	rebuild_tree.execute()