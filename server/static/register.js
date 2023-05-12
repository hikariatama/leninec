$(document).ready(() => {
    $("#login-form").submit((event) => {
        event.preventDefault();
        if ($("#password").val() !== $("#password-verify").val()) {
            alert("Passwords do not match");
            return;
        }

        var username = $("#username").val();
        var password = $("#password").val();
        var fullname = $("#fullname").val();
        var teachercode = $("#teachercode").val();
        var group = $("#group").val();
        $.ajax({
            url: "/register",
            type: "POST",
            data: JSON.stringify({
                username: username,
                password: password,
                fullname: fullname,
                teachercode: teachercode,
                group: group,
                taskstatus: "",
                taskvars: 0,
                task: ""
            }),
            contentType: 'application/json; charset=utf-8',
            dataType: 'json',
            success: function () {
                window.location = "/";
            },
            error: function (xhr, status, error) {
                var err = JSON.parse(xhr.responseText);
                alert(err.message);
            }
        });
    });
});
