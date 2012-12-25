import webnotes

def execute():
	from webnotes.utils.nestedset import rebuild_tree
	rebuild_tree("Item Group", "parent_item_group")