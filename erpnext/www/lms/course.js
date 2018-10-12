function submitQuiz() {
    formData = new FormData(quiz);
    var form_object = {};
    formData.forEach(function (value, key) {
        form_object[key] = value;
    });
    frappe.call({
        method: "erpnext.education.utils.evaluate_quiz",
        args: {
            "quiz_response": form_object,
            "content": $('#content-holder').data('content'),
            "course": $('#content-holder').data('course'),
            "program": $('#content-holder').data('program')
        },
        async: false,
        callback: function (r) {
            if (r) {
                $("input[type=radio]").attr('disabled', true);
                $("#quiz-actions").attr('hidden', true);
                $("#post-quiz-actions").attr('hidden', false);
                $("#result").html(r.message);
            }
        }
    });
}

function addActivity() {
    frappe.call({
        method: "erpnext.education.utils.add_activity",
        args: {
            "content_type": $('#content-holder').data('type'),
            "content": $('#content-holder').data('content'),
            "course": $('#content-holder').data('course'),
            "program": $('#content-holder').data('program'),
        }
    })
}