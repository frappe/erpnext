// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// cur_frm.cscript.custom_employee = function(doc, cdt, cd) {
//     alert("Ggg");
// }
cur_frm.add_fetch("employee", "date_of_joining", "work_start_date");
frappe.ui.form.on('End of Service Award', {

    employee: function() {
        //        // cur_frm.set_value('award',"");
        //        // cur_frm.set_value('salary'," ");
        //        alert("kkk");

        frappe.call({
            "method": "get_salary",
            doc: cur_frm.doc,
            args: { "employee": cur_frm.doc.employee },
            callback: function(data) {
                if (data) {
                    cur_frm.set_value('salary', data.message);
                }
            }
        });

    },
    type_of_contract: function() {
        if (cur_frm.doc.type_of_contract == "Contractor") {
            cur_frm.set_df_property("reason", "options", "\nانتهاء مدة العقد , أو باتفاق الطرفين على إنهاء العقد\nفسخ العقد من قبل صاحب العمل\nفسخ العقد من قبل صاحب العمل لأحد الحالات الواردة في المادة (80)\nترك العامل العمل نتيجة لقوة قاهرة\nإنهاء العاملة لعقد العمل خلال ستة أشهر من عقد الزواج أو خلال ثلاثة أشهر من الوضع\nترك العامل العمل لأحد الحالات الواردة في المادة (81)\nفسخ العقد من قبل العامل أو ترك العامل العمل لغير الحالات الواردة في المادة (81)");
        } else if (cur_frm.doc.type_of_contract == "Full-time") {
            cur_frm.set_df_property("reason", "options", "\nاتفاق العامل وصاحب العمل على إنهاء العقد\nفسخ العقد من قبل صاحب العمل\nفسخ العقد من قبل صاحب العمل لأحد الحالات الواردة في المادة (80)\nترك العامل العمل نتيجة لقوة قاهرة\nإنهاء العاملة لعقد العمل خلال ستة أشهر من عقد الزواج أو خلال ثلاثة أشهر من الوضع\nترك العامل العمل لأحد الحالات الواردة في المادة (81)\nترك العامل العمل دون تقديم استقالة لغير الحالات الواردة في المادة (81)\nاستقالة العامل");
        } else {
            cur_frm.set_df_property("reason", "options", "");
        }
    },
    end_date: function() {

        start = cur_frm.doc.work_start_date;
        end = cur_frm.doc.end_date;

        if (end < start) {
            cur_frm.set_value('years', 0);
            cur_frm.set_value('months', 0);
            cur_frm.set_value('days', 0)
            frappe.msgprint("تاريخ نهاية العمل يجب أن يكون أكبر من تاريخ بداية العمل");

        } else {
            var date1 = new Date(start);
            var date2 = new Date(end);
            var timeDiff = Math.abs(date2.getTime() - date1.getTime());
            var diffDays = Math.ceil(timeDiff / (1000 * 3600 * 24));
            years = Math.floor(diffDays / 365);
            daysrem = diffDays - (years * 365);
            months = Math.floor(daysrem / 30.416);
            monthss = months
            days = Math.ceil(daysrem - (months * 30.416));

            cur_frm.set_value('years', years);
            cur_frm.set_value('months', monthss);
            cur_frm.set_value('days', days);

        };




    },


    find: function(frm) {

        cur_frm.set_value('award', " ");

        frappe.call({
            "method": "get_salary",
            doc: cur_frm.doc,
            args: { "employee": cur_frm.doc.employee },
            callback: function(data) {
                if (data) {
                    cur_frm.set_value('salary', data.message);
                } else {
                    cur_frm.set_value('award', "");

                }
            }
        });


        start = cur_frm.doc.work_start_date;
        end = cur_frm.doc.end_date;

        if (end < start) {
            frappe.msgprint("تاريخ نهاية العمل يجب أن يكون أكبر من تاريخ بداية العمل");
        } else {
            var date1 = new Date(start);
            var date2 = new Date(end);
            var timeDiff = Math.abs(date2.getTime() - date1.getTime());
            var diffDays = Math.ceil(timeDiff / (1000 * 3600 * 24));
            years = Math.floor(diffDays / 365);
            daysrem = diffDays - (years * 365);
            months = Math.floor(daysrem / 30.416);
            monthss = months
            days = Math.ceil(daysrem - (months * 30.416));

            cur_frm.set_value('years', years);
            cur_frm.set_value('months', monthss);
            cur_frm.set_value('days', days);

        };



        var salary = cur_frm.doc.salary;
        var years = parseInt(cur_frm.doc.years) + (parseInt(cur_frm.doc.months) / 12) + (parseInt(cur_frm.doc.days) / 365);
        var reason = cur_frm.doc.reason;

        if (!reason) {
            frappe.msgprint("برجاء اختيار سبب انتهاء العلاقة العمالية");
            cur_frm.set_value('award', "");
        } else {


            if (cur_frm.doc.type_of_contract == "Contractor") {
                if (cur_frm.doc.reason == "فسخ العقد من قبل صاحب العمل لأحد الحالات الواردة في المادة (80)" || cur_frm.doc.reason == "فسخ العقد من قبل العامل أو ترك العامل العمل لغير الحالات الواردة في المادة (81)") {
                    cur_frm.set_value('award', "لا يستحق العامل مكافأة نهاية خدمة");
                } else {
                    cur_frm.set_value('award', "");

                    // cur_frm.set_value('award', "");
                    var firstPeriod, secondPeriod = 0;
                    // set periods
                    if (years > 5) {
                        firstPeriod = 5;
                        secondPeriod = years - 5;
                    } else {
                        firstPeriod = years;
                    }
                    // calculate
                    result = (firstPeriod * cur_frm.doc.salary * 0.5) + (secondPeriod * cur_frm.doc.salary);
                    cur_frm.set_value('award', (result).toFixed(2));

                }
            } else if (cur_frm.doc.type_of_contract == "Full-time") {


                if (cur_frm.doc.reason == "فسخ العقد من قبل صاحب العمل لأحد الحالات الواردة في المادة (80)" || cur_frm.doc.reason == "ترك العامل العمل دون تقديم استقالة لغير الحالات الواردة في المادة (81)") {
                    cur_frm.set_value('award', "لا يستحق العامل مكافأة نهاية خدمة");
                } else if (cur_frm.doc.reason == "استقالة العامل") {
                    if (years < 2) {
                        result = 'لا يستحق العامل مكافأة نهاية خدمة';
                    } else if (years <= 5) {
                        result = (1 / 6) * cur_frm.doc.salary * years;
                    } else if (years <= 10) {
                        result = ((1 / 3) * cur_frm.doc.salary * 5) + ((2 / 3) * cur_frm.doc.salary * (years - 5));
                    } else {
                        result = (0.5 * cur_frm.doc.salary * 5) + (cur_frm.doc.salary * (years - 5));
                    }
                    cur_frm.set_value('award', (result).toFixed(2));

                } else {
                    if (years <= 5) {
                        result = 0.5 * cur_frm.doc.salary * years;
                    } else {
                        result = (0.5 * cur_frm.doc.salary * 5) + (cur_frm.doc.salary * (years - 5));
                    }
                    cur_frm.set_value('award', (result).toFixed(2));
                }


            }
        };

    }


});
