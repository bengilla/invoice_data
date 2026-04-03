pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

function showToast(msg) {
    return new Promise(function (resolve) {
        var toast = document.getElementById('toast');
        var overlay = document.getElementById('toast-overlay');
        document.getElementById('toast-msg').textContent = msg;
        toast.style.display = 'block';
        overlay.style.display = 'block';
        setTimeout(function () {
            toast.style.opacity = '1';
            toast.style.transform = 'translate(-50%,-50%) scale(1)';
            overlay.style.opacity = '1';
        }, 10);
        overlay.onclick = function () { hideToast(); resolve(); };
        toast.onclick = function () { hideToast(); resolve(); };
    });
}
function hideToast() {
    var toast = document.getElementById('toast');
    var overlay = document.getElementById('toast-overlay');
    toast.style.opacity = '0';
    toast.style.transform = 'translate(-50%,-50%) scale(0.9)';
    overlay.style.opacity = '0';
    setTimeout(function () {
        toast.style.display = 'none';
        overlay.style.display = 'none';
    }, 300);
}

let isNight = false;

var subtitles = ['让每一张发票都有价值 ✨', '辛苦了，今天也要好好报销 🍀', '每一分钱都值得被记录 💫', '报销路上一路顺风 🚗', '整理发票，整理心情 🌸', '小发票，大智慧 📝', '轻松报销，快乐工作 🎈', '发票整理好，加薪跑不了 💰', '认真填报销的人，运气都不会差 🌟', '每一笔花费都有意义 💎'];
var subtitleEl = document.getElementById('subtitle');
if (subtitleEl) {
    subtitleEl.textContent = subtitles[Math.floor(Math.random() * subtitles.length)];
}

var sun = document.querySelector('.sun');
var moon = document.querySelector('.moon');

if (sun && moon) {
    sun.addEventListener('click', function() {
        if (isNight) return;
        isNight = true;
        document.body.classList.add('night');
    });
    moon.addEventListener('click', function() {
        if (!isNight) return;
        isNight = false;
        document.body.classList.remove('night');
    });
}

const today = new Date();
document.querySelector('input[name="date"]').value = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');

let currentInvoice = null;
let allData = { months: [], total_amount: 0, invoices: [], invoiceFiles: {}, session_id: null };
let currentBuyer = null;

// 拖拽上传
const uploadArea = document.getElementById('upload-area');
uploadArea.addEventListener('dragover', function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.style.borderColor = 'var(--primary)';
    this.style.background = 'var(--card-hover)';
});
uploadArea.addEventListener('dragleave', function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.style.borderColor = '';
    this.style.background = '';
});
uploadArea.addEventListener('drop', function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.style.borderColor = '';
    this.style.background = '';
    var files = Array.from(e.dataTransfer.files);
    processFiles(files);
});

async function processFiles(allFiles) {
    const pdfFiles = allFiles.filter(f => f.name.match(/\.(pdf|png|jpg|jpeg|bmp|gif)$/i));

    if (pdfFiles.length === 0) {
        document.getElementById('month-list').innerHTML = '<div class="no-data">未找到发票文件</div>';
        return;
    }

    document.getElementById('month-list').innerHTML = '<div class="loading">正在处理发票...</div>';

    // 追加新文件到已有文件
    pdfFiles.forEach(file => {
        allData.invoiceFiles[file.name] = file;
    });

    // 发送所有文件给API（服务器会去重）
    const allFileList = Object.values(allData.invoiceFiles);
    const formData = new FormData();
    allFileList.forEach(file => {
        formData.append('files', file);
    });

    try {
        const response = await fetch('/api/parse-invoices', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            // 调用计数器 API
            try {
                const counterRes = await fetch('/api/counter/increment', { method: 'POST' });
                const counterData = await counterRes.json();
                if (window.updateCrystalCount) {
                    window.updateCrystalCount(counterData.count);
                }
            } catch (e) {}

            // 合并发票数据（支持多次上传）
            const existingFiles = new Set(allData.invoices.map(inv => inv.file_name));
            const newInvoices = (result.invoices || []).filter(inv => !existingFiles.has(inv.file_name));
            allData.invoices = [...allData.invoices, ...newInvoices];
            
            // 重新计算月份数据
            const monthsMap = {};
            allData.invoices.forEach(inv => {
                const key = inv.year + '-' + inv.month;
                if (!monthsMap[key]) {
                    monthsMap[key] = { year: inv.year, month: inv.month, invoices: [], total: 0 };
                }
                monthsMap[key].invoices.push(inv);
                monthsMap[key].total += inv.amount;
            });
            allData.months = Object.values(monthsMap);
            allData.total_amount = allData.invoices.reduce((sum, inv) => sum + inv.amount, 0);
            
            allData.session_id = result.session_id || allData.session_id;
            currentBuyer = null;
            renderStats();
            renderBuyerSection();
            renderMonthList();
            document.getElementById('download-all-btn').style.display = allData.invoices.length > 0 ? 'block' : 'none';
            document.getElementById('clear-btn').style.display = allData.invoices.length > 0 ? 'block' : 'none';
            document.getElementById('meta-form').style.display = allData.invoices.length > 0 ? 'block' : 'none';

            if (result.duplicates && result.duplicates.length > 0) {
                showToast('以下文件重复已跳过：\n' + result.duplicates.join('\n'));
            }
        } else {
            document.getElementById('month-list').innerHTML = '<div class="no-data">' + (result.error || '解析失败') + '</div>';
        }
    } catch (err) {
        console.error('Error:', err);
        document.getElementById('month-list').innerHTML = '<div class="no-data">上传失败: ' + err.message + '</div>';
    }
}

document.getElementById('folder-input').addEventListener('change', function (e) {
    processFiles(Array.from(e.target.files));
});

function clearAllData() {
    allData = { months: [], total_amount: 0, invoices: [], invoiceFiles: {}, session_id: null };
    currentBuyer = null;
    currentInvoice = null;

    document.getElementById('stats').style.display = 'none';
    document.getElementById('buyer-section').style.display = 'none';
    document.getElementById('meta-form').style.display = 'none';
    document.getElementById('month-list').innerHTML = '';
    document.getElementById('download-all-btn').style.display = 'none';
    document.getElementById('clear-btn').style.display = 'none';
    document.getElementById('folder-input').value = '';
}

function toChineseUpper(amount) {
    const cnNums = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖'];
    const cnIntRadice = ['', '拾', '佰', '仟'];
    const cnIntUnits = ['', '万', '亿', '兆'];
    const cnDecUnits = ['角', '分'];
    const cnInteger = '整';
    const cnIntLast = '元';
    const maxNum = 9999999999999.99;

    if (amount >= maxNum) return '金额超出范围';
    let integerNum = Math.floor(amount);
    let decimalNum = Math.round((amount - integerNum) * 100);
    let chineseStr = '';

    if (integerNum === 0) {
        chineseStr = cnNums[0];
    } else {
        let zeroCount = 0;
        let intLen = integerNum.toString().length;
        for (let i = 0; i < intLen; i++) {
            let n = Math.floor(integerNum / Math.pow(10, intLen - i - 1)) % 10;
            let p = intLen - i - 1;
            let quotient = Math.floor(p / 4);
            let modulus = p % 4;
            if (n === 0) {
                zeroCount++;
            } else {
                if (zeroCount > 0) chineseStr += cnNums[0];
                zeroCount = 0;
                chineseStr += cnNums[n] + cnIntRadice[modulus];
            }
            if (modulus === 0 && zeroCount < 4) {
                chineseStr += cnIntUnits[quotient];
            }
        }
    }
    chineseStr += cnIntLast;

    if (decimalNum === 0) {
        chineseStr += cnInteger;
    } else {
        let jiao = Math.floor(decimalNum / 10);
        let fen = decimalNum % 10;
        if (jiao > 0) chineseStr += cnNums[jiao] + cnDecUnits[0];
        if (fen > 0) chineseStr += cnNums[fen] + cnDecUnits[1];
    }

    return '人民币 ' + chineseStr;
}

function renderStats() {
    const filteredInvoices = currentBuyer
        ? allData.invoices.filter(function (inv) { return inv.buyer === currentBuyer; })
        : allData.invoices;
    const otherCount = allData.invoices.length - filteredInvoices.length;

    const filteredMonths = {};
    filteredInvoices.forEach(function (inv) {
        const key = inv.year + '-' + inv.month;
        if (!filteredMonths[key]) {
            filteredMonths[key] = { year: inv.year, month: inv.month, total: 0 };
        }
        filteredMonths[key].total += inv.amount;
    });

    const totalAmount = filteredInvoices.reduce(function (s, i) { return s + i.amount; }, 0);

    document.getElementById('invoice-count').textContent = filteredInvoices.length;
    document.getElementById('total-amount').textContent = '¥' + totalAmount.toFixed(2);
    document.getElementById('stats').style.display = 'grid';

    document.getElementById('amount-upper').textContent = toChineseUpper(totalAmount);
    document.getElementById('summary-other').textContent = otherCount;
}

function renderBuyerSection() {
    const buyerSection = document.getElementById('buyer-section');
    const buyerButtons = document.getElementById('buyer-buttons');

    const buyerMap = {};
    allData.invoices.forEach(function (inv) {
        const buyer = inv.buyer || '未知';
        if (!buyerMap[buyer]) {
            buyerMap[buyer] = { count: 0, total: 0 };
        }
        buyerMap[buyer].count++;
        buyerMap[buyer].total += inv.amount;
    });

    const buyers = Object.keys(buyerMap);

    if (buyers.length <= 1) {
        buyerSection.style.display = 'none';
        return;
    }

    buyerSection.style.display = 'block';
    buyerButtons.innerHTML = '';

    buyers.forEach(function (buyer) {
        const btn = document.createElement('button');
        btn.className = 'buyer-btn';
        btn.innerHTML = buyer + ' <span style="opacity:0.7">¥' + buyerMap[buyer].total.toFixed(2) + '</span>';
        btn.onclick = function () { toggleBuyer(buyer); };
        buyerButtons.appendChild(btn);
    });

    const allBtn = document.createElement('button');
    allBtn.className = 'buyer-btn';
    allBtn.innerHTML = '全部';
    allBtn.onclick = function () { toggleBuyer(null); };
    buyerButtons.appendChild(allBtn);

    if (buyers.length > 0) {
        toggleBuyer(buyers[0]);
    }
}

function toggleBuyer(buyer) {
    currentBuyer = buyer;

    document.querySelectorAll('.buyer-btn').forEach(function (btn) {
        btn.classList.remove('active');
        if ((buyer === null && btn.innerHTML === '全部') ||
            (btn.innerHTML.startsWith(buyer))) {
            btn.classList.add('active');
        }
    });

    renderStats();
    renderMonthList();
}

function renderMonthList() {
    const container = document.getElementById('month-list');
    container.innerHTML = '';

    const sortedMonths = allData.months.sort(function (a, b) {
        if (a.year !== b.year) return b.year - a.year;
        return b.month - a.month;
    });

    if (sortedMonths.length === 0) {
        container.innerHTML = '<div class="no-data">未找到发票文件</div>';
        return;
    }

    sortedMonths.forEach(function (monthData) {
        let filteredInvoices = currentBuyer
            ? monthData.invoices.filter(function (inv) { return inv.buyer === currentBuyer; })
            : monthData.invoices;

        if (filteredInvoices.length === 0) return;

        filteredInvoices = filteredInvoices.slice().sort(function (a, b) {
            if (a.date && b.date) return a.date.localeCompare(b.date);
            return 0;
        });

        const filteredTotal = filteredInvoices.reduce(function (sum, inv) { return sum + inv.amount; }, 0);

        const section = document.createElement('div');
        section.className = 'month-section';

        const html = '<div class="month-header" onclick="toggleMonth(\'' + monthData.year + '-' + monthData.month + '\')">' +
            '<div><div class="month-title">' + monthData.year + '年' + monthData.month + '月</div>' +
            '<div class="month-meta">' + filteredInvoices.length + '张发票</div></div>' +
            '<div class="month-total">¥' + filteredTotal.toFixed(2) + '</div>' +
            '</div>' +
            '<div class="invoice-list" id="list-' + monthData.year + '-' + monthData.month + '">' +
            '<div class="invoice-item header">' +
            '<span class="invoice-index">#</span><span class="invoice-date">日期</span><span class="invoice-company">事项</span><span class="invoice-reason">明细/原由</span><span class="invoice-remark">备注</span><span class="invoice-amount">金额</span><span class="invoice-view">查看</span><span class="invoice-delete">删除</span>' +
            '</div>';

        let invoiceHtml = '';
        filteredInvoices.forEach(function (inv, idx) {
            const itemValue = inv.company || '';
            const reasonValue = inv.reason || '';
            const remarkValue = inv.remark || '';
            invoiceHtml += '<div class="invoice-item">' +
                '<span class="invoice-index">' + (idx + 1) + '</span>' +
                '<span class="invoice-date">' + ((inv.date && inv.date.length >= 5) ? inv.date.substring(5) : (inv.date || '-')) + '</span>' +
                '<span class="invoice-company">' +
                '<div class="custom-select" id="cs-' + inv.file_name + '">' +
                '<div class="custom-select-trigger" onclick="toggleCustomSelect(event)">' + (itemValue || '选择事项') + '</div>' +
                '<div class="custom-select-dropdown">' +
                '<div class="custom-select-option" data-value="" onclick="selectCustomOption(event, \'\', \'' + inv.file_name + '\')">选择事项</div>' +
                '<div class="custom-select-option" data-value="差旅费" onclick="selectCustomOption(event, \'差旅费\', \'' + inv.file_name + '\')">差旅费</div>' +
                '<div class="custom-select-option" data-value="交通费" onclick="selectCustomOption(event, \'交通费\', \'' + inv.file_name + '\')">交通费</div>' +
                '<div class="custom-select-option" data-value="住宿费" onclick="selectCustomOption(event, \'住宿费\', \'' + inv.file_name + '\')">住宿费</div>' +
                '<div class="custom-select-option" data-value="餐饮" onclick="selectCustomOption(event, \'餐饮\', \'' + inv.file_name + '\')">餐饮</div>' +
                '<div class="custom-select-option" data-value="办公用品" onclick="selectCustomOption(event, \'办公用品\', \'' + inv.file_name + '\')">办公用品</div>' +
                '<div class="custom-select-option" data-value="业务招待费" onclick="selectCustomOption(event, \'业务招待费\', \'' + inv.file_name + '\')">业务招待费</div>' +
                '<div class="custom-select-option" data-value="其他" onclick="selectCustomOption(event, \'其他\', \'' + inv.file_name + '\')">其他</div>' +
                '</div></div></span>' +
                '<span class="invoice-reason"><input type="text" class="reason-input" value="' + reasonValue + '" onchange="handleReasonChange(\'' + inv.file_name + '\', this.value)"></span>' +
                '<span class="invoice-remark"><input type="text" class="remark-input" value="' + remarkValue + '" onchange="handleRemarkChange(\'' + inv.file_name + '\', this.value)"></span>' +
                '<span class="invoice-amount">¥' + inv.amount.toFixed(2) + '</span>' +
                '<span class="invoice-view"><a href="#" class="view-btn" onclick="viewInvoice(\'' + inv.file_name + '\'); return false;"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg></a></span>' +
                '<span class="invoice-delete"><a href="#" style="color:#ef4444;font-size:14px;text-decoration:none;" onclick="deleteInvoice(\'' + inv.file_name + '\'); return false;">✕</a></span>' +
                '</div>';
        });

        section.innerHTML = html + invoiceHtml + '</div>';

        container.appendChild(section);
    });
}

function toggleMonth(key) {
    const list = document.getElementById('list-' + key);
    if (list) list.classList.toggle('show');
}

function deleteInvoice(fileName) {
    // 保存展开状态
    var openMonths = [];
    document.querySelectorAll('.invoice-list.show').forEach(function (el) {
        openMonths.push(el.id.replace('list-', ''));
    });

    allData.invoices = allData.invoices.filter(function (inv) { return inv.file_name !== fileName; });
    delete allData.invoiceFiles[fileName];
    var monthsMap = {};
    allData.invoices.forEach(function (inv) {
        var key = inv.year + '-' + inv.month;
        if (!monthsMap[key]) {
            monthsMap[key] = { year: inv.year, month: inv.month, invoices: [], total: 0 };
        }
        monthsMap[key].invoices.push(inv);
        monthsMap[key].total += inv.amount;
    });
    allData.months = Object.values(monthsMap);
    allData.total_amount = allData.invoices.reduce(function (s, i) { return s + i.amount; }, 0);
    currentBuyer = null;
    renderStats();
    renderBuyerSection();
    renderMonthList();

    // 恢复展开状态
    openMonths.forEach(function (key) {
        var list = document.getElementById('list-' + key);
        if (list) list.classList.add('show');
    });
}

function viewInvoice(fileName) {
    console.log('Viewing invoice:', fileName);
    console.log('Available files:', Object.keys(allData.invoiceFiles));

    const inv = allData.invoices.find(function (i) { return i.file_name === fileName; });
    if (!inv) return;

    console.log('Looking for file:', inv.file_name);
    const file = allData.invoiceFiles[inv.file_name];

    if (!file) {
        showToast('找不到文件');
        return;
    }

    currentInvoice = { inv: inv, file: file };

    const preview = document.getElementById('pdf-preview');
    const url = URL.createObjectURL(file);

    preview.innerHTML = '<iframe src="' + url + '" style="width:100%;height:85vh;border:none;"></iframe>';

    document.getElementById('pdf-modal').classList.add('show');
}

function closeModal() {
    document.getElementById('pdf-modal').classList.remove('show');
    currentInvoice = null;
}

let pendingOtherItemFileName = null;
let pendingOtherItemSelect = null;

function toggleCustomSelect(e) {
    e.stopPropagation();
    const trigger = e.currentTarget;
    const select = trigger.closest('.custom-select');
    const dropdown = select.querySelector('.custom-select-dropdown');
    const wasOpen = select.classList.contains('open');
    document.querySelectorAll('.custom-select.open').forEach(function (el) {
        el.classList.remove('open');
        el.classList.remove('open-above');
    });
    if (!wasOpen) {
        select.classList.add('open');
        const rect = select.getBoundingClientRect();
        const dropdownHeight = dropdown.offsetHeight;
        if (rect.bottom + dropdownHeight > window.innerHeight) {
            select.classList.add('open-above');
        }
    }
}

function selectCustomOption(e, value, fileName) {
    e.stopPropagation();
    const trigger = e.currentTarget;
    const select = trigger.closest('.custom-select');
    const options = select.querySelectorAll('.custom-select-option');
    options.forEach(function (opt) {
        opt.classList.remove('selected');
        if (opt.dataset.value === value) {
            opt.classList.add('selected');
        }
    });
    trigger.textContent = value || '选择事项';

    if (value === '其他') {
        pendingOtherItemFileName = fileName;
        pendingOtherItemSelect = select;
        document.getElementById('other-item-input').value = '';
        document.getElementById('other-item-modal').classList.add('show');
        document.getElementById('other-item-input').focus();
    } else {
        select.classList.remove('open');
        updateInvoiceItem(fileName, value);
    }
}

document.addEventListener('click', function (e) {
    if (!e.target.closest('.custom-select')) {
        document.querySelectorAll('.custom-select.open').forEach(function (el) {
            el.classList.remove('open');
        });
    }
});

function handleItemChange(fileName, value, selectEl) {
    if (value === '其他') {
        pendingOtherItemFileName = fileName;
        pendingOtherItemSelect = selectEl;
        document.getElementById('other-item-input').value = '';
        document.getElementById('other-item-modal').classList.add('show');
        document.getElementById('other-item-input').focus();
        setTimeout(function () { selectEl.blur(); }, 0);
    } else {
        updateInvoiceItem(fileName, value);
        setTimeout(function () { selectEl.blur(); }, 0);
    }
}

function closeOtherItemModal() {
    document.getElementById('other-item-modal').classList.remove('show');
    if (pendingOtherItemSelect) {
        pendingOtherItemSelect.value = '';
    }
    pendingOtherItemFileName = null;
    pendingOtherItemSelect = null;
}

function confirmOtherItem() {
    const value = document.getElementById('other-item-input').value.trim();
    if (!value) {
        showToast('请输入事项内容');
        return;
    }
    if (pendingOtherItemFileName) {
        updateInvoiceItem(pendingOtherItemFileName, value);
    }
    closeOtherItemModal();
}

function handleReasonChange(fileName, value) {
    const inv = allData.invoices.find(function (i) { return i.file_name === fileName; });
    if (inv) {
        inv.reason = value;
    }
}

function handleRemarkChange(fileName, value) {
    const inv = allData.invoices.find(function (i) { return i.file_name === fileName; });
    if (inv) {
        inv.remark = value;
    }
}

function updateInvoiceItem(fileName, value) {
    var openMonths = [];
    document.querySelectorAll('.invoice-list.show').forEach(function (el) {
        openMonths.push(el.id.replace('list-', ''));
    });

    const inv = allData.invoices.find(function (i) { return i.file_name === fileName; });
    if (inv) {
        inv.company = value;
        rebuildMonthsData();
        renderStats();
        renderBuyerSection();
        renderMonthList();

        openMonths.forEach(function (key) {
            var list = document.getElementById('list-' + key);
            if (list) list.classList.add('show');
        });
    }
}

function rebuildMonthsData() {
    var monthsMap = {};
    allData.invoices.forEach(function (inv) {
        var key = inv.year + '-' + inv.month;
        if (!monthsMap[key]) {
            monthsMap[key] = { year: inv.year, month: inv.month, invoices: [], total: 0 };
        }
        monthsMap[key].invoices.push(inv);
        monthsMap[key].total += inv.amount;
    });
    allData.months = Object.values(monthsMap);
}

document.getElementById('pdf-modal').addEventListener('click', function (e) {
    if (e.target === this) closeModal();
});

document.getElementById('other-item-modal').addEventListener('click', function (e) {
    if (e.target === this) closeOtherItemModal();
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        closeModal();
        closeOtherItemModal();
    }
});

function getMeta() {
    return {
        department: document.querySelector('[name="department"]').value || '',
        date: document.querySelector('[name="date"]').value || '',
        name: document.querySelector('[name="name"]').value || '',
        position: document.querySelector('[name="position"]').value || '',
    };
}

async function downloadMonth(year, month) {
    if (!document.querySelector('[name="name"]').value.trim()) {
        showToast('请填写报销人姓名');
        document.querySelector('[name="name"]').focus();
        return;
    }
    const monthData = allData.months.find(function (m) {
        return m.year === parseInt(year) && m.month === parseInt(month);
    });
    if (!monthData) return;

    const filteredInvoices = currentBuyer
        ? monthData.invoices.filter(function (inv) { return inv.buyer === currentBuyer; })
        : monthData.invoices;

    const filteredTotal = filteredInvoices.reduce(function (sum, inv) { return sum + inv.amount; }, 0);
    const otherCount = allData.invoices.length - filteredInvoices.length;

    const downloadData = {
        session_id: allData.session_id,
        year: year,
        month: month,
        invoices: filteredInvoices,
        total: filteredTotal,
        total_other_invoice: otherCount,
        meta: getMeta()
    };

    try {
        const response = await fetch('/api/download-month-zip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(downloadData)
        });

        if (!response.ok) {
            throw new Error('下载失败');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = year + '.' + String(month).padStart(2, '0') + '（' + filteredInvoices.length + '张发票）-¥' + filteredTotal.toFixed(2) + '.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (err) {
        showToast('下载失败: ' + err.message);
    }
}

async function downloadAllInvoices() {
    if (!document.querySelector('[name="name"]').value.trim()) {
        showToast('请填写报销人姓名');
        document.querySelector('[name="name"]').focus();
        return;
    }
    try {
        const filteredInvoices = currentBuyer
            ? allData.invoices.filter(function (inv) { return inv.buyer === currentBuyer; })
            : allData.invoices;

        const filteredMonths = {};
        filteredInvoices.forEach(function (inv) {
            const key = inv.year + '-' + inv.month;
            if (!filteredMonths[key]) {
                filteredMonths[key] = { year: inv.year, month: inv.month, invoices: [], total: 0 };
            }
            filteredMonths[key].invoices.push(inv);
            filteredMonths[key].total += inv.amount;
        });

        const monthsList = Object.values(filteredMonths);
        const totalAmount = filteredInvoices.reduce(function (s, i) { return s + i.amount; }, 0);
        const firstYear = monthsList.length > 0 ? monthsList[0].year : '2026';

        const downloadData = {
            session_id: allData.session_id,
            months: monthsList,
            total_amount: totalAmount,
            total_other_invoice: allData.invoices.length - filteredInvoices.length,
            meta: getMeta()
        };

        const response = await fetch('/api/download-all-zip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(downloadData)
        });

        if (!response.ok) {
            throw new Error('下载失败');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = firstYear + '-¥' + totalAmount.toFixed(2) + '.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (err) {
        showToast('下载失败: ' + err.message);
    }
}