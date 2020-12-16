// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Pricing Rule', {
	setup: function(frm) {
		frm.fields_dict["for_price_list"].get_query = function(doc){
			return {
				filters: {
					'selling': doc.selling,
					'buying': doc.buying,
					'currency': doc.currency
				}
			};
		};

		['items', 'item_groups', 'brands'].forEach(d => {
			frm.fields_dict[d].grid.get_field('uom').get_query = function(doc, cdt, cdn){
				var row = locals[cdt][cdn];
				return {
					query:"erpnext.accounts.doctype.pricing_rule.pricing_rule.get_item_uoms",
					filters: {'value': row[frappe.scrub(doc.apply_on)], apply_on: doc.apply_on}
				}
			};
		})
	},

	onload: function(frm) {
		if(frm.doc.__islocal && !frm.doc.applicable_for && (frm.doc.customer || frm.doc.supplier)) {
			if(frm.doc.customer) {
				frm.doc.applicable_for = "Customer";
				frm.doc.selling = 1
			} else {
				frm.doc.applicable_for = "Supplier";
				frm.doc.buying = 1
			}
		}
	},

	refresh: function(frm) {
		var help_content =
			`<table class="table table-bordered" style="background-color: #f9f9f9;">
				<tr><td>
					<h4>
						<i class="fa fa-hand-right"></i>
						{{__('Notes')}}
					</h4>
					<ul>
						<li>
							{{__("Pricing Rule is made to overwrite Price List / define discount percentage, based on some criteria.")}}
						</li>
						<li>
							{{__("If selected Pricing Rule is made for 'Rate', it will overwrite Price List. Pricing Rule rate is the final rate, so no further discount should be applied. Hence, in transactions like Sales Order, Purchase Order etc, it will be fetched in 'Rate' field, rather than 'Price List Rate' field.")}}
						</li>
						<li>
							{{__('Discount Percentage can be applied either against a Price List or for all Price List.')}}
						</li>
						<li>
							{{__('To not apply Pricing Rule in a particular transaction, all applicable Pricing Rules should be disabled.')}}
						</li>
					</ul>
				</td></tr>
				<tr><td>
					<h4><i class="fa fa-question-sign"></i>
						{{__('How Pricing Rule is applied?')}}
					</h4>
					<ol>
						<li>
							{{__("Pricing Rule is first selected based on 'Apply On' field, which can be Item, Item Group or Brand.")}}
						</li>
						<li>
							{{__("Then Pricing Rules are filtered out based on Customer, Customer Group, Territory, Supplier, Supplier Type, Campaign, Sales Partner etc.")}}
						</li>
						<li>
							{{__('Pricing Rules are further filtered based on quantity.')}}
						</li>
						<li>
							{{__('If two or more Pricing Rules are found based on the above conditions, Priority is applied. Priority is a number between 0 to 20 while default value is zero (blank). Higher number means it will take precedence if there are multiple Pricing Rules with same conditions.')}}
						</li>
						<li>
							{{__('Even if there are multiple Pricing Rules with highest priority, then following internal priorities are applied:')}}
							<ul>
								<li>
									{{__('Item Code > Item Group > Brand')}}
								</li>
								<li>
									{{__('Customer > Customer Group > Territory')}}
								</li>
								<li>
									{{__('Supplier > Supplier Type')}}
								</li>
							</ul>
						</li>
						<li>
							{{__('If multiple Pricing Rules continue to prevail, users are asked to set Priority manually to resolve conflict.')}}
						</li>
					</ol>
				</td></tr>
			</table>`;

		frm.set_df_property('pricing_rule_help', 'options', help_content);
		frm.events.set_options_for_applicable_for(frm);
		frm.trigger("toggle_reqd_apply_on");
	},

	apply_on: function(frm) {
		frm.trigger("toggle_reqd_apply_on");
	},

	toggle_reqd_apply_on: function(frm) {
		const fields = {
			'Item Code': 'items',
			'Item Group': 'item_groups',
			'Brand': 'brands'
		}

		for (var key in fields) {
			frm.toggle_reqd(fields[key],
				frm.doc.apply_on === key ? 1 : 0);
		}
	},

	rate_or_discount: function(frm) {
		if(frm.doc.rate_or_discount == 'Rate') {
			frm.set_value('for_price_list', "");
		}
	},

	selling: function(frm) {
		frm.events.set_options_for_applicable_for(frm);
	},

	buying: function(frm) {
		frm.events.set_options_for_applicable_for(frm);
	},

	//Dynamically change the description based on type of margin
	margin_type: function(frm){
		frm.set_df_property('margin_rate_or_amount', 'description', frm.doc.margin_type=='Percentage'?'In Percentage %':'In Amount');
	},

	set_options_for_applicable_for: function(frm) {
		var options = [""];
		var applicable_for = frm.doc.applicable_for;

		if(frm.doc.selling) {
			options = $.merge(options, ["Customer", "Customer Group", "Territory", "Sales Partner", "Campaign"]);
		}
		if(frm.doc.buying) {
			$.merge(options, ["Supplier", "Supplier Group"]);
		}

		set_field_options("applicable_for", options.join("\n"));

		if(!in_list(options, applicable_for)) applicable_for = null;
		frm.set_value("applicable_for", applicable_for);
	}
});
