// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Pricing Rule", "refresh", function(frm) {
	var help_content =
		`<table class="table table-bordered" style="background-color: #f9f9f9;">
			<tr><td>
				<h4>
					<i class="fa fa-hand-right"></i>
					${__('Notes')}
				</h4>
				<ul>
					<li>
						${__("Pricing Rule is made to overwrite Price List / define discount percentage, based on some criteria.")}
					</li>
					<li>
						${__("If selected Pricing Rule is made for 'Price', it will overwrite Price List. Pricing Rule price is the final price, so no further discount should be applied. Hence, in transactions like Sales Order, Purchase Order etc, it will be fetched in 'Rate' field, rather than 'Price List Rate' field.")}
					</li>
					<li>
						${__('Discount Percentage can be applied either against a Price List or for all Price List.')}
					</li>
					<li>
						${__('To not apply Pricing Rule in a particular transaction, all applicable Pricing Rules should be disabled.')}
					</li>
				</ul>
			</td></tr>
			<tr><td>
				<h4><i class="fa fa-question-sign"></i>
					${__('How Pricing Rule is applied?')}
				</h4>
				<ol>
					<li>
						${__("Pricing Rule is first selected based on 'Apply On' field, which can be Item, Item Group or Brand.")}
					</li>
					<li>
						${__("Then Pricing Rules are filtered out based on Customer, Customer Group, Territory, Supplier, Supplier Type, Campaign, Sales Partner etc.")}
					</li>
					<li>
						${__('Pricing Rules are further filtered based on quantity.')}
					</li>
					<li>
						${__('If two or more Pricing Rules are found based on the above conditions, Priority is applied. Priority is a number between 0 to 20 while default value is zero (blank). Higher number means it will take precedence if there are multiple Pricing Rules with same conditions.')}
					</li>
					<li>
						${__('Even if there are multiple Pricing Rules with highest priority, then following internal priorities are applied:')}
						<ul>
							<li>
								${__('Item Code > Item Group > Brand')}
							</li>
							<li>
								${__('Customer > Customer Group > Territory')}
							</li>
							<li>
								${__('Supplier > Supplier Type')}
							</li>
						</ul>
					</li>
					<li>
						${__('If multiple Pricing Rules continue to prevail, users are asked to set Priority manually to resolve conflict.')}
					</li>
				</ol>
			</td></tr>
		</table>`;

	set_field_options("pricing_rule_help", help_content);

	cur_frm.cscript.set_options_for_applicable_for();
});

cur_frm.cscript.set_options_for_applicable_for = function() {
	var options = [""];
	var applicable_for = cur_frm.doc.applicable_for;

	if(cur_frm.doc.selling) {
		options = $.merge(options, ["Customer", "Customer Group", "Territory", "Sales Partner", "Campaign"]);
	}
	if(cur_frm.doc.buying) {
		$.merge(options, ["Supplier", "Supplier Type"]);
	}

	set_field_options("applicable_for", options.join("\n"));

	if(!in_list(options, applicable_for)) applicable_for = null;
	cur_frm.set_value("applicable_for", applicable_for)
}

cur_frm.cscript.selling = function() {
	cur_frm.cscript.set_options_for_applicable_for();
}

cur_frm.cscript.buying = function() {
	cur_frm.cscript.set_options_for_applicable_for();
}

//Dynamically change the description based on type of margin
cur_frm.cscript.margin_type = function(doc){
	cur_frm.set_df_property('margin_rate_or_amount', 'description', doc.margin_type=='Percentage'?'In Percentage %':'In Amount')
}

frappe.ui.form.on('Pricing Rule', 'price_or_discount', function(frm){
	if(frm.doc.price_or_discount == 'Price') {
		frm.set_value('for_price_list', "")
	}
})

frappe.ui.form.on('Pricing Rule', {
	setup: function(frm) {
		frm.fields_dict["for_price_list"].get_query = function(doc){
			return {
				filters: {
					'selling': doc.selling,
					'buying': doc.buying
				}
			}
		}
	}
})
