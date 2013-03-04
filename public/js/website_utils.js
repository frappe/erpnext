
var erpnext = {};

// subject, sender, description
erpnext.send_message = function(opts) {
	if(opts.btn) {
		$(opts.btn).attr("disabled", "disabled");
	}
		
	$.ajax({
		type: "POST",
		url: "server.py",
		data: {
			cmd: "website.helpers.contact.send_message",
			subject: opts.subject,
			sender: opts.sender,
			status: opts.status,
			_type: "POST",
			message: typeof opts.message == "string"
				? opts.message
				: JSON.stringify(opts.message)
		},
		dataType: "json",
		success: function(data) {
			if(opts.btn) {
				$(opts.btn).attr("disabled", false);
			}
			if(opts.callback) 
				opts.callback(data);
		}
	});
}

function valid_email(id) { 
	if(id.toLowerCase().search("[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")==-1) 
		return 0; else return 1; }

var validate_email = valid_email;

function get_url_arg(name) {
	name = name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");
	var regexS = "[\\?&]"+name+"=([^&#]*)";
	var regex = new RegExp( regexS );
	var results = regex.exec( window.location.href );
	if(results == null)
		return "";
	else
		return decodeURIComponent(results[1]);		
}

function repl(s, dict) {
	if(s==null)return '';
	for(key in dict) {
		s = s.split("%("+key+")s").join(dict[key]);
	}
	return s;
}
