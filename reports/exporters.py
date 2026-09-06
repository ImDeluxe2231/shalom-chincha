import csv
from io import BytesIO, StringIO
from textwrap import wrap
from xml.sax.saxutils import escape as xml_escape
from zipfile import ZIP_DEFLATED, ZipFile


def csv_bytes(headers, rows):
    buffer = StringIO(newline="")
    buffer.write("\ufeff")
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _excel_column(number):
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def xlsx_bytes(headers, rows):
    all_rows = [headers, *rows]
    sheet_rows = []
    for row_index, row in enumerate(all_rows, start=1):
        cells = []
        style = ' s="1"' if row_index == 1 else (' s="2"' if row_index % 2 == 0 else "")
        for column_index, value in enumerate(row, start=1):
            reference = f"{_excel_column(column_index)}{row_index}"
            safe = xml_escape(str(value if value is not None else ""))
            cells.append(f'<c r="{reference}" t="inlineStr"{style}><is><t>{safe}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    last_column = _excel_column(len(headers))
    widths = "".join(
        f'<col min="{index}" max="{index}" width="{min(35, max(12, len(str(header)) + 4))}" customWidth="1"/>'
        for index, header in enumerate(headers, start=1)
    )
    sheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
<cols>{widths}</cols><sheetData>{"".join(sheet_rows)}</sheetData>
<autoFilter ref="A1:{last_column}{max(1, len(all_rows))}"/>
</worksheet>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Reporte" sheetId="1" r:id="rId1"/></sheets></workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="10"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF102746"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/><xf numFmtId="0" fontId="0" fillId="1" borderId="0" xfId="0" applyFill="1"/></cellXfs>
</styleSheet>'''
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


def _pdf_safe(value):
    text = str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("latin-1", "replace").decode("latin-1")


def pdf_bytes(title, period, headers, rows):
    lines = [title, period, ""]
    heading = " | ".join(headers)
    lines.extend(wrap(heading, 145) or [heading])
    lines.append("-" * 145)
    for row in rows:
        value = " | ".join(str(cell) for cell in row)
        lines.extend(wrap(value, 145, break_long_words=True, break_on_hyphens=False) or [value])
    if not rows:
        lines.append("No existen registros para los filtros seleccionados.")

    page_chunks = [lines[index:index + 55] for index in range(0, len(lines), 55)] or [[]]
    objects = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    page_ids = [4 + index * 2 for index in range(len(page_chunks))]
    objects[2] = f'<< /Type /Pages /Kids [{" ".join(f"{item} 0 R" for item in page_ids)}] /Count {len(page_ids)} >>'.encode()
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    for index, chunk in enumerate(page_chunks):
        page_id = page_ids[index]
        content_id = page_id + 1
        commands = ["BT", "/F1 7 Tf"]
        y = 565
        for line in chunk:
            commands.append(f"1 0 0 1 28 {y} Tm ({_pdf_safe(line)}) Tj")
            y -= 10
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        objects[page_id] = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        objects[content_id] = f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"

    output = BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}
    for object_id in range(1, max(objects) + 1):
        offsets[object_id] = output.tell()
        output.write(f"{object_id} 0 obj\n".encode())
        output.write(objects[object_id])
        output.write(b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {max(objects) + 1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for object_id in range(1, max(objects) + 1):
        output.write(f"{offsets[object_id]:010d} 00000 n \n".encode())
    output.write(f"trailer\n<< /Size {max(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return output.getvalue()
