// checkbox function (jquery)
function toggle(source) {
    checkboxs = $("[name='ids']");
    for (var i = 0, n = checkboxs.length; i < n; i++) {
        checkboxs[i].checked = source.checked;
    }
}

// single button
function single(source) {
    checkboxs = $("[name='ids']");
    let count = 0;

    for (var i = 0, n = checkboxs.length; i < n; i++) {
        if (checkboxs[i].type === "checkbox" && checkboxs[i].checked === true) {
            count++;
        }
    }
    if (count > 0) {
        console.log(count);
    } else {
        document.getElementById("main-checkbox").checked = false;
    }
}

// url pathname
let url = location.pathname;

// if empty hide title box (jquery)
const title = $("#title-box");
if (url === "/month/0" || url === "/month/None") {
    title.css("display", "none");
} else {
    title.css("display", "");
}

// button color
let btn = document.getElementById(url)
btn.style.backgroundColor = "#f97316";
btn.style.borderColor = "#f97316";
btn.style.color = "#fff";

// fadeout (jquery)
if ($("#error")) {
    setTimeout(function () {
        $("#error").fadeOut("slow", function() {
        $("#error").remove()
        });
    }, 5000);
}
