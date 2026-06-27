const ExcelJS = require('exceljs');
const fs = require('fs');
const path = require('path');

async function main() {
    // Read the Excel to get data
    const wb = new ExcelJS.Workbook();
    await wb.xlsx.readFile(path.join(__dirname, '4、措施筋台账及申请表-test.xlsx'));
    const ws = wb.getWorksheet('措施筋台账-自留');

    // Extract all data rows
    const rows = [];
    ws.eachRow((row, rowNum) => {
        if (rowNum >= 2) {
            const cells = [];
            row.eachCell((cell, col) => {
                let val = cell.value;
                if (val && typeof val === 'object' && val.formula) {
                    val = '[签章图片]';
                }
                cells.push({col, val});
            });
            rows.push({num: rowNum, cells, height: row.height});
        }
    });

    // Headers from row 2 (first in rows array since we start from row 2)
    const headers = rows[0].cells.map(c => ({col: c.col, name: c.val}));

    // Read image and convert to base64
    const imgPath = path.join(__dirname, '成本管理页面参考图', '微信图片_20260622113335_310_168.png');
    const imgBuffer = fs.readFileSync(imgPath);
    const imgBase64 = 'data:image/png;base64,' + imgBuffer.toString('base64');

    console.log('Image base64 length:', imgBase64.length, 'chars');

    // Generate table body rows
    let tableRows = '';
    for (const row of rows.slice(1)) {  // skip header row
        let tds = '';
        for (const h of headers) {
            const cell = row.cells.find(c => c.col === h.col);
            let val = cell ? cell.val : '';
            if (val === '[签章图片]' || h.name === '签单截图') {
                if (row.num === 4) {
                    // Row 4 gets the actual embedded image
                    tds += '<td><img class="sign-img" src="' + imgBase64 + '" alt="签章"></td>';
                } else {
                    tds += '<td>' + (val || '') + '</td>';
                }
            } else {
                tds += '<td>' + (val || '') + '</td>';
            }
        }
        tableRows += '    <tr>' + tds + '</tr>\n';
    }

    // Build header row
    let headerRow = '    <tr>' + headers.map(h => '<th>' + h.name + '</th>').join('') + '</tr>';

    const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>措施筋台账及申请表 — 打印版</title>
<style>
    @page {
        size: A4 landscape;
        margin: 12mm;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: "Microsoft YaHei", "SimSun", sans-serif;
        font-size: 10pt;
        color: #000;
    }
    h2 {
        text-align: center;
        font-size: 14pt;
        margin-bottom: 8px;
    }
    .subtitle {
        text-align: center;
        font-size: 8pt;
        color: #666;
        margin-bottom: 10px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        page-break-inside: auto;
    }
    thead { display: table-header-group; }
    th {
        background: #1A3C6E;
        color: #fff;
        font-size: 8pt;
        padding: 5px 4px;
        border: 1px solid #666;
        text-align: center;
        white-space: nowrap;
    }
    td {
        padding: 4px;
        border: 1px solid #999;
        font-size: 8pt;
        text-align: center;
        vertical-align: middle;
    }
    tr { page-break-inside: avoid; }
    .sign-img {
        max-width: 110px;
        max-height: 75px;
        object-fit: contain;
        display: block;
        margin: 0 auto;
    }
    .footer {
        margin-top: 12px;
        font-size: 8pt;
        display: flex;
        justify-content: space-between;
    }
    .sign-area {
        display: inline-block;
        width: 120px;
        border-bottom: 1px solid #000;
        margin: 0 10px;
    }
    @media print {
        .no-print { display: none !important; }
        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
    .no-print {
        position: fixed; top: 10px; right: 10px; z-index: 999;
    }
    .btn-print {
        padding: 8px 20px; background: #1A3C6E; color: #fff;
        border: none; border-radius: 4px; cursor: pointer; font-size: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .btn-print:hover { background: #0D1F3C; }
</style>
</head>
<body>

<div class="no-print">
    <button class="btn-print" onclick="window.print()">🖨️ 打印此页</button>
</div>

<h2>图纸外钢筋使用量统计表</h2>
<p class="subtitle">（注：每月15号、30号分两个批次把签字版的资料寄回总部存档）</p>

<table>
<thead>
${headerRow}
</thead>
<tbody>
${tableRows}
</tbody>
</table>

<div class="footer">
    <span>制表人：<span class="sign-area"></span></span>
    <span>审核人：<span class="sign-area"></span></span>
    <span>打印日期：${new Date().toLocaleDateString('zh-CN')}</span>
</div>

</body>
</html>`;

    const htmlPath = path.join(__dirname, '4、措施筋台账及申请表-print.html');
    fs.writeFileSync(htmlPath, html, 'utf-8');
    console.log('✓ HTML打印文件已生成:', htmlPath);
    console.log('✓ 文件大小:', (fs.statSync(htmlPath).size / 1024).toFixed(1), 'KB');
    console.log('✓ 签章图片已内嵌为base64');
    console.log('');
    console.log('使用方法：');
    console.log('  1. 浏览器打开该HTML文件');
    console.log('  2. 点击右上角"🖨️ 打印此页"按钮');
    console.log('  3. 查看打印预览效果（A4横版/彩色表头/签章图嵌入第4行）');
}

main().catch(err => console.error('Error:', err));
