frappe.pages['pos'].onload = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Start POS',
		single_column: true
	});

	wrapper.body.html('<div class="text-center" style="margin: 40px">\
		<p>' + __("Select type of transaction") + '</p>\
		<p class="select-type" style="margin: auto; max-width: 300px; margin-bottom: 15px;"></p>\
		<p class="alert alert-warning pos-setting-message hide">'
			+ __("Please setup your POS Preferences")
			+ ': <a class="btn btn-default" onclick="newdoc(\'POS Setting\')">'
			+ __("Make new POS Setting") + '</a></p>\
		<p><button class="btn btn-primary">' + __("Start") + '</button></p>\
	</div>');

	var pos_type = frappe.ui.form.make_control({
		parent: wrapper.body.find(".select-type"),
		df: {
			fieldtype: "Select",
			options: [
				{label: __("Billing (Sales Invoice)"), value:"Sales Invoice"},
				{value:"Sales Order"},
				{value:"Delivery Note"},
				{value:"Quotation"},
				{value:"Purchase Order"},
				{value:"Purchase Receipt"},
				{value:"Purchase Invoice"},
			],
			fieldname: "pos_type"
		},
		only_input: true
	});

	pos_type.refresh();

	wrapper.body.find(".btn-primary").on("click", function() {
		erpnext.open_as_pos = true;
		new_doc(pos_type.get_value());
	});

	$.ajax({
		url: "/api/resource/POS Setting",
		success: function(data) {
			if(!data.data.length) {
				wrapper.body.find(".pos-setting-message").removeClass('hide');
			}
		}
	})

}
