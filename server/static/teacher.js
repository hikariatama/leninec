function fetch_students() {
    let group = $("#group-picker").val();
    $.get(`/groups/${group}/users`, (data) => {
        $("#students").html("");
        data.users.forEach((user) => {
            if (!user.task) {
                color = "ffffff";
            } else if (user.taskstatus == "done") {
                color = "00ff00";
            } else {
                color = "0000ff";
            }
            $("#students").append(`<li class="student"><img src="https://img.icons8.com/fluency-systems-regular/48/${color}/name.png" class="student-icon" alt="user" /> ${user.fullname}</li>`)
        });
    });
}

function fetch_task() {
    let group = $("#group-picker").val();
    $.get(`/groups/${group}/task`, (data) => {
        if (data.task) {
            $("#task code").html(data.task);
            if (data.template) {
                $("#templates").val(data.template);
            } else {
                $("#templates").val("custom");
            }
            Prism.highlightAll();
        } else {
            $("#task code").html("# Для этого класса нет задания");
            Prism.highlightAll();
        }
    });
}


var editor = document.getElementById("editor")
var preview = document.getElementById("preview")
function saveCaretPosition(context) {
    var selection = window.getSelection();
    var range = selection.getRangeAt(0);
    range.setStart(context, 0);
    var len = range.toString().length;

    return function restore() {
        var pos = getTextNodeAtPosition(context, len);
        selection.removeAllRanges();
        var range = new Range();
        range.setStart(pos.node, pos.position);
        selection.addRange(range);
    }
}

function getTextNodeAtPosition(root, index) {
    const NODE_TYPE = NodeFilter.SHOW_TEXT;
    var treeWalker = document.createTreeWalker(root, NODE_TYPE, function next(elem) {
        if (index > elem.textContent.length) {
            index -= elem.textContent.length;
            return NodeFilter.FILTER_REJECT
        }
        return NodeFilter.FILTER_ACCEPT;
    });
    var c = treeWalker.nextNode();
    return {
        node: c ? c : root,
        position: index
    };
}

document.querySelector("pre").addEventListener("keydown", function (e) {
    if (e.key == "Tab") {
        e.preventDefault();
        document.execCommand("insertHTML", false, "    ");
    }
    if (!document.querySelector("code")) {
        document.querySelector("pre").innerHTML = "<code class='language-python'></code>";
    }
    if (!document.querySelector(".line-numbers-rows")) {
        document.querySelector("code").innerHTML += `<br/><span aria-hidden="true" class="line-numbers-rows" contenteditable="false"><span></span></span>`;
        Prism.highlightAll();
    }
});

document.querySelector("pre").addEventListener("input", function (e) {
    var restore = saveCaretPosition(this.querySelector("code"));
    Prism.highlightElement(this.querySelector("code"));
    restore();
});

document.querySelector("pre").addEventListener("paste", function (e) {
    e.preventDefault();
    var text = e.clipboardData.getData("text/plain");
    document.execCommand("insertHTML", false, text);
});


$("#group-picker")[0].addEventListener("change", () => {
    fetch_students();
    fetch_task();
});

$("#templates")[0].addEventListener("change", () => {
    let template = $("#templates").val();
    if (template == "custom") return;
    $.get(`/templates/${template}`, (data) => {
        $("#task code").html(data.template);
        Prism.highlightAll();
    });
});

$("#save-task").on("click", () => {
    let group = $("#group-picker").val();
    let task = $("#task code").html();
    $.post(`/groups/${group}/task`, { task: task }, (data) => {
        if (data.ok) {
            alert("Задание успешно сохранено!");
        }
        fetch_students();
        fetch_task();
    }).fail((data) => {
        alert(`Произошла ошибка при сохранении задания: ${JSON.parse(data.responseText).error}`);
    });
});

$("#delete-task").on("click", () => {
    let group = $("#group-picker").val();
    $.ajax({
        url: `/groups/${group}/task`,
        type: "DELETE",
        success: (data) => {
            if (data.ok) {
                alert("Задание успешно удалено!");
                $("#task code").html("# Для этого класса нет задания");
                Prism.highlightAll();
            } else {
                alert("Произошла ошибка при удалении задания!");
            }
            fetch_students();
            fetch_task();
        }
    });
});


fetch_students();
fetch_task();

setInterval(() => { fetch_students(); }, 3000);
