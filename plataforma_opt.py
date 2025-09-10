import requests
import os
import json
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
from tkcalendar import DateEntry
from concurrent.futures import ThreadPoolExecutor

facturas_descargadas = 0
facturas_fallidas = 0

# ============================================================
# FUNCIONES
# ============================================================

def descargar_archivo(session, url, nombre_archivo, download_folder):
    """Descarga un archivo PDF o XML y guarda en la carpeta indicada."""
    global facturas_descargadas, facturas_fallidas
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

    # Actualizar barra de progreso en la GUI
    progress['value'] = facturas_descargadas + facturas_fallidas
    root.update_idletasks()

def procesar_fila(row, base_url, session, download_folder):
    """Procesa una fila del JSON y descarga PDF y XML."""
    serie_num = f"{row.get('serie', 'NA')}-{row.get('numero', 'NA')}"
    pdf_link = row.get('urlpdf')
    xml_link = row.get('urlxml')

    # Convertir URLs relativas a absolutas
    if pdf_link and pdf_link.startswith('/'):
        pdf_link = base_url + pdf_link.lstrip('/')
    if xml_link and xml_link.startswith('/'):
        xml_link = base_url + xml_link.lstrip('/')

    # Descargar archivos
    if pdf_link:
        descargar_archivo(session, pdf_link, f"{serie_num}.pdf", download_folder)
    else:
        print(f"No hay PDF para {serie_num}")
    if xml_link:
        descargar_archivo(session, xml_link, f"{serie_num}.xml", download_folder)
    else:
        print(f"No hay XML para {serie_num}")

def procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder):
    """Procesa una página completa de facturas."""
    payload_facturas["pCurrentPage"] = str(page)
    payload_facturas["pPageSize"] = str(pagsize)
    resp = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp.json()

    # Usamos ThreadPoolExecutor para descargar archivos en paralelo
    with ThreadPoolExecutor(max_workers=5) as executor:
        for row in data.get("rows", []):
            executor.submit(procesar_fila, row, base_url, session, download_folder)

def iniciar_descarga():
    """Función principal que se ejecuta al presionar el botón."""

    # --- Valores ingresados por usuario ---
    fstart = entry_fstart.get().strip()
    fend = entry_fend.get().strip()
    fserie = entry_fserie.get().strip()
    fnumDesde = entry_fnumDesde.get().strip()
    fnumHasta = entry_fnumHasta.get().strip()
    fruc = entry_fruc.get().strip()

    if not fstart or not fend:
        messagebox.showerror("Error", "Debes ingresar fecha de inicio y final.")
        return

    # --- Carpeta de descarga ---
    download_folder = filedialog.askdirectory(title="Selecciona la carpeta donde guardar las facturas")
    if not download_folder:
        download_folder = os.path.join(os.path.expanduser("~"), "FacturasDescargadas")
    os.makedirs(download_folder, exist_ok=True)
    print(f"Archivos se guardarán en: {download_folder}")

    # --- Sesión y login ---
    session = requests.Session()
    payload_login = {
        "module": "mdlaccess",
        "fruc": "20526276486",
        "flogin": "adminmiraflores@gmail.com",
        "fclave": "123456"
    }
    resp_login = session.post(login_url, data=payload_login, headers=headers)
    if resp_login.status_code != 200:
        messagebox.showerror("Error", "No se pudo iniciar sesión. Revisa tus credenciales o conexión.")
        return

    # --- URLs base ---
    base_url = "https://facturacalvicperu.com/fealvic/factura/BL/"

    # --- Payload inicial para obtener total de registros ---
    payload_facturas = {
        "pCurrentPage": '1',
        "pPageSize": '50',
        "order": 'f_emision desc',
        "action": 'mdlLoadData2',
        "fstart": fstart,
        "fend": fend,
        "ftipdoc": '',
        "festado": '',
        "fserie": fserie,
        "fnumDesde": fnumDesde,
        "fnumHasta": fnumHasta,
        "fusuario": '',
        "fruc": fruc,
        "festacion": ''
    }

    # --- Obtener total de registros para calcular páginas ---
    resp_facturas = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp_facturas.json()
    total_registros = data.get("records", 0)
    pagsize = 10
    total_paginas = (total_registros + pagsize - 1) // pagsize
    print(f"Total de registros: {total_registros}, Total páginas: {total_paginas}")

    # --- Iterar todas las páginas ---
    for page in range(1, total_paginas + 1):
        print(f"Procesando página {page}/{total_paginas}...")
        procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder)

    messagebox.showinfo("Finalizado", f"Proceso completado. Archivos descargados en:\n{download_folder}")

# ============================================================
# INTERFAZ GRÁFICA
# ============================================================

# URLs
login_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal.php"
facturas_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal2.php"
headers = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://facturacalvicperu.com",
    "Referer": "https://facturacalvicperu.com/fealvic/factura/inicio.php",
}

# Crear ventana principal
root = tk.Tk()
root.title("Descarga de Facturas")

# Labels y entradas
tk.Label(root, text="Fecha inicio:").grid(row=0, column=0)
entry_fstart =  DateEntry(root, date_pattern='dd/mm/yyyy')  # calendario
entry_fstart.grid(row=0, column=1)

tk.Label(root, text="Fecha fin:").grid(row=1, column=0)
entry_fend = DateEntry(root, date_pattern='dd/mm/yyyy')
entry_fend.grid(row=1, column=1)

tk.Label(root, text="Serie de factura (opcional):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
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



# Botón para iniciar descarga
btn_descargar = tk.Button(root, text="Iniciar descarga", command=iniciar_descarga)
btn_descargar.grid(row=7, column=1, columnspan=4, pady=20)

# Crear barra de progreso
progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress.grid(row=8, column=0, columnspan=4, pady=10)

progress['maximum'] = total_registros  # total de facturas a procesar
progress['value'] = facturas_descargadas  # facturas descargadas hasta el momento

# Ejecutar GUI
root.mainloop()
