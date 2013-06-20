wn.pages['upload-tool'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Upload Tool',
		single_column: true
	});

	$(wrapper).find('.layout-main').html('\
                <h3>Bulk Contacts Upload </h3><br>\
                <div style="padding-left: 30px;">\
                        <p class="help">Upload file in CSV format with UTF-8 encoding</p>\
			<input id="name_contact" type="text" />\
                        <div id="voucher-upload"></div>\
                </div><br>\
                <div class="working"></div>\
                <div class="well messages" style="display: none;"></div>');
	var x='web'; 
	//x=document.getElementById('name_contact').value;   
	
	
	
        wn.upload.make({
                parent: $(wrapper).find("#voucher-upload"),
                args: {
                       method: 'selling.page.upload_tool.upload_tool.upload',select_doctype: 'a'
                },
                callback: function(r) {
                        wrapper.waiting.toggle(false);
                        alert(r);
                        /*$(wrapper).find(".messages").toggle(true).html(
                                r.join("<div style='margin:4px; border-top:1px solid #aaa;'></div>"))*/
                }
        });
	
	

	/*wn.call({
		
		method: 'selling.page.upload_tool.upload_tool.upload1',
		args: { fieldname: x},
		callback: function(r) {
			//alert(r.message);
			var insert_after_val = null;
			doc = locals[doc.doctype][doc.name];
			
			if(doc.su1) {
				
			}
			insert_after_val = doc.su1;
			set_field_options('su1', r.message, insert_after_val);
		}
	});*/

    wrapper.waiting = wn.messages.waiting($(wrapper).find('.working'),
                "Importing Vouchers...").toggle(false);

        $(wrapper).find(".btn-download-two-accounts").click(function() {
		alert("hi");
                window.location.href = wn.request.url +
                        '?cmd=selling.page.customer_import_tool.customer_import_tool.get_template' +
                        '&type=Two Accounts';
        });
        // rename button
        $(wrapper).find('#voucher-upload form input[type="submit"]')
                .click(function() {
			
                        $(wrapper).find(".messages").toggle(false);
                        wrapper.waiting.toggle(true);
                });
					
}
