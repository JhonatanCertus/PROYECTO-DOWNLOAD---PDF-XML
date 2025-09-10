# ============================================================
# DESCARGADOR DE FACTURAS (PDF/XML) CON PESTAÑAS
# Pestaña 1: Descarga actual
# Pestaña 2: Descarga independiente
# ============================================================

import requests
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkcalendar import DateEntry
from concurrent.futures import ThreadPoolExecutor
import threading

# ============================================================
# VARIABLES GLOBALES
# ============================================================

# Pestaña 1
facturas_descargadas = 0
facturas_fallidas = 0
pdf_encontrados = 0
xml_encontrados = 0
pdf_descargados = 0 
xml_descargados = 0
descargar_pdf = None
descargar_xml = None
session = None
cerrar_app = False
total_registros = 0

# Pestaña 2
facturas_descargadas2 = 0
facturas_fallidas2 = 0
pdf_descargados2 = 0
xml_descargados2 = 0
descargar_pdf2 = None
descargar_xml2 = None
session2 = None
cerrar_app2 = False
total_registros2 = 0

# URLs y cabeceras (compartidas)
login_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal.php"
facturas_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal2.php"
headers = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://facturacalvicperu.com",
    "Referer": "https://facturacalvicperu.com/fealvic/factura/inicio.php",
}

# ============================================================
# FUNCIONES DE DESCARGA (PESTAÑA 1)
# ============================================================

def descargar_archivo(session, url, nombre_archivo, download_folder):
    global facturas_descargadas, facturas_fallidas, cerrar_app
    if cerrar_app:
        return
    try:
        r = session.get(url)
        if r.status_code == 200:
            ruta = os.path.join(download_folder, nombre_archivo)
            with open(ruta, 'wb') as f:
                f.write(r.content)
            facturas_descargadas += 1
        else:
            facturas_fallidas += 1
    except:
        facturas_fallidas += 1

    progress['value'] = facturas_descargadas + facturas_fallidas
    root.update_idletasks()


def procesar_fila(row, base_url, session, download_folder):
    global pdf_descargados, xml_descargados
    if cerrar_app:
        return
    serie_num = f"{row.get('serie', 'NA')}-{row.get('numero', 'NA')}"
    pdf_link = row.get('urlpdf')
    xml_link = row.get('urlxml')

    if pdf_link and pdf_link.startswith('/'):
        pdf_link = base_url + pdf_link.lstrip('/')
    if xml_link and xml_link.startswith('/'):
        xml_link = base_url + xml_link.lstrip('/')

    if descargar_pdf.get() and pdf_link:
        descargar_archivo(session, pdf_link, f"{serie_num}.pdf", download_folder)
        pdf_descargados += 1
        pdf_label.config(text=f"PDF Descargados: {pdf_descargados}")

    if descargar_xml.get() and xml_link:
        descargar_archivo(session, xml_link, f"{serie_num}.xml", download_folder)
        xml_descargados += 1
        xml_label.config(text=f"XML Descargados: {xml_descargados}")


def procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder):
    if cerrar_app:
        return
    payload_facturas["pCurrentPage"] = str(page)
    payload_facturas["pPageSize"] = str(pagsize)
    resp = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp.json()

    with ThreadPoolExecutor(max_workers=20) as executor:
        for row in data.get("rows", []):
            executor.submit(procesar_fila, row, base_url, session, download_folder)


def contar_archivos(session, payload_facturas, facturas_url, pagsize):
    global pdf_encontrados, xml_encontrados, total_registros
    pdf_encontrados = 0
    xml_encontrados = 0

    resp_facturas = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp_facturas.json()
    total_registros = data.get("records", 0)
    total_paginas = (total_registros + pagsize - 1) // pagsize

    for page in range(1, total_paginas + 1):
        payload_facturas["pCurrentPage"] = str(page)
        payload_facturas["pPageSize"] = str(pagsize)
        resp = session.post(facturas_url, data=payload_facturas, headers=headers)
        data = resp.json()

        for row in data.get("rows", []):
            if row.get("urlpdf"):
                pdf_encontrados += 1
            if row.get("urlxml"):
                xml_encontrados += 1

    pdf_encontrados_label.config(text=f"PDF encontrados: {pdf_encontrados}")
    xml_encontrados_label.config(text=f"XML encontrados: {xml_encontrados}")


def mostrar_final(download_folder):
    final_win = tk.Toplevel(root)
    final_win.title("Proceso finalizado")
    final_win.resizable(False, False)

    tk.Label(
        final_win,
        text=f"✅ Descarga finalizada\n\n"
             f"Archivos descargados: {facturas_descargadas}\n"
             f"Archivos con error: {facturas_fallidas}\n\n"
             f"Archivos guardados en:\n{download_folder}",
    ).pack()

    def cerrar_ventana_final():
        final_win.destroy()

    tk.Button(final_win, text="Aceptar", command=cerrar_ventana_final).pack(pady=30)
    final_win.protocol("WM_DELETE_WINDOW", cerrar_ventana_final)


def iniciar_descarga():
    global facturas_descargadas, facturas_fallidas, total_registros
    global cerrar_app, pdf_descargados, xml_descargados, session

    pdf_descargados = 0
    xml_descargados = 0
    facturas_descargadas = 0
    facturas_fallidas = 0
    cerrar_app = False

    fstart = entry_fstart.get().strip()
    fend = entry_fend.get().strip()
    fserie = entry_fserie.get().strip()
    fruc = entry_fruc.get().strip()

    pdf_label.config(text=f"PDF Descargados: {pdf_descargados}")
    xml_label.config(text=f"XML Descargados: {xml_descargados}")
    progress['value'] = 0

    if not fstart or not fend:
        messagebox.showerror("Error", "Debes ingresar fecha de inicio y final.")
        return

    download_folder = filedialog.askdirectory(title="Selecciona carpeta")
    if not download_folder:
        download_folder = os.path.join(os.path.expanduser("~"), "FacturasDescargadas")
    os.makedirs(download_folder, exist_ok=True)

    session = requests.Session()
    payload_login = {
        "module": "mdlaccess",
        "fruc": "20526276486",
        "flogin": "adminmiraflores@gmail.com",
        "fclave": "123456"
    }
    session.post(login_url, data=payload_login, headers=headers)

    base_url = "https://facturacalvicperu.com/fealvic/factura/BL/"
    payload_facturas = {
        "pCurrentPage": '1', "pPageSize": '100', "order": 'f_emision desc',
        "action": 'mdlLoadData2', "fstart": fstart, "fend": fend,
        "ftipdoc": '', "festado": '', "fserie": fserie,
        "fnumDesde":'', "fnumHasta": '',
        "fusuario": '', "fruc": fruc, "festacion": ''
    }

    pagsize = 100
    contar_archivos(session, payload_facturas.copy(), facturas_url, pagsize)

    total_paginas = (total_registros + pagsize - 1) // pagsize
    progress['maximum'] = total_registros
    for page in range(1, total_paginas + 1):
        if cerrar_app:
            break
        procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder)

    if not cerrar_app:
        mostrar_final(download_folder)


# ============================================================
# FUNCIONES DE DESCARGA (PESTAÑA 2 INDEPENDIENTE)
# ============================================================

def descargar_archivo2(session, url, nombre_archivo, download_folder):
    global facturas_descargadas2, facturas_fallidas2, cerrar_app2
    if cerrar_app2:
        return
    try:
        r = session.get(url)
        if r.status_code == 200:
            ruta = os.path.join(download_folder, nombre_archivo)
            with open(ruta, 'wb') as f:
                f.write(r.content)
            facturas_descargadas2 += 1
        else:
            facturas_fallidas2 += 1
    except:
        facturas_fallidas2 += 1

    progress2['value'] = facturas_descargadas2 + facturas_fallidas2
    root.update_idletasks()


def procesar_fila2(row, base_url, session, download_folder):
    global pdf_descargados2, xml_descargados2
    if cerrar_app2:
        return
    serie_num = f"{row.get('serie', 'NA')}-{row.get('numero', 'NA')}"
    pdf_link = row.get('urlpdf')
    xml_link = row.get('urlxml')

    if pdf_link and pdf_link.startswith('/'):
        pdf_link = base_url + pdf_link.lstrip('/')
    if xml_link and xml_link.startswith('/'):
        xml_link = base_url + xml_link.lstrip('/')

    if descargar_pdf2.get() and pdf_link:
        descargar_archivo2(session, pdf_link, f"{serie_num}.pdf", download_folder)
        pdf_descargados2 += 1
        pdf_label2.config(text=f"PDF Descargados: {pdf_descargados2}")

    if descargar_xml2.get() and xml_link:
        descargar_archivo2(session, xml_link, f"{serie_num}.xml", download_folder)
        xml_descargados2 += 1
        xml_label2.config(text=f"XML Descargados: {xml_descargados2}")


def procesar_pagina2(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder):
    if cerrar_app2:
        return
    payload_facturas["pCurrentPage"] = str(page)
    payload_facturas["pPageSize"] = str(pagsize)
    resp = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp.json()

    with ThreadPoolExecutor(max_workers=20) as executor:
        for row in data.get("rows", []):
            executor.submit(procesar_fila2, row, base_url, session, download_folder)


def contar_archivos2(session, payload_facturas, facturas_url, pagsize):
    global total_registros2
    global pdf_descargados2, xml_descargados2
    pdf_count = 0
    xml_count = 0
    resp_facturas = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp_facturas.json()
    total_registros2 = data.get("records", 0)
    total_paginas = (total_registros2 + pagsize - 1) // pagsize

    for page in range(1, total_paginas + 1):
        payload_facturas["pCurrentPage"] = str(page)
        payload_facturas["pPageSize"] = str(pagsize)
        resp = session.post(facturas_url, data=payload_facturas, headers=headers)
        data = resp.json()
        for row in data.get("rows", []):
            if row.get("urlpdf"):
                pdf_count += 1
            if row.get("urlxml"):
                xml_count += 1
    # No estamos actualizando labels de encontrados en esta pestaña, opcional


def mostrar_final2(download_folder):
    final_win = tk.Toplevel(root)
    final_win.title("Proceso finalizado")
    final_win.resizable(False, False)

    tk.Label(
        final_win,
        text=f"✅ Descarga finalizada (Pestaña 2)\n\n"
             f"Archivos descargados: {facturas_descargadas2}\n"
             f"Archivos con error: {facturas_fallidas2}\n\n"
             f"Archivos guardados en:\n{download_folder}",
    ).pack()

    def cerrar_ventana_final():
        final_win.destroy()

    tk.Button(final_win, text="Aceptar", command=cerrar_ventana_final).pack(pady=30)
    final_win.protocol("WM_DELETE_WINDOW", cerrar_ventana_final)


def iniciar_descarga2():
    global facturas_descargadas2, facturas_fallidas2, total_registros2
    global cerrar_app2, pdf_descargados2, xml_descargados2, session2

    pdf_descargados2 = 0
    xml_descargados2 = 0
    facturas_descargadas2 = 0
    facturas_fallidas2 = 0
    cerrar_app2 = False

    fstart = entry_fstart2.get().strip()
    fend = entry_fend2.get().strip()
    fserie = entry_fserie2.get().strip()
    fruc = entry_fruc2.get().strip()

    pdf_label2.config(text=f"PDF Descargados: {pdf_descargados2}")
    xml_label2.config(text=f"XML Descargados: {xml_descargados2}")
    progress2['value'] = 0

    if not fstart or not fend:
        messagebox.showerror("Error", "Debes ingresar fecha de inicio y final.")
        return

    download_folder = filedialog.askdirectory(title="Selecciona carpeta")
    if not download_folder:
        download_folder = os.path.join(os.path.expanduser("~"), "FacturasDescargadas2")
    os.makedirs(download_folder, exist_ok=True)

    session2 = requests.Session()
    payload_login = {
        "module": "mdlaccess",
        "fruc": "20526276486",
        "flogin": "adminmiraflores@gmail.com",
        "fclave": "123456"
    }
    session2.post(login_url, data=payload_login, headers=headers)

    base_url = "https://facturacalvicperu.com/fealvic/factura/BL/"
    payload_facturas = {
        "pCurrentPage": '1', "pPageSize": '100', "order": 'f_emision desc',
        "action": 'mdlLoadData2', "fstart": fstart, "fend": fend,
        "ftipdoc": '', "festado": '', "fserie": fserie,
        "fnumDesde":'', "fnumHasta": '',
        "fusuario": '', "fruc": fruc, "festacion": ''
    }

    pagsize = 100
    contar_archivos2(session2, payload_facturas.copy(), facturas_url, pagsize)

    total_paginas = (total_registros2 + pagsize - 1) // pagsize
    progress2['maximum'] = total_registros2
    for page in range(1, total_paginas + 1):
        if cerrar_app2:
            break
        procesar_pagina2(session2, payload_facturas, page, pagsize, facturas_url, base_url, download_folder)

    if not cerrar_app2:
        mostrar_final2(download_folder)


# ============================================================
# GUI PRINCIPAL CON PESTAÑAS
# ============================================================

root = tk.Tk()
root.title("Descarga de Facturas con Pestañas")

notebook = ttk.Notebook(root)
notebook.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

tab1 = ttk.Frame(notebook)
tab2 = ttk.Frame(notebook)

notebook.add(tab1, text="Descarga")
notebook.add(tab2, text="Pestaña 2")

# ----------------- PESTAÑA 1 -----------------
descargar_pdf = tk.BooleanVar(value=True)
descargar_xml = tk.BooleanVar(value=True)

tk.Label(tab1, text="  Fecha inicio:").grid(row=0, column=0, sticky="w")
entry_fstart = DateEntry(tab1, date_pattern='dd/mm/yyyy')
entry_fstart.grid(row=0, column=1)

tk.Label(tab1, text="  Fecha fin:").grid(row=1, column=0, sticky="w")
entry_fend = DateEntry(tab1, date_pattern='dd/mm/yyyy')
entry_fend.grid(row=1, column=1)

tk.Label(tab1, text="Serie de factura:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
entry_fserie = tk.Entry(tab1, width=15)
entry_fserie.grid(row=2, column=1, padx=5, pady=5)

tk.Label(tab1, text="RUC Cliente:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
entry_fruc = tk.Entry(tab1, width=15)
entry_fruc.grid(row=3, column=1, padx=5, pady=5)

tk.Checkbutton(tab1, text="Descargar PDF", variable=descargar_pdf).grid(row=5, column=0, padx=5, pady=5, sticky="w")
tk.Checkbutton(tab1, text="Descargar XML", variable=descargar_xml).grid(row=5, column=1, padx=5, pady=5, sticky="w")

pdf_encontrados_label = tk.Label(tab1, text="PDF encontrados: 0", width=20)
pdf_encontrados_label.grid(row=6, column=0, sticky="w", padx=10)
xml_encontrados_label = tk.Label(tab1, text="XML encontrados: 0", width=20)
xml_encontrados_label.grid(row=6, column=1, sticky="w", padx=10)

pdf_label = tk.Label(tab1, text="PDF Descargados: 0", width=20)
pdf_label.grid(row=7, column=0, sticky="w", padx=10)
xml_label = tk.Label(tab1, text="XML Descargados: 0", width=20)
xml_label.grid(row=7, column=1, sticky="w", padx=10)

btn_descargar = tk.Button(tab1, text="Iniciar descarga", command=lambda: threading.Thread(target=iniciar_descarga).start())
btn_descargar.grid(row=8, column=0, columnspan=4, pady=20)

progress = ttk.Progressbar(tab1, orient="horizontal", length=400, mode="determinate")
progress.grid(row=9, column=0, columnspan=4, pady=10)

# ----------------- PESTAÑA 2 -----------------
descargar_pdf2 = tk.BooleanVar(value=True)
descargar_xml2 = tk.BooleanVar(value=True)

tk.Label(tab2, text="  Fecha inicio:").grid(row=0, column=0, sticky="w")
entry_fstart2 = DateEntry(tab2, date_pattern='dd/mm/yyyy')
entry_fstart2.grid(row=0, column=1)

tk.Label(tab2, text="  Fecha fin:").grid(row=1, column=0, sticky="w")
entry_fend2 = DateEntry(tab2, date_pattern='dd/mm/yyyy')
entry_fend2.grid(row=1, column=1)

tk.Label(tab2, text="Serie de factura:").grid(row=2, column=0, sticky="w")
entry_fserie2 = tk.Entry(tab2, width=15)
entry_fserie2.grid(row=2, column=1)

tk.Label(tab2, text="RUC Cliente:").grid(row=3, column=0, sticky="w")
entry_fruc2 = tk.Entry(tab2, width=15)
entry_fruc2.grid(row=3, column=1)

tk.Checkbutton(tab2, text="Descargar PDF", variable=descargar_pdf2).grid(row=5, column=0, sticky="w")
tk.Checkbutton(tab2, text="Descargar XML", variable=descargar_xml2).grid(row=5, column=1, sticky="w")

pdf_label2 = tk.Label(tab2, text="PDF Descargados: 0")
pdf_label2.grid(row=6, column=0, sticky="w")
xml_label2 = tk.Label(tab2, text="XML Descargados: 0")
xml_label2.grid(row=6, column=1, sticky="w")

progress2 = ttk.Progressbar(tab2, orient="horizontal", length=400, mode="determinate")
progress2.grid(row=7, column=0, columnspan=4, pady=10)

btn_descargar2 = tk.Button(tab2, text="Iniciar descarga", command=lambda: threading.Thread(target=iniciar_descarga2).start())
btn_descargar2.grid(row=8, column=0, columnspan=4, pady=10)

# ============================================================
# CIERRE SEGURO
# ============================================================

def on_close():
    global cerrar_app, cerrar_app2, session, session2
    cerrar_app = True
    cerrar_app2 = True
    try:
        if session:
            session.close()
        if session2:
            session2.close()
    except:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
