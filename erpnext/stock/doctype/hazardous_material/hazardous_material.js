// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hazardous Material', {
	onload: function(frm, cdt, cdn) {
			$.each(frm.doc.ghs_hazard_statements, function(idx, row){
				frm.clear_table('ghs_precautionary_tatements')
				frappe.call({
					method: "erpnext.stock.doctype.hazardous_material.hazardous_material.get_ghs_precautionary_statements",
					args: {name: row.ghs_hazard_statement
						 },
					callback: function(r) {
						let ghsPS = r.message.hazardous_material_ghs_precautionary_statements;
						ghsPS.forEach(ghs_precautionary_statement => {
							frm.add_child('ghs_precautionary_tatements', ghs_precautionary_statement);
						});
						frm.refresh_field('ghs_precautionary_tatements');
		
					}
				})
				
			 })
	},
	refresh: function (frm, cdt, cdn) {
		   frm.fields_dict['item'].get_query = function(doc) {
			   return {
				   filters: {
					   "is_hazardous_material": 1
				   }
			   }
		   }
	},
	before_save: function(frm){
		$.each(frm.doc.ghs_hazard_statements, function(idx, row){
			frm.clear_table('ghs_precautionary_tatements')
			frappe.call({
				method: "erpnext.stock.doctype.hazardous_material.hazardous_material.get_ghs_precautionary_statements",
				args: {name: row.ghs_hazard_statement
					 },
				callback: function(r) {
					let ghsPS = r.message.hazardous_material_ghs_precautionary_statements;
					ghsPS.forEach(ghs_precautionary_statement => {
						frm.add_child('ghs_precautionary_tatements', ghs_precautionary_statement);
					});
					frm.refresh_field('ghs_precautionary_tatements');
	
				}
			})
			
		 })
	},
	lifecycle: function(frm){       
		if(frm.doc.lifecycle == "Active use"){
			if(!frm.doc.introduction_date && !frm.doc.decommissioning_date){
				frm.set_df_property("decommissioning_date", "read_only", 1);
				frm.set_df_property("introduction_date", "read_only", 0);
			}
		}
		if(frm.doc.lifecycle == "Decommissioned"){
			if(!frm.doc.decommissioning_date && !frm.doc.introduction_date){
				frm.set_df_property("introduction_date", "read_only", 1);
				frm.set_df_property("decommissioning_date", "read_only", 0);
			}
		}
		if(frm.doc.lifecycle == "Evaluation"){
			if(!frm.doc.introduction_date && !frm.doc.decommissioning_date){
				frm.set_df_property("decommissioning_date", "read_only", 0);
				frm.set_df_property("introduction_date", "read_only", 0);
			}
		}
		if(frm.doc.lifecycle == "Phase-out"){
			if(!frm.doc.introduction_date && !frm.doc.decommissioning_date){
				frm.set_df_property("decommissioning_date", "read_only", 0);
				frm.set_df_property("introduction_date", "read_only", 0);
			}
		}
	},
	introduction_date: function(frm){
		if(frm.doc.lifecycle == "Active use"){ 
			if(frm.doc.introduction_date){
				frm.set_df_property("decommissioning_date", "read_only", 0);
			}
		}
	},
	decommissioning_date: function(frm){
		if(frm.doc.lifecycle == "Decommissioned"){ 
			if(frm.doc.decommissioning_date){
				frm.set_df_property("introduction_date", "read_only", 0);
			}
		}
	}
	});
	frappe.ui.form.on('Hazardous Material Company Use', {
		lifecycle: function(frm, cdt, cdn){
				var child = locals[cdt][cdn]
				var d_d = frappe.meta.get_docfield("Hazardous Material Company Use","decommissioning_date", cur_frm.doc.name);
				var i_d = frappe.meta.get_docfield("Hazardous Material Company Use","introduction_date", cur_frm.doc.name);
				if(child.lifecycle === 'Active use'){
					if(!child.decommissioning_date && !child.introduction_date){
						d_d.read_only = 1;
						i_d.read_only = 0;
						frm.refresh_field('hazardous_material_company_use');
					}
				}
				if(child.lifecycle === 'Decommissioned'){
					if(!child.decommissioning_date && !child.introduction_date) {
						d_d.read_only = 0;
						i_d.read_only = 1;
						frm.refresh_field('hazardous_material_company_use');
					}
				}
				if(child.lifecycle === 'Evaluation'){
					if(!child.decommissioning_date && !child.introduction_date){
						d_d.read_only = 0;
						i_d.read_only = 0;
						frm.refresh_field('hazardous_material_company_use');
					}
				}
				if(child.lifecycle === 'Phase-out'){
					if(!child.decommissioning_date && !child.introduction_date){
						d_d.read_only = 0;
						i_d.read_only = 0;
						frm.refresh_field('hazardous_material_company_use');
					}
				}
			},
		decommissioning_date: function(frm, cdt, cdn){
			var child = locals[cdt][cdn]
			var d_d = frappe.meta.get_docfield("Hazardous Material Company Use","decommissioning_date", cur_frm.doc.name);
			var i_d = frappe.meta.get_docfield("Hazardous Material Company Use","introduction_date", cur_frm.doc.name);
	
			if(child.decommissioning_date){
				i_d.read_only = 0;
				frm.refresh_field('hazardous_material_company_use');
			}
		},
		introduction_date: function(frm, cdt, cdn){
			var child = locals[cdt][cdn]
			var d_d = frappe.meta.get_docfield("Hazardous Material Company Use","decommissioning_date", cur_frm.doc.name);
			var i_d = frappe.meta.get_docfield("Hazardous Material Company Use","introduction_date", cur_frm.doc.name);
	
			if(child.introduction_date){
				d_d.read_only = 0;
				frm.refresh_field('hazardous_material_company_use');
			}
		}
	});
