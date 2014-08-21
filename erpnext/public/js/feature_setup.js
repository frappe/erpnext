// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

/* features setup "Dictionary", "Script"
Dictionary Format
	'projects': {
		'Sales Order': {
			'fields':['project_name'],
			'sales_order_details':['projected_qty']
		},
		'Purchase Order': {
			'fields':['project_name']
		}
	}
// ====================================================================*/
pscript.feature_dict = {
	'fs_projects': {
		'BOM': {'fields':['project_name']},
		'Delivery Note': {'fields':['project_name']},
		'Purchase Invoice': {'entries':['project_name']},
		'Production Order': {'fields':['project_name']},
		'Purchase Order': {'po_details':['project_name']},
		'Purchase Receipt': {'purchase_receipt_details':['project_name']},
		'Sales Invoice': {'fields':['project_name']},
		'Sales Order': {'fields':['project_name']},
		'Stock Entry': {'fields':['project_name']},
		'Timesheet': {'timesheet_details':['project_name']}
	},
	'fs_discounts': {
		'Delivery Note': {'delivery_note_details':['discount_percentage']},
		'Quotation': {'quotation_details':['discount_percentage']},
		'Sales Invoice': {'entries':['discount_percentage']},
		'Sales Order': {'sales_order_details':['discount_percentage','price_list_rate']}
	},
	'fs_purchase_discounts': {
		'Purchase Order': {'po_details':['base_price_list_rate', 'discount_percentage', 'price_list_rate']},
		'Purchase Receipt': {'purchase_receipt_details':['base_price_list_rate', 'discount_percentage', 'price_list_rate']},
		'Purchase Invoice': {'entries':['base_price_list_rate', 'discount_percentage', 'price_list_rate']}
	},
	'fs_brands': {
		'Delivery Note': {'delivery_note_details':['brand']},
		'Material Request': {'indent_details':['brand']},
		'Item': {'fields':['brand']},
		'Purchase Order': {'po_details':['brand']},
		'Purchase Invoice': {'entries':['brand']},
		'Quotation': {'quotation_details':['brand']},
		'Sales Invoice': {'entries':['brand']},
		'Sales BOM': {'fields':['new_item_brand']},
		'Sales Order': {'sales_order_details':['brand']},
		'Serial No': {'fields':['brand']}
	},
	'fs_after_sales_installations': {
		'Delivery Note': {'fields':['installation_status','per_installed'],'delivery_note_details':['installed_qty']}
	},
	'fs_item_batch_nos': {
		'Delivery Note': {'delivery_note_details':['batch_no']},
		'Item': {'fields':['has_batch_no']},
		'Purchase Receipt': {'purchase_receipt_details':['batch_no']},
		'Quality Inspection': {'fields':['batch_no']},
		'Sales and Pruchase Return Wizard': {'return_details':['batch_no']},
		'Sales Invoice': {'entries':['batch_no']},
		'Stock Entry': {'mtn_details':['batch_no']},
		'Stock Ledger Entry': {'fields':['batch_no']}
	},
	'fs_item_serial_nos': {
		'Customer Issue': {'fields':['serial_no']},
		'Delivery Note': {'delivery_note_details':['serial_no'],'packing_details':['serial_no']},
		'Installation Note': {'installed_item_details':['serial_no']},
		'Item': {'fields':['has_serial_no']},
		'Maintenance Schedule': {'item_maintenance_detail':['serial_no'],'maintenance_schedule_detail':['serial_no']},
		'Maintenance Visit': {'maintenance_visit_details':['serial_no']},
		'Purchase Receipt': {'purchase_receipt_details':['serial_no']},
		'Quality Inspection': {'fields':['item_serial_no']},
		'Sales and Pruchase Return Wizard': {'return_details':['serial_no']},
		'Sales Invoice': {'entries':['serial_no']},
		'Stock Entry': {'mtn_details':['serial_no']},
		'Stock Ledger Entry': {'fields':['serial_no']}
	},
	'fs_item_barcode': {
		'Item': {'fields': ['barcode']},
		'Delivery Note': {'delivery_note_details': ['barcode']},
		'Sales Invoice': {'entries': ['barcode']}
	},
	'fs_item_group_in_details': {
		'Delivery Note': {'delivery_note_details':['item_group']},
		'Opportunity': {'enquiry_details':['item_group']},
		'Material Request': {'indent_details':['item_group']},
		'Item': {'fields':['item_group']},
		'Global Defaults': {'fields':['default_item_group']},
		'Purchase Order': {'po_details':['item_group']},
		'Purchase Receipt': {'purchase_receipt_details':['item_group']},
		'Purchase Voucher': {'entries':['item_group']},
		'Quotation': {'quotation_details':['item_group']},
		'Sales Invoice': {'entries':['item_group']},
		'Sales BOM': {'fields':['serial_no']},
		'Sales Order': {'sales_order_details':['item_group']},
		'Serial No': {'fields':['item_group']},
		'Sales Partner': {'partner_target_details':['item_group']},
		'Sales Person': {'target_details':['item_group']},
		'Territory': {'target_details':['item_group']}
	},
	'fs_page_break': {
		'Delivery Note': {'delivery_note_details':['page_break'],'packing_details':['page_break']},
		'Material Request': {'indent_details':['page_break']},
		'Purchase Order': {'po_details':['page_break']},
		'Purchase Receipt': {'purchase_receipt_details':['page_break']},
		'Purchase Voucher': {'entries':['page_break']},
		'Quotation': {'quotation_details':['page_break']},
		'Sales Invoice': {'entries':['page_break']},
		'Sales Order': {'sales_order_details':['page_break']}
	},
	'fs_exports': {
		'Delivery Note': {'fields':['conversion_rate','currency','grand_total','in_words','rounded_total'],'delivery_note_details':['base_price_list_rate','base_amount','base_rate']},
		'POS Setting': {'fields':['conversion_rate','currency']},
		'Quotation': {'fields':['conversion_rate','currency','grand_total','in_words','rounded_total'],'quotation_details':['base_price_list_rate','base_amount','base_rate']},
		'Sales Invoice': {'fields':['conversion_rate','currency','grand_total','in_words','rounded_total'],'entries':['base_price_list_rate','base_amount','base_rate']},
		'Sales BOM': {'fields':['currency']},
		'Sales Order': {'fields':['conversion_rate','currency','grand_total','in_words','rounded_total'],'sales_order_details':['base_price_list_rate','base_amount','base_rate']}
	},

	'fs_imports': {
		'Purchase Invoice': {
			'fields': ['conversion_rate', 'currency', 'grand_total',
		 		'in_words', 'net_total', 'other_charges_added',
		 		'other_charges_deducted'],
			'entries': ['base_price_list_rate', 'base_amount','base_rate']
		},
		'Purchase Order': {
			'fields': ['conversion_rate','currency', 'grand_total',
			'in_words', 'net_total', 'other_charges_added',
			 'other_charges_deducted'],
			'po_details': ['base_price_list_rate', 'base_amount','base_rate']
		},
		'Purchase Receipt': {
			'fields': ['conversion_rate', 'currency','grand_total', 'in_words',
			 	'net_total', 'other_charges_added', 'other_charges_deducted'],
			'purchase_receipt_details': ['base_price_list_rate','base_amount','base_rate']
		},
		'Supplier Quotation': {
			'fields':['conversion_rate','currency']
		}
	},

	'fs_item_advanced': {
		'Item': {'fields':['item_customer_details']}
	},
	'fs_sales_extras': {
		'Address': {'fields':['sales_partner']},
		'Contact': {'fields':['sales_partner']},
		'Customer': {'fields':['sales_team']},
		'Delivery Note': {'fields':['sales_team']},
		'Item': {'fields':['item_customer_details']},
		'Sales Invoice': {'fields':['sales_team']},
		'Sales Order': {'fields':['sales_team']}
	},
	'fs_more_info': {
		"Customer Issue": {"fields": ["more_info"]},
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
		'Purchase Receipt': {'purchase_receipt_details':['qa_no']}
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
	for(var sys_feat in sys_defaults) {
		if(sys_defaults[sys_feat]=='0'
			&& (sys_feat in pscript.feature_dict)) { //"Features to hide" exists
			if(cur_frm.doc.doctype in pscript.feature_dict[sys_feat]) {
				for(var fort in pscript.feature_dict[sys_feat][cur_frm.doc.doctype]) {
					if(fort=='fields') {
						hide_field(pscript.feature_dict[sys_feat][cur_frm.doc.doctype][fort]);
					} else if(cur_frm.fields_dict[fort]) {
						cur_frm.fields_dict[fort].grid.set_column_disp(pscript.feature_dict[sys_feat][cur_frm.doc.doctype][fort], false);
					} else {
						msgprint(__('Grid "')+fort+__('" does not exists'));
					}
				}
			}

		}
	}
})
