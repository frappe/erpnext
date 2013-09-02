// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc) {
	return wn.call({
		method:"utilities.doctype.rename_tool.rename_tool.get_doctypes",
		callback: function(r) {
			cur_frm.set_df_property("select_doctype", "options", r.message);
			cur_frm.cscript.setup_upload();
		}
	});	
}

cur_frm.cscript.select_doctype = function() {
	cur_frm.cscript.setup_upload();
}

cur_frm.cscript.setup_upload = function() {
	var me = this;
	var $wrapper = $(cur_frm.fields_dict.upload_html.wrapper).empty()
		.html("<hr><div class='alert alert-warning'>" +
			wn._("Upload a .csv file with two columns: the old name and the new name. Max 500 rows.")
			+ "</div>");
	var $log = $(cur_frm.fields_dict.rename_log.wrapper).empty();

	// upload
	wn.upload.make({
		parent: $wrapper,
		args: {
			method: 'utilities.doctype.rename_tool.rename_tool.upload',
			select_doctype: cur_frm.doc.select_doctype
		},
		sample_url: "e.g. http://example.com/somefile.csv",
		callback: function(fid, filename, r) {
			$log.empty().html("<hr>");
			$.each(r.message, function(i, v) {
				$("<div>" + v + "</div>").appendTo($log);
			});
		}
	});
	
	// rename button
	$wrapper.find('form input[type="submit"]')
		.click(function() {
			$log.html("Working...");
		})
		.addClass("btn-info")
		.attr('value', 'Upload and Rename')
	
}