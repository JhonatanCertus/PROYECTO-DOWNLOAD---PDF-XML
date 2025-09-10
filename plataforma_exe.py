import requests
import os
import json
import sys
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

# ============================================================
# FUNCIONES
# ============================================================

def descargar_archivo(session, url, nombre_archivo, download_folder):
    """Descarga un archivo PDF o XML"""
    try:
        r = session.get(url)
        if r.status_code == 200:
            ruta = os.path.join(download_folder, nombre_archivo)
            with open(ruta, 'wb') as f:
                f.write(r.content)
            print(f"Archivo descargado: {ruta}")
        else:
            print(f"Error al descargar {nombre_archivo}: {r.status_code}")
    except Exception as e:
        print(f"Excepción al descargar {nombre_archivo}: {e}")

def iniciar_descarga():
    """Función principal que se ejecuta al presionar el botón"""

    # Obtener valores del formulario
    fstart = entry_fstart.get().strip()
    fend = entry_fend.get().strip()
    fserie = entry_fserie.get().strip()
    
    if not fstart or not fend:
        messagebox.showerror("Error", "Debes ingresar fecha de inicio y final.")
        return

    # Selección de carpeta de descarga
    download_folder = filedialog.askdirectory(title="Selecciona la carpeta donde guardar las facturas")
    if not download_folder:
        # Carpeta por defecto si el usuario cancela
        download_folder = os.path.join(os.path.expanduser("~"), "FacturasDescargadas")
    os.makedirs(download_folder, exist_ok=True)
    print(f"Archivos se guardarán en: {download_folder}")

    # Sesión
    session = requests.Session()

    # Datos de login
    payload_login = {
        "module": "mdlaccess",
        "fruc": "20526276486",
        "flogin": "adminmiraflores@gmail.com",
        "fclave": "123456"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://facturacalvicperu.com",
        "Referer": "https://facturacalvicperu.com/fealvic/factura/inicio.php",
    }

    # LOGIN
    resp_login = session.post(login_url, data=payload_login, headers=headers)
    if resp_login.status_code != 200:
        messagebox.showerror("Error", "No se pudo iniciar sesión. Revisa tus credenciales o conexión.")
        return

    # URL y base para convertir links relativos
    base_url = "https://facturacalvicperu.com/fealvic/factura/BL/"
    
    # PAYLOAD inicial para obtener total de registros
    payload_facturas = {
        "pCurrentPage": '1',
        "pPageSize": '10',
        "order": 'f_emision desc',
        "action": 'mdlLoadData2',
        "fstart": fstart,
        "fend": fend,
        "ftipdoc": '',
        "festado": '',
        "fserie": fserie,
        "fnumDesde": '',
        "fnumHasta": '',
        "fusuario": '',
        "fruc": '',
        "festacion": ''
    }

    # Obtener total de registros
    resp_facturas = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp_facturas.json()
    total_registros = data.get("records", 0)
    pagsize = 10
    total_paginas = (total_registros + pagsize - 1) // pagsize

    print(f"Total de registros: {total_registros}, Total páginas: {total_paginas}")

    # Iterar páginas
    for page in range(1, total_paginas + 1):
        print(f"Procesando página {page}/{total_paginas}...")
        payload_facturas["pCurrentPage"] = str(page)
        payload_facturas["pPageSize"] = str(pagsize)

        resp_facturas = session.post(facturas_url, data=payload_facturas, headers=headers)
        data = resp_facturas.json()

        for row in data.get("rows", []):
            serie_num = f"{row.get('serie', 'NA')}-{row.get('numero', 'NA')}"
            pdf_link = row.get('urlpdf')
            xml_link = row.get('urlxml')

            if pdf_link and pdf_link.startswith('/'):
                pdf_link = base_url + pdf_link.lstrip('/')
            if xml_link and xml_link.startswith('/'):
                xml_link = base_url + xml_link.lstrip('/')

            if pdf_link:
                descargar_archivo(session, pdf_link, f"{serie_num}.pdf", download_folder)
            else:
                print(f"No hay PDF para {serie_num}")

            if xml_link:
                descargar_archivo(session, xml_link, f"{serie_num}.xml", download_folder)
            else:
                print(f"No hay XML para {serie_num}")

    messagebox.showinfo("Finalizado", f"Proceso completado. Archivos descargados en:\n{download_folder}")

# ============================================================
# INTERFAZ GRÁFICA
# ============================================================

# URLs
login_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal.php"
facturas_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal2.php"

# Crear ventana principal
root = tk.Tk()
root.title("Descarga de Facturas")

# Labels y entradas
tk.Label(root, text="Fecha inicio (dd/mm/yyyy):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
entry_fstart = tk.Entry(root, width=15)
entry_fstart.grid(row=0, column=1, padx=5, pady=5)

tk.Label(root, text="Fecha fin (dd/mm/yyyy):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
entry_fend = tk.Entry(root, width=15)
entry_fend.grid(row=1, column=1, padx=5, pady=5)

tk.Label(root, text="Serie de factura (opcional):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
entry_fserie = tk.Entry(root, width=15)
entry_fserie.grid(row=2, column=1, padx=5, pady=5)

# Botón para iniciar descarga
btn_descargar = tk.Button(root, text="Iniciar descarga", command=iniciar_descarga)
btn_descargar.grid(row=3, column=0, columnspan=2, pady=10)

# Ejecutar GUI
root.mainloop()
