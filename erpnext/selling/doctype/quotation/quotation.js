// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

/*{% include 'item_info/item_info/custom_quotation.js' %};*/
{% include 'selling/sales_common.js' %}

erpnext.selling.QuotationController = erpnext.selling.SellingController.extend({
	onload: function(doc, dt, dn) {
		var me = this;
		this._super(doc, dt, dn);
		if(doc.customer && !doc.quotation_to)
			doc.quotation_to = "Customer";
		else if(doc.lead && !doc.quotation_to)
			doc.quotation_to = "Lead";

	},
	refresh: function(doc, dt, dn) {
		this._super(doc, dt, dn);

		if(doc.docstatus == 1 && doc.status!=='Lost') {
			cur_frm.add_custom_button(__('Sales Order'),
				cur_frm.cscript['Make Sales Order'], __("Make"));

			if(doc.status!=="Ordered") {
				cur_frm.add_custom_button(__('Lost'),
					cur_frm.cscript['Declare Order Lost'], __("Status"));
			}
			
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}

		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('Opportunity'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
						source_doctype: "Opportunity",
						get_query_filters: {
							status: ["not in", ["Lost", "Closed"]],
							enquiry_type: cur_frm.doc.order_type,
							customer: cur_frm.doc.customer || undefined,
							lead: cur_frm.doc.lead || undefined,
							company: cur_frm.doc.company
						}
					})
				}, __("Get items from"), "btn-default");
		}

		this.toggle_reqd_lead_customer();
		
	},

	quotation_to: function() {
		var me = this;
		if (this.frm.doc.quotation_to == "Lead") {
			this.frm.set_value("customer", null);
			this.frm.set_value("contact_person", null);
		} else if (this.frm.doc.quotation_to == "Customer") {
			this.frm.set_value("lead", null);
		}

		this.toggle_reqd_lead_customer();
	},

	toggle_reqd_lead_customer: function() {
		var me = this;

		this.frm.toggle_reqd("lead", this.frm.doc.quotation_to == "Lead");
		this.frm.toggle_reqd("customer", this.frm.doc.quotation_to == "Customer");

		// to overwrite the customer_filter trigger from queries.js
		$.each(["customer_address", "shipping_address_name"],
			function(i, opts) {
				me.frm.set_query(opts, me.frm.doc.quotation_to==="Lead"
					? erpnext.queries["lead_filter"] : erpnext.queries["customer_filter"]);
			}
		);
	},

	tc_name: function() {
		this.get_terms();
	},

	validate_company_and_party: function(party_field) {
		if(!this.frm.doc.quotation_to) {
			msgprint(__("Please select a value for {0} quotation_to {1}", [this.frm.doc.doctype, this.frm.doc.name]));
			return false;
		} else if (this.frm.doc.quotation_to == "Lead") {
			return true;
		} else {
			return this._super(party_field);
		}
	},

	lead: function() {
		var me = this;
		frappe.call({
			method: "erpnext.crm.doctype.lead.lead.get_lead_details",
			args: { "lead": this.frm.doc.lead },
			callback: function(r) {
				if(r.message) {
					me.frm.updating_party_details = true;
					me.frm.set_value(r.message);
					me.frm.refresh();
					me.frm.updating_party_details = false;

				}
			}
		})
	}
});

cur_frm.script_manager.make(erpnext.selling.QuotationController);

cur_frm.fields_dict.lead.get_query = function(doc,cdt,cdn) {
	return{	query: "erpnext.controllers.queries.lead_query" }
}

cur_frm.cscript['Make Sales Order'] = function() {
	frappe.model.open_mapped_doc({
		method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
		frm: cur_frm
	})
}

cur_frm.cscript['Declare Order Lost'] = function(){
	var dialog = new frappe.ui.Dialog({
		title: "Set as Lost",
		fields: [
			{"fieldtype": "Text", "label": __("Reason for losing"), "fieldname": "reason",
				"reqd": 1 },
			{"fieldtype": "Button", "label": __("Update"), "fieldname": "update"},
		]
	});

	dialog.fields_dict.update.$input.click(function() {
		args = dialog.get_values();
		if(!args) return;
		return cur_frm.call({
			method: "declare_order_lost",
			doc: cur_frm.doc,
			args: args.reason,
			callback: function(r) {
				if(r.exc) {
					msgprint(__("There were errors."));
					return;
				}
				dialog.hide();
				cur_frm.refresh();
			},
			btn: this
		})
	});
	dialog.show();

}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(frappe.boot.notification_settings.quotation))
		cur_frm.email_doc(frappe.boot.notification_settings.quotation_message);
}

frappe.ui.form.on("Quotation Item", "items_on_form_rendered", function(frm, cdt, cdn) {
	// enable tax_amount field if Actual
})

frappe.ui.form.on("Quotation Item", "stock_balance", function(frm, cdt, cdn) {
	var d = frappe.model.get_doc(cdt, cdn);
	frappe.route_options = {"item_code": d.item_code}; 
	frappe.set_route("query-report", "Stock Balance");
})




//dialog for related items


frappe.ui.form.on("Quotation Item", {
    relative_items: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn]
        var me = this;            
        this.dialog = new frappe.ui.Dialog({
            title: "Select Relative Items",
                fields: [
                   {"fieldtype": "HTML" , "fieldname": "relative_items" , "label": "Relative Items"},
                   ],
                   primary_action_label: "Add",
                    primary_action: function(){
                        add_quotation_items(me.dialog)
                    }
            });
        fd = this.dialog.fields_dict;
        frappe.call({
            method: "erpnext.selling.doctype.quotation.quotation.get_relative_items",
            args: {
                "item_code":d.item_code,
                "item_name":d.item_name
            },
            callback: function(r){
                var related_list = []
                if(cur_frm.doc.related_items){
                    for(var i = 0 ; i < cur_frm.doc.related_items.length ; i++){
                        if(cur_frm.doc.related_items[i].item_code){
                            related_list.push(cur_frm.doc.related_items[i].item_code);
                        }
                    }
                }
                if(r.message){
                    r.message["Suggested Items"] = filter(r.message["Suggested Items"],related_list)
                    r.message["Alternate Items"] = filter(r.message["Alternate Items"],related_list)
                    r.message["Accessory Items"] = filter(r.message["Accessory Items"],related_list)
                    var Suggested = r.message["Suggested Items"]
                    var alternative = r.message["Alternate Items"]
                    var accessories = r.message["Accessory Items"]
                    max = Math.max(Suggested.length,alternative.length,accessories.length);
                    if(max > 0){
                        $(frappe.render_template("relative_items",{"items":r.message,"max":max})).appendTo(me.dialog.fields_dict.relative_items.$wrapper);
                        me.dialog.show();
                    }
                    else{
                        msgprint("All Related Items For Item Code - " +" "+ d.item_code +"\n"+"Already Added To Related Items Table")
                    }
                }
                else{
                    msgprint("No Related Items For Item Code - " +" "+ d.item_code)    
                }
            }
        });
        add_quotation_items =function(){
            var items_to_add = []
            $.each($(fd.relative_items.wrapper).find(".select:checked"), function(value, item){
                items_to_add.push($(item).val());
            });
            if(items_to_add.length > 0){
                frappe.call({
                    method:"erpnext.selling.doctype.quotation.quotation.items_details",
                    args: { 
                        "item_list": items_to_add,
                        "item_code":d.item_code
                    },
                    callback: function(r) {
                        $.each(r.message, function(i, d) {
                            var row = frappe.model.add_child(cur_frm.doc, "Related Item", "related_items");
                            row.item_code = d.item_code;
                            row.item_name = d.item_name;
                            row.item_type = d.item_type;
                            row.parent_item = d.name;
                            row.rate = 0;
                        })
                        refresh_field("related_items");
                        dialog.hide()
                    }
                });
            }
            else{
                msgprint("Select Item Before Add")
            }
        }    
    },
});

filter = function(arr1, arr2) {   
    return arr1.filter(function(obj) {
    return !inList(arr2,obj.item_code)
    });
};