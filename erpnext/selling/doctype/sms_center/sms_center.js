// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	message: function () {
		var total_words = this.frm.doc.message.length;
		var total_msg = 1;

		if (total_words > 160) {
			total_msg = cint(total_words / 160);
			total_msg = (total_words % 160 == 0 ? total_msg : total_msg + 1);
		}

		this.frm.set_value("total_words", total_words);
		this.frm.set_value("total_messages", this.frm.doc.message ? total_msg : 0);
	}
});