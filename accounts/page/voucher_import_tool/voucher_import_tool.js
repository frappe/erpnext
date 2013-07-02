wn.pages['voucher-import-tool'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Voucher Import Tool',
		single_column: true
	});
	
	$(wrapper).find('.layout-main').html('\
		<p class="help">Import multiple accounting entries via CSV (spreadsheet) file:</p>\
		<h3>1. Download Template</h3><br>\
		<div style="padding-left: 30px;">\
			<button class="btn btn-default btn-download-two-accounts">Download</button>\
			<p class="help">Import multiple vouchers with one debit and one credit entry</p>\
		</div>\
		<div style="padding-left: 30px;">\
			<button class="btn btn-default btn-download-multiple-accounts">Download</button>\
			<p class="help">Import multiple vouchers with multiple accounts</p>\
		</div>\
		<hr>\
		<h3>2. Upload</h3><br>\
		<div style="padding-left: 30px;">\
			<p class="help">Upload file in CSV format with UTF-8 encoding</p>\
			<div id="voucher-upload"></div>\
		</div><br>\
		<div class="working"></div>\
		<div class="well messages" style="display: none;"></div>');
		
	wn.upload.make({
		parent: $(wrapper).find("#voucher-upload"),
		args: {
			method: "accounts.page.voucher_import_tool.voucher_import_tool.upload"
		},
		callback: function(r) {
			wrapper.waiting.toggle(false);
			$(wrapper).find(".messages").toggle(true).html(
				r.join("<div style='margin:4px; border-top:1px solid #aaa;'></div>"))
		}
	});
	
	wrapper.waiting = wn.messages.waiting($(wrapper).find('.working'), 
		"Importing Vouchers...").toggle(false);

	$(wrapper).find(".btn-download-two-accounts").click(function() {
		window.location.href = wn.request.url + 
			'?cmd=accounts.page.voucher_import_tool.voucher_import_tool.get_template' + 	
			'&type=Two Accounts';
	});

	$(wrapper).find(".btn-download-multiple-accounts").click(function() {
		window.location.href = wn.request.url + 
				'?cmd=accounts.page.voucher_import_tool.voucher_import_tool.get_template' + 
				'&type=Multiple Accounts';
	});
	
	// rename button
	$(wrapper).find('#voucher-upload form input[type="submit"]')
		.click(function() {
			$(wrapper).find(".messages").toggle(false);
			wrapper.waiting.toggle(true);
		});		
}