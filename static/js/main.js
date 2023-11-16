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
// new DataTable("#example");

$("#example").dataTable({
  language: {
    emptyTable: "请上传发票(PDF)",
    infoFiltered: "(从总共 _MAX_ 行筛选出来)",
    loadingRecords: "读取...",
    zeroRecords: "未有相等讯息",
    info: "显示页面 _PAGE_ 共 _PAGES_ 页",
    lengthMenu: "显示 _MENU_ 行",
    search: "查找",
    paginate: {
      next: "下一页",
      previous: "上一页",
    },
  },
});
