// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

/* features setup "Dictionary", "Script"
Dictionary Format
	'projects': {
		'Sales Order': {
			'fields':['project_name'],
			'items':['projected_qty']
		},
		'Purchase Order': {
			'fields':['project_name']
		}
	}
// ====================================================================*/
frappe.provide("erpnext.feature_setup");
erpnext.feature_setup.feature_dict = {
	'fs_projects': {
		'BOM': {'fields':['project_name']},
		'Delivery Note': {'fields':['project_name']},
		'Purchase Invoice': {'items':['project_name']},
		'Production Order': {'fields':['project_name']},
		'Purchase Order': {'items':['project_name']},
		'Purchase Receipt': {'items':['project_name']},
		'Sales Invoice': {'fields':['project_name']},
		'Sales Order': {'fields':['project_name']},
		'Stock Entry': {'fields':['project_name']},
		'Timesheet': {'timesheet_details':['project_name']}
	},
	'fs_discounts': {
		'Delivery Note': {'items':['discount_percentage']},
		'Quotation': {'items':['discount_percentage']},
		'Sales Invoice': {'items':['discount_percentage']},
		'Sales Order': {'items':['discount_percentage','price_list_rate']}
	},
	'fs_purchase_discounts': {
		'Purchase Order': {'items':['base_price_list_rate', 'discount_percentage', 'price_list_rate']},
		'Purchase Receipt': {'items':['base_price_list_rate', 'discount_percentage', 'price_list_rate']},
		'Purchase Invoice': {'items':['base_price_list_rate', 'discount_percentage', 'price_list_rate']}
	},
	'fs_brands': {
		'Delivery Note': {'items':['brand']},
		'Material Request': {'items':['brand']},
		'Item': {'fields':['brand']},
		'Purchase Order': {'items':['brand']},
		'Purchase Invoice': {'items':['brand']},
		'Quotation': {'items':['brand']},
		'Sales Invoice': {'items':['brand']},
		'Sales BOM': {'fields':['new_item_brand']},
		'Sales Order': {'items':['brand']},
		'Serial No': {'fields':['brand']}
	},
	'fs_after_sales_installations': {
		'Delivery Note': {'fields':['installation_status','per_installed'],'items':['installed_qty']}
	},
	'fs_item_batch_nos': {
		'Delivery Note': {'items':['batch_no']},
		'Item': {'fields':['has_batch_no']},
		'Purchase Receipt': {'items':['batch_no']},
		'Quality Inspection': {'fields':['batch_no']},
		'Sales and Pruchase Return Wizard': {'return_details':['batch_no']},
		'Sales Invoice': {'items':['batch_no']},
		'Stock Entry': {'items':['batch_no']},
		'Stock Ledger Entry': {'fields':['batch_no']}
	},
	'fs_item_serial_nos': {
		'Warranty Claim': {'fields':['serial_no']},
		'Delivery Note': {'items':['serial_no'],'packed_items':['serial_no']},
		'Installation Note': {'items':['serial_no']},
		'Item': {'fields':['has_serial_no']},
		'Maintenance Schedule': {'items':['serial_no'],'schedules':['serial_no']},
		'Maintenance Visit': {'purposes':['serial_no']},
		'Purchase Receipt': {'items':['serial_no']},
		'Quality Inspection': {'fields':['item_serial_no']},
		'Sales and Pruchase Return Wizard': {'return_details':['serial_no']},
		'Sales Invoice': {'items':['serial_no']},
		'Stock Entry': {'items':['serial_no']},
		'Stock Ledger Entry': {'fields':['serial_no']}
	},
	'fs_item_barcode': {
		'Item': {'fields': ['barcode']},
		'Delivery Note': {'items': ['barcode']},
		'Sales Invoice': {'items': ['barcode']},
		'Stock Entry': {'items': ['barcode']}
	},
	'fs_item_group_in_details': {
		'Delivery Note': {'items':['item_group']},
		'Opportunity': {'items':['item_group']},
		'Material Request': {'items':['item_group']},
		'Item': {'fields':['item_group']},
		'Global Defaults': {'fields':['default_item_group']},
		'Purchase Order': {'items':['item_group']},
		'Purchase Receipt': {'items':['item_group']},
		'Purchase Voucher': {'items':['item_group']},
		'Quotation': {'items':['item_group']},
		'Sales Invoice': {'items':['item_group']},
		'Sales BOM': {'fields':['serial_no']},
		'Sales Order': {'items':['item_group']},
		'Serial No': {'fields':['item_group']},
		'Sales Partner': {'targets':['item_group']},
		'Sales Person': {'targets':['item_group']},
		'Territory': {'targets':['item_group']}
	},
	'fs_page_break': {
		'Delivery Note': {'items':['page_break'],'packed_items':['page_break']},
		'Material Request': {'items':['page_break']},
		'Purchase Order': {'items':['page_break']},
		'Purchase Receipt': {'items':['page_break']},
		'Purchase Voucher': {'items':['page_break']},
		'Quotation': {'items':['page_break']},
		'Sales Invoice': {'items':['page_break']},
		'Sales Order': {'items':['page_break']}
	},
	'fs_exports': {
		'Delivery Note': {
			'fields': ['conversion_rate','currency','base_grand_total','base_in_words','base_rounded_total',
				'base_total', 'base_net_total', 'base_discount_amount', 'base_total_taxes_and_charges'],
			'items': ['base_price_list_rate','base_amount','base_rate', 'base_net_rate', 'base_net_amount']
		},
		'POS Setting': {'fields':['conversion_rate','currency']},
		'Quotation': {
			'fields': ['conversion_rate','currency','base_grand_total','base_in_words','base_rounded_total',
				'base_total', 'base_net_total', 'base_discount_amount', 'base_total_taxes_and_charges'],
			'items': ['base_price_list_rate','base_amount','base_rate', 'base_net_rate', 'base_net_amount']
		},
		'Sales Invoice': {
			'fields': ['conversion_rate','currency','base_grand_total','base_in_words','base_rounded_total',
				'base_total', 'base_net_total', 'base_discount_amount', 'base_total_taxes_and_charges'],
			'items': ['base_price_list_rate','base_amount','base_rate', 'base_net_rate', 'base_net_amount']
		},
		'Sales BOM': {'fields':['currency']},
		'Sales Order': {
			'fields': ['conversion_rate','currency','base_grand_total','base_in_words','base_rounded_total',
				'base_total', 'base_net_total', 'base_discount_amount', 'base_total_taxes_and_charges'],
			'items': ['base_price_list_rate','base_amount','base_rate', 'base_net_rate', 'base_net_amount']
		}
	},

	'fs_imports': {
		'Purchase Invoice': {
			'fields': ['conversion_rate', 'currency', 'base_grand_total', 'base_discount_amount',
		 		'base_in_words', 'base_total', 'base_net_total', 'base_taxes_and_charges_added',
		 		'base_taxes_and_charges_deducted', 'base_total_taxes_and_charges'],
			'items': ['base_price_list_rate', 'base_amount','base_rate', 'base_net_rate', 'base_net_amount']
		},
		'Purchase Order': {
			'fields': ['conversion_rate','currency', 'base_grand_total', 'base_discount_amount',
				'base_in_words', 'base_total', 'base_net_total', 'base_taxes_and_charges_added',
			 	'base_taxes_and_charges_deducted', 'base_total_taxes_and_charges'],
			'items': ['base_price_list_rate', 'base_amount','base_rate', 'base_net_rate', 'base_net_amount']
		},
		'Purchase Receipt': {
			'fields': ['conversion_rate', 'currency','base_grand_total', 'base_in_words', 'base_total',
			 	'base_net_total', 'base_taxes_and_charges_added', 'base_taxes_and_charges_deducted',
				'base_total_taxes_and_charges', 'base_discount_amount'],
			'items': ['base_price_list_rate','base_amount','base_rate', 'base_net_rate', 'base_net_amount']
		},
		'Supplier Quotation': {
			'fields': ['conversion_rate', 'currency','base_grand_total', 'base_in_words', 'base_total',
			 	'base_net_total', 'base_taxes_and_charges_added', 'base_taxes_and_charges_deducted',
				'base_total_taxes_and_charges', 'base_discount_amount'],
			'items': ['base_price_list_rate','base_amount','base_rate', 'base_net_rate', 'base_net_amount']
		}
	},

	'fs_item_advanced': {
		'Item': {'fields':['customer_items']}
	},
	'fs_sales_extras': {
		'Address': {'fields':['sales_partner']},
		'Contact': {'fields':['sales_partner']},
		'Customer': {'fields':['sales_team']},
		'Delivery Note': {'fields':['sales_team']},
		'Item': {'fields':['customer_items']},
		'Sales Invoice': {'fields':['sales_team']},
		'Sales Order': {'fields':['sales_team']}
	},
	'fs_more_info': {
		"Warranty Claim": {"fields": ["more_info"]},
		'Material Request': {'fields':['more_info']},
		'Lead': {'fields':['more_info']},
		'Opportunity': {'fields':['more_info']},
		'Purchase Invoice': {'fields':['more_info']},
		'Purchase Order': {'fields':['more_info']},
		'Purchase Receipt': {'fields':['more_info']},
		'Supplier Quotation': {'fields':['more_info']},
		'Quotation': {'fields':['more_info']},
		'Sales Invoice': {'fields':['more_info']},
		'Sales Order': {'fields':['more_info']},
		'Delivery Note': {'fields':['more_info']},
	},
	'fs_quality': {
		'Item': {'fields':['inspection_criteria','inspection_required']},
		'Purchase Receipt': {'items':['qa_no']}
	},
	'fs_manufacturing': {
		'Item': {'fields':['manufacturing']}
	},
	'fs_pos': {
		'Sales Invoice': {'fields':['is_pos']}
	},
	'fs_recurring_invoice': {
		'Sales Invoice': {'fields': ['recurring_invoice']}
	}
}

$(document).bind('form_refresh', function() {
	var feature_dict = erpnext.feature_setup.feature_dict;
	for(var sys_feat in sys_defaults) {
		if(sys_defaults[sys_feat]=='0'
			&& (sys_feat in feature_dict)) { //"Features to hide" exists
			if(cur_frm.doc.doctype in feature_dict[sys_feat]) {
				for(var fort in feature_dict[sys_feat][cur_frm.doc.doctype]) {
					if(fort=='fields') {
						hide_field(feature_dict[sys_feat][cur_frm.doc.doctype][fort]);
					} else if(cur_frm.fields_dict[fort]) {
						cur_frm.fields_dict[fort].grid.set_column_disp(feature_dict[sys_feat][cur_frm.doc.doctype][fort], false);
					} else {
						msgprint(__('Grid "')+fort+__('" does not exists'));
					}
				}
			}

		}
	}
})
