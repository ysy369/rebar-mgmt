#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 tests/钢筋精细化管理平台_技术方案.md 转换为 PDF。
依赖：fpdf2 >= 2.5（pip install fpdf2）

支持 Windows / Linux / WSL 环境自动识别中文字体。
"""
import os
import re
import sys

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
except ImportError:
    print("请先安装 fpdf2: pip install fpdf2")
    sys.exit(1)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE_DIR, "钢筋精细化管理平台_技术方案.md")
DST = os.path.join(BASE_DIR, "钢筋精细化管理平台_技术方案.pdf")


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("CNFont", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "钢筋精细化管理平台技术方案", align="L",
                  new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(0, 10, f"第 {self.page_no()} 页", align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("CNFont", "", 8)
        self.set_text_color(150, 150, 150)


def find_chinese_font():
    """自动查找系统中文字体，返回字体路径。"""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/msyhbd.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
        "/mnt/c/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def add_fonts(pdf):
    """注册中文字体。"""
    font_path = find_chinese_font()
    if font_path:
        pdf.add_font("CNFont", "", font_path)
        pdf.add_font("CNFont", "B", font_path)
        print(f"使用字体: {font_path}")
    else:
        print("警告：未找到中文字体，PDF 中文可能显示为乱码。")
        pdf.add_font("CNFont", "", "Helvetica")


def parse_table(lines):
    """解析 Markdown 表格，返回表头和行数据。"""
    header = None
    rows = []
    sep_re = re.compile(r"^\|[\s\-:|]+\|$")
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if sep_re.match(stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if header is None:
            header = cells
        elif len(cells) == len(header):
            rows.append(cells)
    return header, rows


def process_inline(text):
    """处理加粗、行内代码等 Markdown 行内样式。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def render_table(pdf, header, rows):
    """渲染表格。"""
    col_count = len(header)
    avail = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = avail / col_count

    # 表头
    pdf.set_font("CNFont", "B", 9)
    pdf.set_fill_color(26, 39, 68)
    pdf.set_text_color(255, 255, 255)
    for j, h in enumerate(header):
        is_last = (j == len(header) - 1)
        pdf.cell(col_w, 7, h, border=1, fill=True, align="C",
                 new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                 new_y=YPos.NEXT if is_last else YPos.TOP)

    # 行
    pdf.set_font("CNFont", "", 9)
    pdf.set_text_color(50, 50, 50)
    for row in rows:
        for j, cell in enumerate(row):
            is_last = (j == len(row) - 1)
            pdf.cell(col_w, 7, cell, border=1, align="L",
                     new_x=XPos.LMARGIN if is_last else XPos.RIGHT,
                     new_y=YPos.NEXT if is_last else YPos.TOP)
    pdf.ln(3)


def _heading1(pdf, line):
    pdf.set_font("CNFont", "B", 20)
    pdf.set_text_color(26, 39, 68)
    pdf.cell(0, 12, line[2:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)


def _heading2(pdf, line):
    pdf.set_font("CNFont", "B", 15)
    pdf.set_text_color(26, 39, 68)
    pdf.cell(0, 10, line[3:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(224, 123, 57)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(3)


def _heading3(pdf, line):
    pdf.set_font("CNFont", "B", 12)
    pdf.set_text_color(26, 39, 68)
    pdf.cell(0, 8, line[4:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


def _heading4(pdf, line):
    pdf.set_font("CNFont", "B", 11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 7, line[5:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _body_width(pdf):
    """返回正文可用宽度。"""
    return pdf.w - pdf.l_margin - pdf.r_margin


def _ensure_left(pdf):
    """确保 x 在左边界。"""
    pdf.set_x(pdf.l_margin)


def _list_item(pdf, line):
    content = re.sub(r"^(\s*)-\s+", r"\1", line)
    pdf.set_font("CNFont", "", 10.5)
    pdf.set_text_color(50, 50, 50)
    _ensure_left(pdf)
    txt = "  -  " + process_inline(content)
    pdf.multi_cell(_body_width(pdf), 6, txt)


def _numbered_item(pdf, line):
    content = re.sub(r"^(\s*)\d+\.\s+", r"\1", line)
    pdf.set_font("CNFont", "", 10.5)
    pdf.set_text_color(50, 50, 50)
    _ensure_left(pdf)
    pdf.multi_cell(_body_width(pdf), 6, process_inline(content))


def _quote(pdf, line):
    pdf.set_font("CNFont", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.set_fill_color(245, 247, 250)
    _ensure_left(pdf)
    pdf.multi_cell(_body_width(pdf), 6, line[2:], fill=True)
    pdf.ln(1)


def _normal(pdf, line):
    pdf.set_font("CNFont", "", 10.5)
    pdf.set_text_color(50, 50, 50)
    _ensure_left(pdf)
    pdf.multi_cell(_body_width(pdf), 6, process_inline(line))


def render_markdown(pdf, src):
    with open(src, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    in_code = False
    list_re = re.compile(r"^(\s*)-\s+")
    num_re = re.compile(r"^(\s*)\d+\.\s+")

    while i < len(lines):
        line = lines[i].rstrip()

        # 代码块
        if line.startswith("```"):
            in_code = not in_code
            i += 1
            continue

        if in_code:
            pdf.set_font("CNFont", "", 9)
            pdf.set_fill_color(245, 245, 245)
            _ensure_left(pdf)
            pdf.multi_cell(_body_width(pdf), 5, line, fill=True)
            i += 1
            continue

        # 标题
        if line.startswith("# "):
            _heading1(pdf, line)
            i += 1
            continue
        if line.startswith("## "):
            _heading2(pdf, line)
            i += 1
            continue
        if line.startswith("### "):
            _heading3(pdf, line)
            i += 1
            continue
        if line.startswith("#### "):
            _heading4(pdf, line)
            i += 1
            continue

        # 表格
        if line.startswith("|"):
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].rstrip())
                i += 1
            header, rows = parse_table(table_lines)
            if header:
                render_table(pdf, header, rows)
            continue

        # 列表
        if list_re.match(line):
            _list_item(pdf, line)
            i += 1
            continue

        # 数字列表
        if num_re.match(line):
            _numbered_item(pdf, line)
            i += 1
            continue

        # 引用
        if line.startswith("> "):
            _quote(pdf, line)
            i += 1
            continue

        # 分隔线
        if line.strip() == "---":
            pdf.set_draw_color(200, 200, 200)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(3)
            i += 1
            continue

        # 空行
        if not line.strip():
            pdf.ln(2)
            i += 1
            continue

        # 普通段落
        _normal(pdf, line)
        i += 1


def main():
    if not os.path.exists(SRC):
        print(f"源文件不存在: {SRC}")
        sys.exit(1)

    pdf = PDF()
    add_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=20)

    # ===== 封面 =====
    pdf.add_page()
    pdf.set_fill_color(26, 39, 68)
    pdf.rect(0, 0, pdf.w, pdf.h, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.ln(50)
    pdf.set_font("CNFont", "B", 28)
    pdf.cell(0, 16, "钢筋精细化管理平台", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    pdf.set_font("CNFont", "", 18)
    pdf.set_text_color(255, 200, 100)
    pdf.cell(0, 12, "技术方案", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(40)
    pdf.set_font("CNFont", "", 12)
    pdf.set_text_color(200, 200, 220)
    pdf.cell(0, 10, "面向工程甲方管理层", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    pdf.cell(0, 8, "版本：v1.0", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "日期：2026-06-23", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ===== 正文 =====
    pdf.add_page()
    render_markdown(pdf, SRC)
    pdf.output(DST)
    print(f"PDF 已生成: {DST}")


if __name__ == "__main__":
    main()
