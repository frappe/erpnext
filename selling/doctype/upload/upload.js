cur_frm.cscript.refresh = function(doc) {
	cur_frm.cscript.setup_upload();	
}

cur_frm.cscript.nam= function() {
	cur_frm.cscript.setup_upload();
	cur_frm.doc.lis11=''
	refresh_field("lis11");

}
cur_frm.cscript.lis11= function() {
        cur_frm.cscript.setup_upload();
       cur_frm.doc.nam=''
        refresh_field("nam");

}

cur_frm.cscript.setup_upload = function() {
	//alert(cur_frm.doc.nam);
	var me = this;
	var $wrapper = $(cur_frm.fields_dict.upload_html.wrapper).empty()
		.html("<hr><div >" +
			wn._("")
			+ "</div>");
	var $log = $(cur_frm.fields_dict.rename_log.wrapper).empty();
 /*       wn.upload.make({
                parent: $wrapper,
                args: {
                        method: 'selling.doctype.upload.upload.upload',
                        nam: cur_frm.doc.nam
                },
                sample_url: "e.g. http://example.com/somefile.csv",
                callback: function(r) {
                        alert(r);
                }
        });
*/
	// upload
        var nam1,nam2; 
	wn.upload.make({
		parent: $wrapper,
		args: {
			method: 'selling.doctype.upload.upload.upload',
			nam1:cur_frm.doc.lis11,
			nam2:cur_frm.doc.nam
		},
		sample_url: "e.g. http://example.com/somefile.csv",
		callback: function(r){	
			alert(r);
			cur_frm.doc.lis11=''
        refresh_field("lis11");
        cur_frm.doc.nam=''
        refresh_field("nam");		
       cur_frm.doc.cus=''
        refresh_field("cus");

		}
	});
	
	// rename button
	$wrapper.find('form input[type="submit"]')
		.click(function() {
			$log.html("Working...");
		})
		.addClass("btn-info")
		.attr('value', 'Upload and Rename')
/*	wn.upload.make({
                parent: $wrapper,
                args: {
                        method: 'selling.doctype.upload.upload.upload',
                        nam: cur_frm.doc.nam
                },
                sample_url: "e.g. http://example.com/somefile.csv",
                callback: function(r) {
                        alert(r);
                }
        });
*/
}
