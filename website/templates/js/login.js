
wn.provide('erpnext.login');

$(document).ready(function(wrapper) {
	$('#login_btn').click(erpnext.login.doLogin)
		
	$('#password').keypress(function(ev){
		if(ev.which==13 && $('#password').val()) {
			$('form').submit(function() {
				erpnext.login.doLogin();
				return false;
			});
		}
	});
	$(document).trigger('login_rendered');
})

// Login
erpnext.login.doLogin = function(){

    var args = {};
    args['usr']=$("#login_id").val();
    args['pwd']=$("#password").val();

	if(!args.usr || !args.pwd) {
		msgprint("Sorry, you can't login if you don't enter both the email id and password.")
	}

	$('#login_btn').set_working();
	$('#login_message').empty();
	
    $c("login", args, function(r, rtext) {
		$('#login_btn').done_working();
	    if(r.message=="Logged In"){
	        window.location.href='app.html' + (get_url_arg('page') 
				? ('?page='+get_url_arg('page')) : '');
	    } else {
	        $i('login_message').innerHTML = '<span style="color: RED;">'
				+(r.message)+'</span>';
	    }
	});

	return false;
}


erpnext.login.show_forgot_password = function(){
    // create dialog
	var d = new wn.ui.Dialog({
		title:"Forgot Password",
		fields: [
			{'label':'Email Id', 'fieldname':'email_id', 'fieldtype':'Data', 'reqd':true},
			{'label':'Email Me A New Password', 'fieldname':'run', 'fieldtype':'Button'}
		]
	});

	$(d.fields_dict.run.input).click(function() {
		var values = d.get_values();
		if(!values) return;
		wn.call({
			method:'reset_password',
			args: { user: values.email_id },
			callback: function() {
				d.hide();
			}
		})
	})
	d.show();
}