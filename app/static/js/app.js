/**
 * 钢筋精细化管理平台 — 全局 JavaScript
 */
(function () {
    "use strict";

    // ---------- 侧边栏折叠（移动端） ----------
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });
        const mainContent = document.querySelector(".main-content");
        if (mainContent) {
            mainContent.addEventListener("click", function (e) {
                if (sidebar.classList.contains("open") && !e.target.closest(".sidebar")) {
                    sidebar.classList.remove("open");
                }
            });
        }
    }

    // ---------- Flash 消息自动消失 ----------
    document.querySelectorAll(".alert-dismissible").forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    // ---------- CSRF 自动注入：所有 POST 表单自动加上令牌 ----------
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    var csrfToken = csrfMeta ? csrfMeta.getAttribute("content") : "";
    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (form.method.toUpperCase() === "POST" && csrfToken) {
            if (!form.querySelector('input[name="_csrf_token"]')) {
                var input = document.createElement("input");
                input.type = "hidden";
                input.name = "_csrf_token";
                input.value = csrfToken;
                form.appendChild(input);
            }
        }
    });

    // ---------- 统一删除确认 ----------
    document.querySelectorAll(".confirm-delete-form").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            var message = form.getAttribute("data-message") || "确定删除？";
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // ---------- 批量操作确认 ----------
    document.querySelectorAll("form[data-batch-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            var message = form.getAttribute("data-batch-confirm");
            var checked = form.querySelectorAll('input[type="checkbox"]:checked').length;
            if (checked === 0) {
                alert("请至少选择一项");
                e.preventDefault();
                return;
            }
            if (message && !confirm(message.replace("{count}", checked))) {
                e.preventDefault();
            }
        });
    });

    // ---------- 表单提交 Loading ----------
    document.querySelectorAll("form").forEach(function (form) {
        var submitBtn = form.querySelector('button[type="submit"]');
        if (!submitBtn) return;
        form.addEventListener("submit", function () {
            if (form.checkValidity && !form.checkValidity()) return;
            submitBtn.disabled = true;
            var originalText = submitBtn.innerHTML;
            submitBtn.setAttribute("data-original-text", originalText);
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...';
            // 5 秒后自动恢复，防止提交失败后按钮一直禁用
            setTimeout(function () {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }, 5000);
        });
    });

    // ---------- 全选 / 反选 ----------
    document.querySelectorAll("[data-check-all]").forEach(function (master) {
        master.addEventListener("change", function () {
            var targetClass = master.getAttribute("data-check-all");
            document.querySelectorAll("." + targetClass).forEach(function (cb) {
                cb.checked = master.checked;
            });
        });
    });

    // ---------- 图片上传预览 ----------
    document.querySelectorAll("input[data-preview]").forEach(function (input) {
        input.addEventListener("change", function () {
            var targetId = input.getAttribute("data-preview");
            var target = document.getElementById(targetId);
            if (!target || input.files.length === 0) return;
            var file = input.files[0];
            if (!file.type.startsWith("image/")) return;
            var reader = new FileReader();
            reader.onload = function (e) {
                target.src = e.target.result;
                target.classList.remove("d-none");
            };
            reader.readAsDataURL(file);
        });
    });

    // ---------- 文件列表渲染（避免 innerHTML 拼接） ----------
    window.updateFileListDom = function (fileInputId, listId, submitBtnId) {
        var files = document.getElementById(fileInputId).files;
        var list = document.getElementById(listId);
        var btn = document.getElementById(submitBtnId);
        if (!list) return;
        list.innerHTML = "";
        for (var i = 0; i < files.length; i++) {
            var div = document.createElement("div");
            div.className = "text-success";
            div.innerHTML = '<i class="bi bi-file-earmark-excel"></i> ' + files[i].name;
            list.appendChild(div);
        }
        if (btn) btn.disabled = files.length === 0;
    };
})();

// ============================================
// 层级侧边栏交互（支持三级嵌套）
// ============================================

function getMenuStorageKey() {
    var menu = document.getElementById("sidebarMenu");
    var context = menu ? menu.getAttribute("data-menu-context") : "global";
    var projectId = menu ? menu.getAttribute("data-project-id") : "";
    return "expandedMenus_" + (context || "global") + "_" + (projectId || "0");
}

function saveMenuState() {
    var storageKey = getMenuStorageKey();
    var expandedMenus = [];
    document.querySelectorAll(".menu-group.expanded").forEach(function (g) {
        var key = g.getAttribute("data-menu-key");
        if (key) {
            expandedMenus.push(key);
        }
    });
    localStorage.setItem(storageKey, JSON.stringify(expandedMenus));
}

function toggleMenu(element) {
    if (typeof event !== "undefined" && event) {
        event.stopPropagation();
        event.preventDefault();
    }
    var group = element.closest(".menu-group");
    if (!group) return;
    group.classList.toggle("expanded");
    saveMenuState();
}

function expandParentMenus(activeEl) {
    var parent = activeEl.closest(".menu-group");
    while (parent) {
        parent.classList.add("expanded");
        parent = parent.parentElement.closest(".menu-group");
    }
}

document.addEventListener("DOMContentLoaded", function () {
    var storageKey = getMenuStorageKey();
    var saved = localStorage.getItem(storageKey);

    if (saved) {
        try {
            var expandedMenus = JSON.parse(saved);
            document.querySelectorAll(".menu-group").forEach(function (g) {
                var key = g.getAttribute("data-menu-key");
                if (key && expandedMenus.indexOf(key) !== -1) {
                    g.classList.add("expanded");
                }
            });
        } catch (e) {
            localStorage.removeItem(storageKey);
        }
    }

    // 自动展开当前页所在的所有父级菜单
    var activeLeaf = document.querySelector(".submenu a.active");
    var activeHome = document.querySelector(".menu-home.active");
    if (activeLeaf) {
        expandParentMenus(activeLeaf);
    }
    if (activeHome) {
        expandParentMenus(activeHome);
    }
});
