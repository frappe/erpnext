## 15.3.1.5 Abbruchrechte einschränken

Fügen Sie dem Ereignis custom_before_cancel eine Steuerungsfunktion hinzu:

    cur_frm.cscript.custom_before_cancel = function(doc) {
        if (user_roles.indexOf("Accounts User")!=-1 && user_roles.indexOf("Accounts Manager")==-1
                && user_roles.indexOf("System Manager")==-1) {
            if (flt(doc.grand_total) > 10000) {
                msgprint("You can not cancel this transaction, because grand total \
                    is greater than 10000");
                validated = false;
            }
        }
    }


{next}

Contributed by <A HREF="http://www.cwt-kabel.de">CWT connector & wire technology GmbH</A>

<A HREF="http://www.cwt-kabel.de"><IMG alt="logo" src="http://www.cwt-assembly.com/sites/all/images/logo.png" height=100></A>
