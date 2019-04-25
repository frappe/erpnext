frappe.ui.form.on('Chart of Accounts Importer', {
	onload: function (frm) {
		frm.set_value("company", "");
		frm.set_value("import_file", "");
	},
	refresh: function (frm) {
		// disable default save
		frm.disable_save();

		// make company mandatory
		frm.set_df_property('company', 'reqd', frm.doc.company ? 0 : 1);
		frm.set_df_property('import_file_section', 'hidden', frm.doc.company ? 0 : 1);
		frm.set_df_property('chart_preview', 'hidden',
			$(frm.fields_dict['chart_tree'].wrapper).html()!="" ? 0 : 1);

		// Show import button when file is successfully attached
		if (frm.page && frm.page.show_import_button) {
			create_import_button(frm);
		}

		// show download template button when company is properly selected
		if(frm.doc.company) {
			// download the csv template file
			frm.add_custom_button(__("Download template"), function () {
				let get_template_url = 'erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.download_template';
				open_url_post(frappe.request.url, { cmd: get_template_url, doctype: frm.doc.doctype });
			});
		} else {
			frm.set_value("import_file", "");
		}
	},

	import_file: function (frm) {
		if (!frm.doc.import_file) {
			frm.page.set_indicator("");
			$(frm.fields_dict['chart_tree'].wrapper).empty(); // empty wrapper on removing file
		} else {
			generate_tree_preview(frm);
			validate_csv_data(frm);
		}
	},

	company: function (frm) {
		// validate that no Gl Entry record for the company exists.
		frappe.call({
			method: "erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.validate_company",
			args: {
				company: frm.doc.company
			},
			callback: function(r) {
				if(r.message===false) {
					frm.set_value("company", "");
					frappe.throw(__("Transactions against the company already exist! "));
				} else {
					frm.trigger("refresh");
				}
			}
		});
	}
});

var validate_csv_data = function(frm) {
	frappe.call({
		method: "erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.validate_accounts",
		args: {file_name: frm.doc.import_file},
		callback: function(r) {
			if(r.message && r.message[0]===true) {
				frm.page["show_import_button"] = true;
				frm.page["total_accounts"] = r.message[1];
				frm.trigger("refresh");
			} else {
				frm.page.set_indicator(__('Resolve error and upload again.'), 'orange');
				frappe.throw(__(r.message));
			}
		}
	});
};

var create_import_button = function(frm) {
	frm.page.set_primary_action(__("Start Import"), function () {
		setup_progress_bar(frm);
		frappe.call({
			method: "erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.import_coa",
			args: {
				file_name: frm.doc.import_file,
				company: frm.doc.company
			},
			freeze: true,
			callback: function(r) {
				if(!r.exc) {
					clearInterval(frm.page["interval"]);
					frm.page.set_indicator(__('Import Successfull'), 'blue');
					frappe.hide_progress();
					create_reset_button(frm);
				}
			}
		});
	}).addClass('btn btn-primary');
};

var create_reset_button = function(frm) {
	frm.page.set_primary_action(__("Reset"), function () {
		frm.page.clear_primary_action();
		delete frm.page["show_import_button"];
		frm.reload_doc();
	}).addClass('btn btn-primary');
};

var generate_tree_preview = function(frm) {
	let parent = __('All Accounts');
	$(frm.fields_dict['chart_tree'].wrapper).empty(); // empty wrapper to load new data

	// generate tree structure based on the csv data
	new frappe.ui.Tree({
		parent: $(frm.fields_dict['chart_tree'].wrapper),
		label: parent,
		expandable: true,
		method: 'erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer.get_coa',
		args: {
			file_name: frm.doc.import_file,
			parent: parent,
			doctype: 'Chart of Accounts Importer'
		},
		onclick: function(node) {
			parent = node.value;
		}
	});
};

var setup_progress_bar = function(frm) {
	frm.page["seconds_elapsed"] = 0;
	frm.page["execution_time"] = (frm.page["total_accounts"] > 100) ? 100 : frm.page["total_accounts"];

	frm.page["interval"] = setInterval(function()  {
		frm.page["seconds_elapsed"] += 1;
		frappe.show_progress(__('Creating Accounts'), frm.page["seconds_elapsed"], frm.page["execution_time"]);
	}, 250);
};