{% extends "page.html" %}

{% block javascript %}
{{ super() }}
// Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)
// 
// MIT License (MIT)
// 
// Permission is hereby granted, free of charge, to any person obtaining a 
// copy of this software and associated documentation files (the "Software"), 
// to deal in the Software without restriction, including without limitation 
// the rights to use, copy, modify, merge, publish, distribute, sublicense, 
// and/or sell copies of the Software, and to permit persons to whom the 
// Software is furnished to do so, subject to the following conditions:
// 
// The above copyright notice and this permission notice shall be included in 
// all copies or substantial portions of the Software.
// 
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
// INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
// PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
// HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
// CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
// OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// 

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

{% endblock %}