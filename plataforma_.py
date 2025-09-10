import requests
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkcalendar import DateEntry
from concurrent.futures import ThreadPoolExecutor
import threading
from PIL import Image, ImageTk, ImageSequence  # Para animar GIF

# ============================================================
# VARIABLES GLOBALES
# ============================================================
facturas_descargadas = 0
facturas_fallidas = 0
cerrar_app = False  # Control para detener la descarga si se cierra la ventana
total_registros = 0  # Inicializar para evitar errores

# URLs y cabeceras
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

    # Actualizar barra y contador
    progress['value'] = facturas_descargadas + facturas_fallidas
    progress_label.config(text=f"{facturas_descargadas + facturas_fallidas}/{total_registros*2}")
    root.update_idletasks()


def procesar_fila(row, base_url, session, download_folder):
    """
    Procesa una fila de facturas y descarga PDF y XML en paralelo.
    """
    if cerrar_app:
        return
    serie_num = f"{row.get('serie', 'NA')}-{row.get('numero', 'NA')}"
    pdf_link = row.get('urlpdf')
    xml_link = row.get('urlxml')

    if pdf_link and pdf_link.startswith('/'):
        pdf_link = base_url + pdf_link.lstrip('/')
    if xml_link and xml_link.startswith('/'):
        xml_link = base_url + xml_link.lstrip('/')

    if pdf_link:
        descargar_archivo(session, pdf_link, f"{serie_num}.pdf", download_folder)
    if xml_link:
        descargar_archivo(session, xml_link, f"{serie_num}.xml", download_folder)


def procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder):
    """
    Procesa una página de facturas con descargas paralelas.
    """
    if cerrar_app:
        return
    payload_facturas["pCurrentPage"] = str(page)
    payload_facturas["pPageSize"] = str(pagsize)
    resp = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp.json()
    with ThreadPoolExecutor(max_workers=5) as executor:
        for row in data.get("rows", []):
            executor.submit(procesar_fila, row, base_url, session, download_folder)

# ============================================================
# VENTANA FINAL CON GIF ANIMADO
# ============================================================

def mostrar_final(download_folder):
    """
    Ventana emergente con GIF animado y resumen final.
    """
    final_win = tk.Toplevel(root)
    final_win.title("Proceso finalizado")
  
    final_win.resizable(False, False)

    # Texto resumen
    tk.Label(
        final_win,
        text=f"✅ Descarga finalizada\n\n"
             f"Facturas descargadas: {facturas_descargadas}\n"
             f"Facturas con error: {facturas_fallidas}\n\n"
             f"Archivos guardados en:\n{download_folder}",

    ).pack()

    # Botón cerrar (cierra todo)
    def cerrar_todo():
        global cerrar_app
        cerrar_app = True
        final_win.destroy()
        root.destroy()

    tk.Button(final_win, text="Aceptar", command=cerrar_todo).pack(pady=30)

    final_win.protocol("WM_DELETE_WINDOW", cerrar_todo)

# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def iniciar_descarga():
    """
    Maneja login, consulta y descarga de facturas.
    """
    global facturas_descargadas, facturas_fallidas, total_registros, cerrar_app
    facturas_descargadas = 0
    facturas_fallidas = 0
    cerrar_app = False

    fstart = entry_fstart.get().strip()
    fend = entry_fend.get().strip()
    fserie = entry_fserie.get().strip()
    fnumDesde = entry_fnumDesde.get().strip()
    fnumHasta = entry_fnumHasta.get().strip()
    fruc = entry_fruc.get().strip()

    if not fstart or not fend:
        messagebox.showerror("Error", "Debes ingresar fecha de inicio y final.")
        return

    download_folder = filedialog.askdirectory(title="Selecciona carpeta")
    if not download_folder:
        download_folder = os.path.join(os.path.expanduser("~"), "FacturasDescargadas")
    os.makedirs(download_folder, exist_ok=True)

    # Login
    session = requests.Session()
    payload_login = {"module": "mdlaccess", "fruc": "20526276486",
                     "flogin": "adminmiraflores@gmail.com", "fclave": "123456"}
    resp_login = session.post(login_url, data=payload_login, headers=headers)
    if resp_login.status_code != 200:
        messagebox.showerror("Error", "No se pudo iniciar sesión")
        return

    # Payload facturas
    base_url = "https://facturacalvicperu.com/fealvic/factura/BL/"
    payload_facturas = {"pCurrentPage": '1', "pPageSize": '50', "order": 'f_emision desc',
                        "action": 'mdlLoadData2', "fstart": fstart, "fend": fend,
                        "ftipdoc": '', "festado": '', "fserie": fserie,
                        "fnumDesde": fnumDesde, "fnumHasta": fnumHasta,
                        "fusuario": '', "fruc": fruc, "festacion": ''}

    resp_facturas = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp_facturas.json()
    total_registros = data.get("records", 0)
    pagsize = 10
    total_paginas = (total_registros + pagsize - 1) // pagsize

    progress['maximum'] = total_registros * 2
    progress['value'] = 0
    progress_label.config(text=f"0/{total_registros*2}")

    # Descarga todas las páginas
    for page in range(1, total_paginas + 1):
        if cerrar_app:
            break
        procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder)

    if not cerrar_app:
        mostrar_final(download_folder)  # 👉 muestra ventana con GIF

# ============================================================
# GUI PRINCIPAL
# ============================================================

root = tk.Tk()
root.title("Descarga de Facturas")

# Entradas
tk.Label(root, text="Fecha inicio:").grid(row=0, column=0)
entry_fstart = DateEntry(root, date_pattern='dd/mm/yyyy')
entry_fstart.grid(row=0, column=1)

tk.Label(root, text="Fecha fin:").grid(row=1, column=0)
entry_fend = DateEntry(root, date_pattern='dd/mm/yyyy')
entry_fend.grid(row=1, column=1)

tk.Label(root, text="Serie de factura:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
entry_fserie = tk.Entry(root, width=15)
entry_fserie.grid(row=2, column=1, padx=5, pady=5)

tk.Label(root, text="Desde Nro:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
entry_fnumDesde = tk.Entry(root, width=15)
entry_fnumDesde.grid(row=3, column=1, padx=5, pady=5)

tk.Label(root, text="Hasta Nro:").grid(row=3, column=2, sticky="w", padx=5, pady=5)
entry_fnumHasta = tk.Entry(root, width=15)
entry_fnumHasta.grid(row=3, column=3, padx=5, pady=5)

tk.Label(root, text="RUC Cliente:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
entry_fruc = tk.Entry(root, width=15)
entry_fruc.grid(row=4, column=1, padx=5, pady=5)

# Botón iniciar (ejecuta en hilo separado)
btn_descargar = tk.Button(root, text="Iniciar descarga", command=lambda: threading.Thread(target=iniciar_descarga).start())
btn_descargar.grid(row=7, column=0, columnspan=4, pady=20)

# Contador alineado derecha
progress_label = tk.Label(root, text="0/0", anchor="e", width=20)
progress_label.grid(row=8, column=3, sticky="e", padx=10)

# Barra progreso
progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress.grid(row=9, column=0, columnspan=4, pady=10)

# Cierre seguro
def on_close():
    global cerrar_app
    cerrar_app = True
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()
