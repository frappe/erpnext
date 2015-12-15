## 15.3.1.7 Benutzer auf Grundlage eines Unterdatensatzes einschränken

    // restrict certain warehouse to Material Manager
    cur_frm.cscript.custom_validate = function(doc) {
        if(user_roles.indexOf("Material Manager")==-1) {

            var restricted_in_source = wn.model.get("Stock Entry Detail",
                {parent:cur_frm.doc.name, s_warehouse:"Restricted"});

            var restricted_in_target = wn.model.get("Stock Entry Detail",
                {parent:cur_frm.doc.name, t_warehouse:"Restricted"})

            if(restricted_in_source.length || restricted_in_target.length) {
                msgprint("Only Material Manager can make entry in Restricted Warehouse");
                validated = false;
            }
        }
    }

{next}

Contributed by <A HREF="http://www.cwt-kabel.de">CWT connector & wire technology GmbH</A>

<A HREF="http://www.cwt-kabel.de"><IMG alt="logo" src="http://www.cwt-assembly.com/sites/all/images/logo.png" height=100></A>
