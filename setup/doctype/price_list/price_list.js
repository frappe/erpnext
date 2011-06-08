
//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(doc.__islocal) {
		set_field_options('Price Help', ''); return;
	}
	if(!doc.file_list) {
		set_field_options('Price Help', '<div class="help_box">To upload a price list, please attach a (.csv) file with 3 columns - <b>Item Code, Price and Currency</b> (no headings necessary). See attachments box in the right column</div>')
	} else {
		set_field_options('Price Help', '<div class="help_box">To update prices from the attachment, please click on "Update Prices"</div>')
	}
}

cur_frm.cscript['Clear Prices'] = function(doc, cdt, cdn) {
	if(confirm("This action will clear all rates for '"+ doc.name +"' from the Item Master and cannot be un-done. Are you sure you want to continue?")) {
		$c_obj([doc], 'clear_prices', '', function(r, rt) { });
	}
}
