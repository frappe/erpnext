// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exit Re Entry Application', {
    refresh: function(frm) {

        showEditor(frm, "exit_re_entry_family_members_editor",
            __("Exit ReEntry Family Members"),
            	"family_members_html", {
                "method": "get_family_exit_re_entry",
                "self_field": "has_self_exit_re_entry",
                "dt_field": "family_members"
            });
    }
});



function showEditor(frm, editor_name, title, html_filed, editor_opt) {
    if (!cur_frm[editor_name]) {
        var $wrapper = $('<div>')
            .append("<h3>" + __(title) + "</h3>")
            .append("<div class='data-container'></div>")
            .appendTo(cur_frm.fields_dict[html_filed].wrapper)
            .find(".data-container")
            //cur_frm.exit_re_entry_family_members_editor = new frappe.ExitReEntryFamilyMembersEditor($exit_re_entry_family_members_area, frm.employee);
        cur_frm[editor_name] = new frappe.FamilyMembersEditor(frm, editor_opt.method, editor_opt.self_field, editor_opt.dt_field, $wrapper, editor_name);

    } else {
        cur_frm[editor_name].show();
    }

}


frappe.FamilyMembersEditor = Class.extend({
    init: function(frm, method, self_field, dt_field, wrapper, editor) {
        // alert(11);
        var me = this;
        this.frm = frm;
        this.dt_field = dt_field;
        this.self_field = self_field;
        this.wrapper = wrapper;
        this.member_map = [];
        this.employee = cur_frm.doc.employee;
        //alert(this.employee)
        $(wrapper).html('<div class="help">' + __("Loading") + '...</div>')
       if (this.employee){ 
        return frappe.call({
            method: 'erpnext.hr.doctype.leave_application.leave_application.get_family_members',
            args: {
                employee_name: this.employee
            },
            callback: function(r) {
                
                me.members = r.message;

                me.show_members();

                // refresh call could've already happened
                // when all role checkboxes weren't created
                if (cur_frm.doc) {
                    cur_frm[editor].show();
                }
            }
        });
	}
    },
    show_members: function() {
        var me = this;
        $(this.wrapper).empty();
        var member_toolbar = $('<p><button class="btn btn-default btn-add btn-sm" style="margin-right: 5px;"></button>\
          <button class="btn btn-sm btn-default btn-remove"></button></p>').appendTo($(this.wrapper));

        member_toolbar.find(".btn-add")
          .html(__('Add all family'))
          .on("click", function() {
          $(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
            if(!$(check).is(":checked")) {
              check.checked = true;
            }
          });
        });

        member_toolbar.find(".btn-remove")
          .html(__('Clear all family'))
          .on("click", function() {
          $(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
            if($(check).is(":checked")) {
              check.checked = false;
            }
          });
        });
        var employee_name101 = me.frm.employee_name;
        console.log(cur_frm.doc.employee_name);
        me.display_member($(me.wrapper), cur_frm.doc.employee, employee_name101);
        $.each(this.members, function(i, member) {
            me.member_map[member.family_member_name] = member;
            var member_display = (member.name1 || " ") + " - "  + " - " + (member.Passport || ""); 

            me.display_member($(me.wrapper), member.name1, member_display);
        });



        $(this.wrapper).find('input[type="checkbox"]').change(function() {
            debugger;
            var index = $(me.wrapper).find('.family-member').index($(this).parent());
            if (index == 0) {
                cur_frm.set_value(me.self_field, $(this).prop("checked"));
                return true;
            }
            me.set_members_in_table();
            cur_frm.dirty();
        });
    },
    display_member: function($wrapper, value, display) {
        $wrapper.append('<div class="family-member" data-family-member="' + value + '"><input type="checkbox" style="margin-top:0px;"><span href="#" class="grey">' + display + '</span></div>');
    },
    show: function() {
        var me = this;

        // uncheck all roles
        $(this.wrapper).find('input[type="checkbox"]')
            .each(function(i, checkbox) { checkbox.checked = false; });

        // set user roles as checked
        $.each((cur_frm.doc[me.dt_field] || []), function(i, member) {
            var checkbox = $(me.wrapper)
                .find('[data-family-member="' + member.name1 + '"] input[type="checkbox"]').get(0);
            if (checkbox) checkbox.checked = true;
        });

        $(this.wrapper).find('input[type="checkbox"]:eq(0)').prop("checked", (cur_frm.doc[me.self_field] == 1));


    },
    set_members_in_table: function() {
        var me = this;
        var opts = this.get_members();
        var existing_members_map = {};
        var existing_members_list = [];

        $.each((cur_frm.doc[me.dt_field] || []), function(i, member) {
            existing_members_map[member.name1] = member.name;
            existing_members_list.push(member.name1);

            console.log("========__=============")
            console.log(existing_members_map)
            console.log(existing_members_list)
            console.log("=====================")
        });

        // remove unchecked members
        $.each(opts.unchecked_members, function(i, member) {
            debugger;
            if (existing_members_list.indexOf(member) != -1) {

                frappe.model.clear_doc("Family Info", existing_members_map[member]);

            }
        });

        // add new roles that are checked
        $.each(opts.checked_members, function(i, member) {
            if (existing_members_list.indexOf(member) == -1) {
                member_doc = me.member_map[member];
                var family_member = frappe.model.add_child(cur_frm.doc, "Family Info", me.dt_field);
                family_member.relation = member_doc.relation;
                family_member.name1 = member_doc.name1;
                family_member.birthdate = member_doc.birthdate;
                family_member.passport = member_doc.passport;
                
            }
        });

        refresh_field(me.dt_field);
    },
    get_members: function() {
        var checked_members = [];
        var unchecked_members = [];
        $(this.wrapper).find('[data-family-member]:gt(0)').each(function(index, value) {
            var checked = $(this).find('input[type="checkbox"]:checked').prop("checked");
            if (checked) {
                checked_members.push($(this).attr('data-family-member'));
            } else {
                unchecked_members.push($(this).attr('data-family-member'));
            }
        });
        console.log("=========================")
        console.log("checked_members")
        console.log(checked_members)
        console.log("=========================")
        console.log("unchecked_members")
        console.log(unchecked_members)
        console.log("=========================")
        return {
            checked_members: checked_members,
            unchecked_members: unchecked_members
        }
    }
});

