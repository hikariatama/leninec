$(document).ready(() => {
    $("#login-form").submit((event) => {
        event.preventDefault();
        var username = $("#username").val();
        var password = $("#password").val();
        $.ajax({
            url: "/login",
            type: "POST",
            data: JSON.stringify({
                username: username,
                password: password
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
