# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	from webnotes.utils.nestedset import rebuild_tree
	rebuild_tree("Item Group", "parent_item_group")