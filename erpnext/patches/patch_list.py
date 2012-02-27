patch_list = [
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'stable_branch_shift_09_01_12',
		'description': 'Various Reloads for shifting branch from master to stable'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'print_hide_totals',
		'description': 'Uncheck print_hide for RV, SO, DN and Quotation'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'rename_doctype_indent',
		'description': 'Add DocType Label: Indent to Purchase Requisition'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'production_cleanup',
		'description': 'Major changes in production module, almost rewrited the entire code'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'jan_production_patches',
		'description': 'Fixes after Major changes in production module'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'allocated_to_profile',
		'description': """Change Options to "Profile" for fieldname "allocated_to"
			as this is giving improper values in Permission Engine"""
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'remove_get_tds_button',
		'description': "Remove One Get TDS button, which is appearing twice in JV"
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'customer_address_contact_patch',
		'description': "Install Customer Address Contact report and run patches regarding primary address and contact"
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'doclabel_in_doclayer',
		'description': "Show DocType Labels instead of DocType names in Customize Form View"
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'email_settings_reload',
		'description': "Change type of mail_port field to Int and reload email_settings doctype"
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'serial_no_add_opt',
		'description': "Add option 'Purchase Returned' to Serial No status field"
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'cancel_purchase_returned',
		'description': "Set docstatus = 2 where status = 'Purchase Returned' for serial no"
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'deploy_packing_slip',
		'description': "Delete old packing slip fields & print format & deploy new doctypes related to Packing Slip"
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'map_conversion_rate',
		'description': "Maps conversion rate in doctype mappers PO-PR and PO-PV"
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'account_type_patch',
		'description': 'mentioed account type for some tax accounts'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'subcon_default_val',
		'description': 'Default value of is_subcontracted in PO, PR is No'
	},
	{
		'patch_module': 'patches.jan_mar_2012.website',
		'patch_file': 'all',
		'description': 'Run all website related patches'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'remove_archive',
		'description': 'unarchive all records and drop archive tables'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'no_copy_patch',
		'description': 'insert after fld in custom fld should be no_copy'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'reload_item',
		'description': 'reload item'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'fix_packing_slip',
		'description': 'Update Mapper Delivery Note-Packing Slip'
	},
]
