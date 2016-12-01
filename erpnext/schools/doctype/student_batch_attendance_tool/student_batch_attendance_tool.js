// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("schools")

frappe.ui.form.on('Student Batch Attendance Tool', {
    refresh: function(frm) {
        frm.disable_save();
        hide_field('attendance');
    },

    student_batch: function(frm) {
        if (frm.doc.student_batch && frm.doc.date) {
            frappe.call({
                method: "erpnext.schools.api.check_attendance_records_exist",
                args: {
                    "student_batch": frm.doc.student_batch,
                    "date": frm.doc.date
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint("Attendance already marked.");
                        hide_field('attendance');
                    } else {
                        frappe.call({
                            method: "erpnext.schools.api.get_student_batch_students",
                            args: {
                                "student_batch": frm.doc.student_batch
                            },
                            callback: function(r) {
                                if (r.message) {
                                    unhide_field('attendance');
                                    frm.events.get_students(frm, r.message)
                                }
                            }
                        });
                    }
                }
            });
        }
    },

    date: function(frm) {
        frm.trigger("student_batch");
    },

    get_students: function(frm, students) {
        if (!frm.students_area) {
            frm.students_area = $('<div>')
                .appendTo(frm.fields_dict.students_html.wrapper);
        }
        frm.students_editor = new schools.StudentsEditor(frm, frm.students_area, students)
    }
});


schools.StudentsEditor = Class.extend({
    init: function(frm, wrapper, students) {
        this.wrapper = wrapper;
        this.frm = frm;
        this.make(frm, students);
    },
    make: function(frm, students) {
        var me = this;

        $(this.wrapper).empty();
        var student_toolbar = $('<p>\
			<button class="btn btn-default btn-add btn-xs" style="margin-right: 5px;"></button>\
			<button class="btn btn-xs btn-default btn-remove" style="margin-right: 5px;"></button>\
			<button class="btn btn-default btn-primary btn-mark-att btn-xs"></button></p>').appendTo($(this.wrapper));

        student_toolbar.find(".btn-add")
            .html(__('Check all'))
            .on("click", function() {
                $(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
                    if (!$(check).is(":checked")) {
                        check.checked = true;
                    }
                });
            });

        student_toolbar.find(".btn-remove")
            .html(__('Uncheck all'))
            .on("click", function() {
                $(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
                    if ($(check).is(":checked")) {
                        check.checked = false;
                    }
                });
            });

        student_toolbar.find(".btn-mark-att")
            .html(__('Mark Attendence'))
            .on("click", function() {
                var students_present = [];
                var students_absent = [];
                $(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
                    if ($(check).is(":checked")) {
                        students_present.push(students[i]);
                    } else {
                        students_absent.push(students[i]);
                    }
                });
                frappe.call({
                    method: "erpnext.schools.api.mark_attendance",
                    args: {
                        "students_present": students_present,
                        "students_absent": students_absent,
                        "student_batch": frm.doc.student_batch,
                        "date": frm.doc.date
                    },
                    callback: function(r) {
                        hide_field('attendance');
                    }
                });
            });


        $.each(students, function(i, m) {
            $(repl('<div class="col-sm-6">\
				<div class="checkbox">\
				<label><input type="checkbox" class="students-check" student="%(student)s">\
				%(student)s</label>\
			</div></div>', { student: m.student_name })).appendTo(me.wrapper);
        });
    }
});