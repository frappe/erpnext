// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Coal Raising Invoice', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1){
			cur_frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			})
			if (frm.doc.outstanding_amount > 0){
				cur_frm.add_custom_button(__('Journal Entry'), function(doc) {
					frm.events.make_journal_entry(frm)
				},__('Create'))
			}			
		}
	},
	make_journal_entry:function(frm){
		frappe.call({
			method:"post_journal_entry",
			doc : frm.doc,
			callback: function (r) {
				
			},
		});
	},
	branch:function(frm){
        cur_frm.set_query("warehouse", function() {
            return {
                query: "erpnext.controllers.queries.filter_branch_wh",
                filters: {'branch': frm.doc.branch}
            }
        });
	},
	get_coal_raising_details:function(frm){
		if(frm.doc.branch){
			frappe.call({
				method:'get_coal_raising_details',
				doc:cur_frm.doc,
				callback:function(r){
					cur_frm.refresh_field('items')
					frm.dirty()
				}
			})
		}
	},
	supplier:function(frm){
		if (frm.doc.supplier){
			frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					party_type:"Supplier",
					party:frm.doc.supplier,
					company: frm.doc.company,
				},
				callback: function(r) {
					if(r.message) {
						console.log(r.message)
						frm.set_value("credit_account",r.message)
						frm.refresh_fields("credit_account")
					}
				}
			});
		}
	},
	make_payment_entry:function(frm){
		frappe.call({
			method:
			"erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
			args: {
				dt: frm.doc.doctype,
				dn: frm.doc.name,
				party_type:"Supplier"
			},
			callback: function (r) {
				var doc = frappe.model.sync(r.message);
				frappe.set_route("Form", doc[0].doctype, doc[0].name);
			},
		});
	},
});
