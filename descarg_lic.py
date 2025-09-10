# ============================================================
# DESCARGA DE FACTURAS - VERSIÓN COMPLETA CON LICENCIA AES-128
# ============================================================
# Observación: 
# Esta versión valida licencia en base64 antes de permitir el acceso.
# ============================================================

import os
import json
import base64
import threading
import requests
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkcalendar import DateEntry
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ============================================================
# CONFIGURACIÓN DE CIFRADO
# ============================================================
# Clave AES-128 (16 bytes exactos)
AES_KEY = b"MiClaveSegura123"  # 16 bytes exactos
AES_MODE = AES.MODE_ECB

# ============================================================
# FUNCIONES DE LICENCIA
# ============================================================

def descifrar_licencia(licencia_b64):
    """
    Descifra la licencia en base64 y devuelve un diccionario.
    """
    try:
        licencia_b64 = licencia_b64.strip().replace("\n", "")  # limpiar saltos de línea
        cipher = AES.new(AES_KEY, AES_MODE)
        ciphertext = base64.b64decode(licencia_b64)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        licencia = json.loads(decrypted.decode("utf-8"))
        return licencia
    except Exception as e:
        raise ValueError(f"Licencia inválida o corrupta: {e}")

def validar_licencia(licencia):
    """
    Valida que la licencia esté activa y no expirada.
    """
    fecha_fin = licencia.get("fecha_fin")
    activo = licencia.get("activo", False)
    usuario = licencia.get("usuario", "Desconocido")

    if not fecha_fin or not activo:
        return False, "Licencia inactiva o inválida"

    fecha_fin_dt = datetime.fromisoformat(fecha_fin)
    if datetime.now() > fecha_fin_dt:
        return False, f"Licencia expirada el {fecha_fin_dt.date()}"

    return True, f"Licencia válida para {usuario} hasta {fecha_fin_dt.date()}"

def pedir_licencia():
    """
    Pide al usuario que copie y pegue su licencia en base64 y valida acceso.
    """
    root = tk.Tk()
    root.withdraw()  # Oculta ventana principal
    licencia_b64 = simpledialog.askstring("Licencia", "Ingrese su licencia (copiar y pegar):")
    if not licencia_b64:
        messagebox.showerror("Error", "No ingresó ninguna licencia")
        exit()
    try:
        licencia = descifrar_licencia(licencia_b64)
    except ValueError as e:
        messagebox.showerror("Error", str(e))
        exit()
    valido, mensaje = validar_licencia(licencia)
    if not valido:
        messagebox.showerror("Licencia inválida", mensaje)
        exit()
    messagebox.showinfo("Licencia válida", mensaje)
    return licencia

# ============================================================
# VARIABLES GLOBALES DE DESCARGA
# ============================================================
facturas_descargadas = 0
facturas_fallidas = 0
cerrar_app = False
total_registros = 0
descargar_pdf = None
descargar_xml = None

# URLs y headers
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
    Descarga PDF o XML y actualiza barra de progreso.
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
    Procesa una fila de factura y descarga archivos según selección.
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
    if descargar_pdf.get() and pdf_link:
        descargar_archivo(session, pdf_link, f"{serie_num}.pdf", download_folder)
    if descargar_xml.get() and xml_link:
        descargar_archivo(session, xml_link, f"{serie_num}.xml", download_folder)

def procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder):
    """
    Procesa una página de facturas en paralelo usando hilos.
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

def mostrar_final(download_folder):
    """
    Muestra ventana final con resumen de la descarga.
    """
    final_win = tk.Toplevel(root)
    final_win.title("Proceso finalizado")
    final_win.resizable(False, False)
    tk.Label(final_win, text=f"✅ Descarga finalizada\n\n"
                             f"Archivos descargados: {facturas_descargadas}\n"
                             f"Archivos con error: {facturas_fallidas}\n\n"
                             f"Archivos guardados en:\n{download_folder}").pack()
    tk.Button(final_win, text="Aceptar", command=final_win.destroy).pack(pady=30)
    final_win.protocol("WM_DELETE_WINDOW", final_win.destroy)

# ============================================================
# FUNCION PRINCIPAL DE INTERFAZ DE DESCARGA
# ============================================================

def iniciar_descarga_gui():
    """
    Recolecta datos del formulario, inicia sesión y descarga facturas.
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

    # Login simulado
    session = requests.Session()
    payload_login = {"module": "mdlaccess", "fruc": "20526276486",
                     "flogin": "adminmiraflores@gmail.com", "fclave": "123456"}
    session.post(login_url, data=payload_login, headers=headers)

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

    for page in range(1, total_paginas + 1):
        if cerrar_app:
            break
        procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder)

    if not cerrar_app:
        mostrar_final(download_folder)

# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

# Validar licencia antes de iniciar la app
licencia_usuario = pedir_licencia()

# ============================================================
# GUI PRINCIPAL
# ============================================================

root = tk.Tk()
root.title("Descarga de Facturas")
descargar_pdf = tk.BooleanVar(value=True)
descargar_xml = tk.BooleanVar(value=True)

# Entradas de formulario
tk.Label(root, text="Fecha inicio:").grid(row=0, column=0)
entry_fstart = DateEntry(root, date_pattern='dd/mm/yyyy')
entry_fstart.grid(row=0, column=1)

tk.Label(root, text="Fecha fin:").grid(row=1, column=0)
entry_fend = DateEntry(root, date_pattern='dd/mm/yyyy')
entry_fend.grid(row=1, column=1)

tk.Label(root, text="Serie de factura:").grid(row=2, column=0)
entry_fserie = tk.Entry(root, width=15)
entry_fserie.grid(row=2, column=1)

tk.Label(root, text="Desde Nro:").grid(row=3, column=0)
entry_fnumDesde = tk.Entry(root, width=15)
entry_fnumDesde.grid(row=3, column=1)

tk.Label(root, text="Hasta Nro:").grid(row=3, column=2)
entry_fnumHasta = tk.Entry(root, width=15)
entry_fnumHasta.grid(row=3, column=3)

tk.Label(root, text="RUC Cliente:").grid(row=4, column=0)
entry_fruc = tk.Entry(root, width=15)
entry_fruc.grid(row=4, column=1)

# Checkbuttons
tk.Checkbutton(root, text="Descargar PDF", variable=descargar_pdf).grid(row=5, column=0, sticky="w")
tk.Checkbutton(root, text="Descargar XML", variable=descargar_xml).grid(row=5, column=1, sticky="w")

# Botón de descarga
btn_descargar = tk.Button(root, text="Iniciar descarga",
                          command=lambda: threading.Thread(target=iniciar_descarga_gui).start())
btn_descargar.grid(row=7, column=0, columnspan=4, pady=20)

# Barra de progreso
progress_label = tk.Label(root, text="0/0", anchor="e", width=20)
progress_label.grid(row=8, column=3, sticky="e", padx=10)
progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress.grid(row=9, column=0, columnspan=4, pady=10)

# Manejo de cierre de ventana
def on_close():
    global cerrar_app
    cerrar_app = True
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
