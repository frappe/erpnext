---
{
	"_label": "Restrict Purpose of Stock Entry"
}
---

	cur_frm.cscript.custom_validate = function(doc) {
	    if(user=="user1@example.com" && doc.purpose!="Material Receipt") {
	        msgprint("You are only allowed Material Receipt");
	        validated = false;
	    }
	}