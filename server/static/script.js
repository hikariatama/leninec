const SOCKET_URL = `wss://${window.location.host}/ws`;

window.onload = () => {
    if (localStorage.getItem('speed')) {
        document.querySelector('.wrapper-speed select').value = localStorage.getItem('speed');
        document.querySelector(".pointer").style.transitionDuration = { "1": ".2", "2": ".1", "5": ".04", "0": "0" }[localStorage.getItem("speed")] + "s";
    }
    if (localStorage.getItem('code')) {
        document.querySelector('.code-window code').innerHTML = localStorage.getItem('code');
    }
    Prism.highlightAll();
}

var lang = {
    'property': {
        pattern: /(^|[^\\])"(?:\\.|[^\\"\r\n])*"(?=\s*:)/,
        lookbehind: true,
        greedy: true
    },
    'string': {
        pattern: /(^|[^\\])"(?:\\.|[^\\"\r\n])*"(?!\s*:)/,
        lookbehind: true,
        greedy: true
    },
    'comment': {
        pattern: /\/\/.*|\/\*[\s\S]*?(?:\*\/|$)/,
        greedy: true
    },
    'number': /-?\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b/i,
    'punctuation': /[{}[\],]/,
    'label': /(?:\s)([a-zA-Z_][a-zA-Z0-9_]*:)/,
    'instruction': /(push|pop|add|sub|mul|div|mov|jmp|je|jl|jg)/,
    'define': /(#define\s.*?\s|#enddefine|\s\w+?!)/,
}

Prism.languages['leninec'] = lang;

function update_reg(register, value) {
    document.querySelector(`.registers .register:nth-child(${register}) .value`).innerHTML = value;
}

function stack_push(value) {
    var index = document.querySelectorAll(".stack-entry").length;
    document.querySelector(".stack").innerHTML += `<div class="stack-entry"><div class="index">${index}</div><div class="value">${value}</div></div>`;
}

function stack_pop() {
    document.querySelector(".stack-entry:nth-last-child(1)").remove();
}

function update_pos(pos) {
    document.querySelector(".pointer").style.marginTop = `${(pos + 1) * 19.5}px`;
}

function update_res(result) {
    document.querySelector(".result").innerHTML = `leninec@vm:# $ ${result}`;
}

function finish() {
    document.querySelector(".run-btn").classList.remove("disabled");
    document.querySelector(".run-btn").innerHTML = "Evaluate!";
}

var inp = "";

function run(code) {
    document.querySelector(".result").innerHTML = "leninec@vm:# $ ./run";
    var socket = new WebSocket(SOCKET_URL);
    socket.onopen = (e) => {
        console.log("[open] Connection established");
        console.log("Sending to server");
        var speed_map = { "1": 0.15, "2": 0.075, "5": 0.03, "0": 0, "0.5": 0.3, "0.25": 0.6 };
        socket.send(`@d ${speed_map[document.querySelector(".wrapper-speed select").value]}`);
        socket.send(code);
    };

    socket.onmessage = (event) => {
        console.log(`[message] Data received from server: ${event.data}`);
        if (event.data.startsWith("@p")) {
            let pos = parseInt(event.data.split(" ")[1]);
            update_pos(pos);
        } else if (event.data.startsWith("@r")) {
            let registers = event.data.split(" ")[1].split("|");
            for (let i = 0; i < registers.length; i++) {
                update_reg(i + 1, registers[i]);
            }
        } else if (event.data.startsWith("@s")) {
            let stack = event.data.split(" ")[1].split("|");
            document.querySelector(".stack").innerHTML = "";
            for (let i = 0; i < stack.length; i++) {
                stack_push(stack[i]);
            }
        } else if (event.data.startsWith("@f")) {
            finish();
        } else if (event.data.startsWith("@e")) {
            update_res(`./run ${inp}<br><span class="error">${event.data.split(" ").slice(1).join(" ")}</span>`);
        } else if (event.data.startsWith("@i")) {
            inp = event.data.split(" ").slice(1).join(" ");
            update_res(`./run ${inp}<br>`);
        } else if (event.data.startsWith("@o")) {
            update_res(`./run ${inp}<br>Output: ${event.data.split(" ").slice(1).join(" ")}<br>leninec@vm:# $ `);
        }
    };

    socket.onclose = (event) => {
        finish();
    };

    socket.onerror = function (error) {
        console.log(`[error] ${error.message}`);
    };
}

document.querySelector(".run-btn").addEventListener("click", function () {
    if (this.classList.contains("disabled")) return;
    Prism.highlightAll();
    document.querySelector(".stack").innerHTML = "";
    this.classList.add("disabled");
    document.querySelector(".run-btn").innerHTML = "Evaluating...";
    run(document.querySelector(".code-window code").innerHTML.replace(/<br\/?>/g, "\n").replace(/<.*?>/g, ""));
});

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

document.querySelector(".code-window").addEventListener("keydown", function (e) {
    if (e.key == "Tab") {
        e.preventDefault();
        document.execCommand("insertHTML", false, "    ");
    }
});

document.querySelector(".code-window").addEventListener("input", function (e) {
    var restore = saveCaretPosition(this.querySelector("code"));
    Prism.highlightElement(this.querySelector("code"));
    restore();
    localStorage.setItem("code", this.querySelector("code").innerHTML.replace(/<br\/?>/g, "\n").replace(/<.*?>/g, ""));
});

document.querySelector(".code-window").addEventListener("paste", function (e) {
    e.preventDefault();
    var text = e.clipboardData.getData("text/plain");
    document.execCommand("insertHTML", false, text);
});

document.querySelector(".wrapper-speed select").addEventListener("change", function () {
    localStorage.setItem("speed", document.querySelector(".wrapper-speed select").value);
    document.querySelector(".pointer").style.transitionDuration = { "1": ".1", "2": ".05", "5": ".05", "0": "0", "0.5": ".2", "0.25": ".3" }[this.value] + "s";
});
