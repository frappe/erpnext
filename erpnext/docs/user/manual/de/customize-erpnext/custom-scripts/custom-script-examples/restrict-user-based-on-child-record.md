# Benutzer auf Grundlage eines Unterdatensatzes einschränken
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

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
