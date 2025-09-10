# ============================================================
# DESCARGADOR DE FACTURAS (PDF/XML)
# Versión optimizada:
# - Evita recorrer el servidor dos veces (conteo + descarga).
# - Usa ThreadPoolExecutor para descargas en paralelo.
# - Barra de progreso dinámica según PDF/XML seleccionados.
# - Cierre seguro de sesión y aplicación.
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
facturas_descargadas = 0
facturas_fallidas = 0
cerrar_app = False      # Control para detener la descarga si se cierra la ventana

# Contadores para encontrados y descargados
pdf_encontrados = 0
xml_encontrados = 0
pdf_descargados = 0
xml_descargados = 0

# Variables de checkboxes
descargar_pdf = None
descargar_xml = None

# Sesión HTTP (global para poder cerrarla)
session = None

# URLs y cabeceras HTTP
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
# FUNCIONES DE DESCARGA
# ============================================================

def descargar_archivo(session, url, nombre_archivo, download_folder):
    """
    Descarga un archivo PDF o XML y actualiza barra de progreso y contador.
    """
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

    # Actualizar barra de progreso
    progress['value'] = facturas_descargadas + facturas_fallidas
    root.update_idletasks()


def procesar_fila(row, base_url, session, download_folder):
    """
    Procesa una fila de facturas y descarga PDF/XML según selección.
    """
    global pdf_descargados, xml_descargados
    if cerrar_app:
        return

    serie_num = f"{row.get('serie', 'NA')}-{row.get('numero', 'NA')}"
    pdf_link = row.get('urlpdf')
    xml_link = row.get('urlxml')

    # Ajustar URLs relativas a absolutas
    if pdf_link and pdf_link.startswith('/'):
        pdf_link = base_url + pdf_link.lstrip('/')
    if xml_link and xml_link.startswith('/'):
        xml_link = base_url + xml_link.lstrip('/')

    # Descargar PDF si está habilitado
    if descargar_pdf.get() and pdf_link:
        descargar_archivo(session, pdf_link, f"{serie_num}.pdf", download_folder)
        pdf_descargados += 1
        pdf_label.config(text=f"PDF Descargados: {pdf_descargados}")

    # Descargar XML si está habilitado
    if descargar_xml.get() and xml_link:
        descargar_archivo(session, xml_link, f"{serie_num}.xml", download_folder)
        xml_descargados += 1
        xml_label.config(text=f"XML Descargados: {xml_descargados}")


def obtener_facturas(session, payload_facturas, pagsize):
    """
    Genera todas las filas de facturas (streaming):
    - Hace una sola pasada por todas las páginas.
    - Evita tener que contar primero y luego volver a recorrer.
    """
    # Primer request para saber cuántos registros hay
    resp = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp.json()
    total_registros = data.get("records", 0)
    total_paginas = (total_registros + pagsize - 1) // pagsize

    # Rendimos la primera página ya obtenida
    for row in data.get("rows", []):
        yield row

    # Recorremos las demás páginas
    for page in range(2, total_paginas + 1):
        if cerrar_app:
            break
        payload_facturas["pCurrentPage"] = str(page)
        payload_facturas["pPageSize"] = str(pagsize)
        resp = session.post(facturas_url, data=payload_facturas, headers=headers)
        data = resp.json()
        for row in data.get("rows", []):
            yield row

# ============================================================
# VENTANA FINAL
# ============================================================

def mostrar_final(download_folder):
    """
    Ventana emergente con resumen final.
    """
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

# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def iniciar_descarga():
    """
    Maneja login, conteo y descarga de facturas (optimizado).
    """
    global facturas_descargadas, facturas_fallidas
    global cerrar_app, pdf_descargados, xml_descargados, session
    global pdf_encontrados, xml_encontrados

    # Resetear contadores
    pdf_descargados = 0
    xml_descargados = 0
    pdf_encontrados = 0
    xml_encontrados = 0
    facturas_descargadas = 0
    facturas_fallidas = 0
    cerrar_app = False

    fstart = entry_fstart.get().strip()
    fend = entry_fend.get().strip()
    fserie = entry_fserie.get().strip()
    fruc = entry_fruc.get().strip()

    # Resetear labels visuales
    pdf_label.config(text="PDF Descargados: 0")
    xml_label.config(text="XML Descargados: 0")
    pdf_encontrados_label.config(text="PDF encontrados: 0")
    xml_encontrados_label.config(text="XML encontrados: 0")
    progress['value'] = 0

    if not fstart or not fend:
        messagebox.showerror("Error", "Debes ingresar fecha de inicio y final.")
        return

    # Carpeta de destino
    download_folder = filedialog.askdirectory(title="Selecciona carpeta")
    if not download_folder:
        download_folder = os.path.join(os.path.expanduser("~"), "FacturasDescargadas")
    os.makedirs(download_folder, exist_ok=True)

    # Crear sesión HTTP
    session = requests.Session()
    payload_login = {
        "module": "mdlaccess",
        "fruc": "20526276486",
        "flogin": "adminmiraflores@gmail.com",
        "fclave": "123456"
    }
    session.post(login_url, data=payload_login, headers=headers)

    # Payload facturas
    base_url = "https://facturacalvicperu.com/fealvic/factura/BL/"
    payload_facturas = {
        "pCurrentPage": '1', "pPageSize": '10', "order": 'f_emision desc',
        "action": 'mdlLoadData2', "fstart": fstart, "fend": fend,
        "ftipdoc": '', "festado": '', "fserie": fserie,
        "fnumDesde": '', "fnumHasta": '',
        "fusuario": '', "fruc": fruc, "festacion": ''
    }

    pagsize = 10

    # ============================================================
    # ✅ Obtener todas las facturas en una sola pasada
    # ============================================================
    filas = list(obtener_facturas(session, payload_facturas.copy(), pagsize))

    # Contar encontrados
    for row in filas:
        if row.get("urlpdf"):
            pdf_encontrados += 1
        if row.get("urlxml"):
            xml_encontrados += 1

    # Mostrar encontrados
    pdf_encontrados_label.config(text=f"PDF encontrados: {pdf_encontrados}")
    xml_encontrados_label.config(text=f"XML encontrados: {xml_encontrados}")

    # Configurar progreso según selección
    if descargar_pdf.get() and descargar_xml.get():
        total_a_descargar = pdf_encontrados + xml_encontrados
    elif descargar_pdf.get():
        total_a_descargar = pdf_encontrados
    elif descargar_xml.get():
        total_a_descargar = xml_encontrados
    else:
        total_a_descargar = 0
    progress['maximum'] = total_a_descargar

    # ============================================================
    # ✅ Descargar en paralelo con un solo ThreadPoolExecutor
    # ============================================================
    with ThreadPoolExecutor(max_workers=20) as executor:
        for row in filas:
            executor.submit(procesar_fila, row, base_url, session, download_folder)

    # Mostrar ventana final
    if not cerrar_app:
        mostrar_final(download_folder)

# ============================================================
# GUI PRINCIPAL
# ============================================================

root = tk.Tk()
root.title("Descarga de Facturas")

# Crear un estilo personalizado para pestañas
style = ttk.Style()
style.configure("Custom.TNotebook.Tab", font=("Helvetica", 7, "bold"))

# Crear notebook con estilo (contenedor de pestañas)
notebook = ttk.Notebook(root, style="Custom.TNotebook")
notebook.pack(fill="both", expand=True)

# ============================================================
# PESTAÑA NRO 01
# ============================================================

tab1 = tk.Frame(notebook)
notebook.add(tab1, text="Descarga Archivos")

# Variables de checkboxes
descargar_pdf = tk.BooleanVar(value=True)
descargar_xml = tk.BooleanVar(value=True)

# Entradas
tk.Label(tab1, text="Fecha inicio:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
entry_fstart = DateEntry(tab1, date_pattern='dd/mm/yyyy')
entry_fstart.grid(row=0, column=1)

tk.Label(tab1, text="Fecha fin:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
entry_fend = DateEntry(tab1, date_pattern='dd/mm/yyyy')
entry_fend.grid(row=1, column=1)

tk.Label(tab1, text="Serie de factura:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
entry_fserie = tk.Entry(tab1, width=15)
entry_fserie.grid(row=2, column=1, padx=5, pady=5)

tk.Label(tab1, text="RUC Cliente:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
entry_fruc = tk.Entry(tab1, width=15)
entry_fruc.grid(row=3, column=1, padx=5, pady=5)

# Checkboxes PDF/XML
tk.Checkbutton(tab1, text="Descargar PDF", variable=descargar_pdf).grid(row=5, column=0, padx=5, pady=5, sticky="w")
tk.Checkbutton(tab1, text="Descargar XML", variable=descargar_xml).grid(row=5, column=1, padx=5, pady=5, sticky="w")

# Labels para visualización
pdf_encontrados_label = tk.Label(tab1, text="PDF encontrados: 0", width=20)
pdf_encontrados_label.grid(row=6, column=0, sticky="w", padx=10)
xml_encontrados_label = tk.Label(tab1, text="XML encontrados: 0", width=20)
xml_encontrados_label.grid(row=6, column=1, sticky="w", padx=10)

pdf_label = tk.Label(tab1, text="PDF Descargados: 0", width=20)
pdf_label.grid(row=7, column=0, sticky="w", padx=10)
xml_label = tk.Label(tab1, text="XML Descargados: 0", width=20)
xml_label.grid(row=7, column=1, sticky="w", padx=10)

# Botón iniciar
btn_descargar = tk.Button(tab1, text="Iniciar descarga", command=lambda: threading.Thread(target=iniciar_descarga).start())
btn_descargar.grid(row=8, column=0, columnspan=4, pady=10)

# Barra progreso
progress = ttk.Progressbar(tab1, orient="horizontal", length=400, mode="determinate")
progress.grid(row=9, column=0, columnspan=4, pady=10)

# ============================================================ 
# # PESTAÑA NRO 02 # 
# ============================================================ 

tab2 = tk.Frame(notebook)
notebook.add(tab2, text="Listado Documentos")

# Entradas
tk.Label(tab2, text="Fecha inicio:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
entry_fstart = DateEntry(tab2, date_pattern='dd/mm/yyyy')
entry_fstart.grid(row=0, column=1)

tk.Label(tab2, text="Fecha fin:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
entry_fend = DateEntry(tab2, date_pattern='dd/mm/yyyy')
entry_fend.grid(row=1, column=1)

tk.Label(tab2, text="Serie de factura:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
entry_fserie = tk.Entry(tab2, width=15)
entry_fserie.grid(row=2, column=1, padx=5, pady=5)

tk.Label(tab2, text="RUC Cliente:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
entry_fruc = tk.Entry(tab2, width=15)
entry_fruc.grid(row=3, column=1, padx=5, pady=5)

# ============================================================
# CIERRE SEGURO
# ============================================================

def on_close():
    """
    Maneja el cierre seguro de la app:
    - Marca la bandera para detener descargas.
    - Cierra la sesión HTTP si existe.
    - Destruye la ventana.
    """
    global cerrar_app, session
    cerrar_app = True
    try:
        if session:
            session.close()   # ✅ Cierra la sesión explícitamente
    except:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
