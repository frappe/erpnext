// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

wn.provide('erpnext.login');

wn.pages["{{ name }}"].onload = function(wrapper) {
	wrapper.appframe = new wn.ui.AppFrame($(wrapper).find('.appframe-area'));
	wrapper.appframe.title('Login');
	wrapper.appframe.$w.find('.close').toggle(false);

	var lw = $i('login_wrapper');
	$bs(lw, '1px 1px 3px #888');

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
}

// Login Callback
erpnext.login.onLoginReply = function(r, rtext) {
	$('#login_btn').done_working();
    if(r.message=="Logged In"){
        window.location.href='app.html' + (get_url_arg('page') ? ('?page='+get_url_arg('page')) : '');
    } else {
        $i('login_message').innerHTML = '<span style="color: RED;">'+(r.message)+'</span>';
        //if(r.exc)alert(r.exc);
    }
}


// Login
erpnext.login.doLogin = function(){

    var args = {};
    args['usr']=$i("login_id").value;
    args['pwd']=$i("password").value;
    if($i('remember_me').checked) 
      args['remember_me'] = 1;

	$('#login_btn').set_working();
	
    $c("login", args, erpnext.login.onLoginReply);

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