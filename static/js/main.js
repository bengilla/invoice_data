// main checkbox function
function toggle() {
  mainCheck = $("#main_checkbox");
  singleCheck = $(".single_checkbox");

  if (mainCheck.prop("checked") === true) {
    singleCheck.each(function () {
      var element = $(this);
      if (element.is(":visible")) {
        element.prop("checked", true);
      }
    });
  } else {
    singleCheck.prop("checked", false);
  }
}

// if un-uncheck single checkbox, select all checkbox with disable
function single() {
  mainCheckbox = $("#main_checkbox");
  singleCheckbox = $(".single_checkbox");
  count = singleCheckbox.filter(":checked").length;

  mainCheckbox.prop("checked", count === singleCheckbox.length);
}

// ----------------------------------------------------------------

// url pathname
let url = location.pathname;

// if empty hide title box (jquery)
// title = $("#title_box");
// if (url === "/month/0" || url === "/month/None") {
//   title.show();
// } else {
//   title.show();
// }

// button color
selector = "#" + $.escapeSelector(url);
btn = $(selector);
btn.css({
  "background-color": "#f97316",
  "border-color": "#f97316",
  color: "#fff",
});

// ----------------------------------------------------------------

// error fadeout
errorElements = $(".error");
if (errorElements.length) {
  // check if any elements were found
  setTimeout(function () {
    errorElements.fadeOut("slow", function () {
      $(this).remove();
    });
  }, 8000);
}

// ----------------------------------------------------------------

// hide and show function
function invoice(source) {
  each_company = $("." + source.innerHTML); // 取这个公司的 class
  companyList = $(".company_list");

  companyList.hide();
  each_company.show();
}

function all_invoice(source) {
  companyList = $(".company_list");
  companyList.show();
}
