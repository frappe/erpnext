// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Statement Format', {
	refresh: function(frm) {
		if(frm.doc.txn_type_derivation !== 'Map From Statement'){
			txn_types = frappe.meta.get_docfield('Bank Statement Mapping Item', 'target_field').options
			txn_types = txn_types.split('\n')
			txn_types.splice(txn_types.indexOf('Transaction Type'),1)
			frm.set_df_property('target_field', 'options', txn_types, frm.doc.name, 'bank_statement_mapping_item')
		}
	},
	txn_type_derivation: (frm)=>{
		if(frm.doc.txn_type_derivation !== 'Map From Statement'){
			txn_types = frappe.meta.get_docfield('Bank Statement Mapping Item', 'target_field').options
			txn_types = txn_types.split('\n')
			txn_types.splice(txn_types.indexOf('Transaction Type'),1)
			frm.set_df_property('target_field', 'options', txn_types, frm.doc.name, 'bank_statement_mapping_item')
		}
	}
});
