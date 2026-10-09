from erpnext.patches.v16_0.mirror_release_perms_to_custom_docperm import mirror_rules


def execute():
	mirror_rules({"Warehouse": {"Stock Manager": ("read", "report", "print", "email")}})
