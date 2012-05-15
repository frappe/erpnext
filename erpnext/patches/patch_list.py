# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
		'description': 'Add DocType Label: Purchase Request to Purchase Requisition'
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
	{
		'patch_module': 'patches.jan_mar_2012.apps',
		'patch_file': 'todo_item',
		'description': 'Reloads todo item'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'convert_tables_to_utf8',
		'description': 'Convert tables to UTF-8'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'pending_patches',
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'pos_setting_patch',
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'reload_doctype',
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'reload_po_pr_mapper',
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'delete_pur_of_service',
		'description': 'Deletes purpose of service'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'navupdate',
		'description': 'New Navigation Pages'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'label_cleanup',
		'description': 'Remove extra fields and new dynamic labels'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'add_roles_to_admin',
		'description': 'Add Roles to Administrator'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'dt_map_fix',
		'description': 'removed transaction date from dt_mapper'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'reload_table',
		'description': 'Relaod all item table: fld order changes' 
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'remove_series_defval',
		'description': 'Remove rv series default value' 
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'update_stockreco_perm',
		'description': 'Update stock reco permission' 
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'stock_entry_others_patch',
		'description': 'new purpose others in stock entry' 
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'reload_quote',
		'description': 'reload quote: organization fld added' 
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'update_purpose_se',
		'description': 'Purpose SE: Others to Other' 
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'update_se_fld_options',
		'description': 'Purpose SE: Others to Other' 
	},
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'pos_invoice_fix',
		'description': 'Reload POS Invoice' 
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'reload_mapper',
		'description': 'SO-DN, SO-Rv, DN-RV'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'mapper_fix',
		'description': 'DN-RV duplicate table entry'
	},
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'so_rv_mapper_fix',
		'description': 'SO-RV duplicate mapper entry removal'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'sync_ref_db',
		'description': 'Deletes non required doctypes'
	},
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'clean_property_setter',
		'description': 'Patch related to property setter cleanup' 
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'naming_series_patch',
		'description': 'Move naming series options into property setter'
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'rename_dt',
		'description': 'Rename DocType Patch'
	},
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'cleanup_control_panel',
		'description': 'Remove email related fields from Control Panel' 
	},
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'doctype_get_refactor',
		'description': 'Patch related to doctype get refactoring' 
	},
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'delete_docformat',
		'description': 'Deletes DocFormat from database' 
	},
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'usertags',
		'description': 'Adds _user_tags columns to tables' 
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'reload_c_form',
		'description': 'Added attchemnt option and total field'
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'after_sync_cleanup',
		'description': 'cleanup after sync'
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'change_cacheitem_schema',
		'description': 'Modified datatype of `value` column from text to longtext'
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'remove_default_from_rv_detail',
		'description': ''
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'update_role_in_address',
		'description': 'updated roles in address'
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'update_permlevel_in_address',
		'description': 'updated permlevel in address'
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'update_appraisal_permission',
		'description': 'updated permission in appraisal'
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'serial_no_fixes',
		'description': 'fixes for sle creation while import'
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'repost_stock_for_posting_time',
		'description': 'repost stock for posting time 00:00:seconds'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'cleanup_property_setter',
		'description': 'cleanup_property_setter'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'rename_prev_doctype',
		'description': 'rename prev doctype fix'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'cleanup_notification_control',
		'description': 'cleanup notification control'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'renamedt_in_custom_search_criteria',
		'description': 'raname dt in custom search criteria'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'stock_reco_patch',
		'description': 'stock reco patch: store diff info in field'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'cms',
		'description': 'generate html pages'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'reload_reports',
		'description': 'reload reports: itemwise sales/delivery details'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'page_role_series_fix',
		'description': 'reset series of page role at max'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'reload_sales_invoice_pf',
		'description': 'Reload sales invoice print formats'
	},

]
