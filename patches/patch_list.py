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

from __future__ import unicode_literals
patch_list = [
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'so_rv_mapper_fix',
		'description': 'SO-RV duplicate mapper entry removal'
	},
	{
		'patch_module': 'patches.mar_2012',
		'patch_file': 'clean_property_setter',
		'description': 'Patch related to property setter cleanup' 
	},
	{
		'patch_module': 'patches.jan_mar_2012',
		'patch_file': 'sync_ref_db',
		'description': 'Deletes non required doctypes'
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
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'std_pf_readonly',
		'description': 'Make standard print formats readonly for system manager'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'reload_so_pending_items',
		'description': 'reload so pending items'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'customize_form_cleanup',
		'description': 'cleanup customize form records'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'cs_server_readonly',
		'description': 'Make server custom script readonly for system manager'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'clear_session_cache',
		'description': 'clears session cache as shifting to json format'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'same_purchase_rate_patch',
		'description': 'Main same rate throughout pur cycle: in global defaults, by default set true'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'create_report_manager_role',
		'description': 'Create report manager role if not exists'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'reload_customer_address_contact',
		'description': 'Reload report customer address contact'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'profile_perm_patch',
		'description': 'Make profile readonly for role All'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'remove_euro_currency',
		'description': 'Remove EURO currency and replace with EUR'
	},
	{
		'patch_module': 'patches.may_2012',
		'patch_file': 'remove_communication_log',
		'description': 'Remove Communication Log and replace it with Communication'
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'barcode_in_feature_setup',
		'description': 'Track item by barcode'
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'copy_uom_for_pur_inv_item',
		'description': 'Copy uom for pur inv item from PO and PR item table'
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'fetch_organization_from_lead',
		'description': 'Fetch organization from lead in quote'
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'reports_list_permission',
		'description': 'allow read permission to all for report list'
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'support_ticket_autoreply',
		'description': 'New Send Autoreply checkbox in Email Settings'
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'series_unique_patch',
		'description': "add unique constraint to series table's name column"
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'set_recurring_type',
		'description': "set recurring type as monthly in old"
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'alter_tabsessions',
		'description': "alter tabsessions to change user column definition"
	},
	{
		'patch_module': 'patches.june_2012',
		'patch_file': 'delete_old_parent_entries',
		'description': "delete entries of child table having parent like old_par%% or ''"
	},
	{
		'patch_module': 'patches.april_2012',
		'patch_file': 'delete_about_contact',
		'description': "delete depracated doctypes of website module"
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'reload_pr_po_mapper',
		'description': "order date should be greater than equal to request date"
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'address_contact_perms',
		'description': "sync address contact perms"
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'packing_list_cleanup_and_serial_no',
		'description': "packing list cleanup and serial no status update"
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'deprecate_import_data_control',
		'description': "deprecate doctype - Import Data Control and page - Import Data"
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'default_freeze_account',
		'description': "set default freeze_account as 'No' where NULL"
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'update_purchase_tax',
		'description': "rename options in purchase taxes and charges"
	},
	{	'patch_module': 'patches.june_2012',
		'patch_file': 'cms2',
		'description': 'cms2 release patches'
	},
	{	'patch_module': 'patches.july_2012',
		'patch_file': 'auth_table',
		'description': 'create new __Auth table'
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'remove_event_role_owner_match',
		'description': "Remove Owner match from Event DocType's Permissions"
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'deprecate_bulk_rename',
		'description': "Remove Bulk Rename Tool"
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'blog_guest_permission',
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'bin_permission',
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'project_patch_repeat',
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'repost_stock_due_to_wrong_packing_list',
	},
	{
		'patch_module': 'patches.july_2012',
		'patch_file': 'supplier_quotation',
	},
	{
		'patch_module': 'patches.august_2012',
		'patch_file': 'report_supplier_quotations',
	},
	{
		'patch_module': 'patches.august_2012',
		'patch_file': 'task_allocated_to_assigned',
	},
	{
		'patch_module': 'patches.august_2012',
		'patch_file': 'change_profile_permission',
	},
	{
		'patch_module': 'patches.august_2012',
		'patch_file': 'changed_blog_date_format',
	},
	{
		'patch_module': 'patches.august_2012',
		'patch_file': 'repost_billed_amt',
	},
	{
		'patch_module': 'patches.august_2012',
		'patch_file': 'remove_cash_flow_statement',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'stock_report_permissions_for_accounts',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'communication_delete_permission',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'reload_criteria_stock_ledger',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'all_permissions_patch',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'customer_permission_patch',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'add_stock_ledger_entry_index',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'plot_patch',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'event_permission',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'repost_stock',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'reload_gross_profit',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'rebuild_trees',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'deprecate_account_balance',
	},
	{
		'patch_module': 'patches.september_2012',
		'patch_file': 'profile_delete_permission',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'update_permission',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'reload_gl_mapper',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'fix_wrong_vouchers',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'remove_old_customer_contact_address',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'company_fiscal_year_docstatus_patch',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'update_account_property',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'remove_old_trial_bal',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'fix_cancelled_gl_entries',
	},
	{
		'patch_module': 'patches.october_2012',
		'patch_file': 'custom_script_delete_permission',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'custom_field_insert_after',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'reload_stock_ledger_report',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'delete_item_sales_register1',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'rename_employee_leave_balance_report',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'report_permissions',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'customer_issue_allocated_to_assigned',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'reset_appraisal_permissions',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'disable_cancelled_profiles',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'remove_old_unbilled_items_report',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'support_ticket_response_to_communication',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'cancelled_bom_patch',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'communication_sender_and_recipient',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'update_delivered_billed_percentage_for_pos',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'add_theme_to_profile',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'add_employee_field_in_employee',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'leave_application_cleanup',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'production_order_patch',
	},
	{
		'patch_module': 'patches.november_2012',
		'patch_file': 'gle_floating_point_issue',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'deprecate_tds',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'expense_leave_reload',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'repost_ordered_qty',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'repost_projected_qty',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'reload_debtors_creditors_ledger',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'website_cache_refactor',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'production_cleanup',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'fix_default_print_format',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'file_list_rename',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'replace_createlocal',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'clear_web_cache',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'remove_quotation_next_contact',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'stock_entry_cleanup',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'production_order_naming_series',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'rebuild_item_group_tree',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'address_title',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'delete_form16_print_format',
	},
	{
		'patch_module': 'patches.december_2012',
		'patch_file': 'remove_project_mapper',
	},
]