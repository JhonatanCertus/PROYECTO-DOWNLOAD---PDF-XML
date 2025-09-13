# ============================================================
# PROYECTO DESCARGA Y LISTADO DE FACTURAS
# Pestaña 1: Descarga PDF/XML
# Pestaña 2: Listado y filtrado por estado interno
# ============================================================

import requests
import os
import json
import urllib3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkcalendar import DateEntry
from concurrent.futures import ThreadPoolExecutor
import threading
import pandas as pd

# ------------------------------------------------------------
# Ignorar warnings de SSL (certificado expirado) — comportamiento
# igual que en tu versión original que funcionaba en tu equipo.
# ------------------------------------------------------------
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# CARGAR CONFIGURACIÓN DE LOGIN DESDE JSON
# ============================================================
CONFIG_PATH = "config.json"
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        login_config = json.load(f)
except FileNotFoundError:
    messagebox.showerror("Error", f"No se encontró el archivo {CONFIG_PATH}.")
    raise SystemExit(f"No se encontró el archivo {CONFIG_PATH}.")
except json.JSONDecodeError:
    messagebox.showerror("Error", f"El archivo {CONFIG_PATH} no tiene un formato JSON válido.")
    raise SystemExit(f"El archivo {CONFIG_PATH} no tiene un formato JSON válido.")

# ============================================================
# VARIABLES GLOBALES
# ============================================================
facturas_descargadas = 0
facturas_fallidas = 0
cerrar_app = False      # Para detener descargas si se cierra la ventana
total_registros = 0     

# Contadores para encontrados y descargados
pdf_encontrados = 0
xml_encontrados = 0
pdf_descargados = 0 
xml_descargados = 0

# Variables de checkboxes (se inicializan más abajo en GUI)
descargar_pdf = None
descargar_xml = None

# Sesiones HTTP (globales)
session = None
session2 = None

# URLs y cabeceras (mantengo las tuyas)
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
# Crear sesión global e iniciar sesión (usa config.json)
# ============================================================
def crear_sesion_inicial():
    global session
    session = requests.Session()
    payload_login = {
        "module": "mdlaccess",
        "fruc": login_config.get("fruc", ""),
        "flogin": login_config.get("flogin", ""),
        "fclave": login_config.get("fclave", "")
    }
    # Ignorar verificación SSL como en tu entorno original
    try:
        session.post(login_url, data=payload_login, headers=headers, verify=False, timeout=15)
    except Exception:
        # No detener la app aquí; las funciones manejarán errores posteriores
        pass

# Crear sesión al inicio
crear_sesion_inicial()

# ============================================================
# FUNCIONES DE DESCARGA PESTAÑA 1
# ============================================================
def descargar_archivo(session_obj, url, nombre_archivo, download_folder):
    global facturas_descargadas, facturas_fallidas, cerrar_app
    if cerrar_app:
        return
    try:
        # Ignorar verificación SSL (para servidor con certificado vencido)
        r = session_obj.get(url, verify=False, timeout=30)
        if r.status_code == 200:
            ruta = os.path.join(download_folder, nombre_archivo)
            with open(ruta, 'wb') as f:
                f.write(r.content)
            facturas_descargadas += 1
        else:
            facturas_fallidas += 1
    except Exception:
        facturas_fallidas += 1

    # Actualizar barra de progreso (UI)
    try:
        progress['value'] = facturas_descargadas + facturas_fallidas
        root.update_idletasks()
    except Exception:
        pass


def procesar_fila(row, base_url, session_obj, download_folder):
    global pdf_descargados, xml_descargados
    if cerrar_app:
        return

    serie_num = f"{row.get('serie', 'NA')}-{row.get('numero', 'NA')}"
    pdf_link = row.get('urlpdf')
    xml_link = row.get('urlxml')

    # Ajustar URLs relativas
    if pdf_link and pdf_link.startswith('/'):
        pdf_link = base_url + pdf_link.lstrip('/')
    if xml_link and xml_link.startswith('/'):
        xml_link = base_url + xml_link.lstrip('/')

    # Descargar PDF si está habilitado
    if descargar_pdf and descargar_pdf.get() and pdf_link:
        descargar_archivo(session_obj, pdf_link, f"{serie_num}.pdf", download_folder)
        pdf_descargados += 1
        try:
            pdf_label.config(text=f"PDF Descargados: {pdf_descargados}")
        except Exception:
            pass

    # Descargar XML si está habilitado
    if descargar_xml and descargar_xml.get() and xml_link:
        descargar_archivo(session_obj, xml_link, f"{serie_num}.xml", download_folder)
        xml_descargados += 1
        try:
            xml_label.config(text=f"XML Descargados: {xml_descargados}")
        except Exception:
            pass


def procesar_pagina(session_obj, payload_facturas, page, pagsize, facturas_url_local, base_url, download_folder):
    if cerrar_app:
        return
    payload_facturas["pCurrentPage"] = str(page)
    payload_facturas["pPageSize"] = str(pagsize)
    try:
        resp = session_obj.post(facturas_url_local, data=payload_facturas, headers=headers, verify=False, timeout=30)
        data = resp.json()
    except Exception:
        return

    with ThreadPoolExecutor(max_workers=20) as executor:
        for row in data.get("rows", []):
            executor.submit(procesar_fila, row, base_url, session_obj, download_folder)


def contar_archivos(session_obj, payload_facturas, facturas_url_local, pagsize):
    global pdf_encontrados, xml_encontrados, total_registros
    pdf_encontrados = 0
    xml_encontrados = 0

    try:
        resp_facturas = session_obj.post(facturas_url_local, data=payload_facturas, headers=headers, verify=False, timeout=30)
        data = resp_facturas.json()
    except Exception:
        total_registros = 0
        pdf_encontrados_label.config(text=f"PDF encontrados: {pdf_encontrados}")
        xml_encontrados_label.config(text=f"XML encontrados: {xml_encontrados}")
        return

    total_registros = data.get("records", 0)
    total_paginas = (total_registros + pagsize - 1) // pagsize

    for page in range(1, total_paginas + 1):
        payload_facturas["pCurrentPage"] = str(page)
        payload_facturas["pPageSize"] = str(pagsize)
        try:
            resp = session_obj.post(facturas_url_local, data=payload_facturas, headers=headers, verify=False, timeout=30)
            data = resp.json()
        except Exception:
            continue

        for row in data.get("rows", []):
            if row.get("urlpdf"):
                pdf_encontrados += 1
            if row.get("urlxml"):
                xml_encontrados += 1

    # Actualizar labels en pantalla (UI)
    try:
        pdf_encontrados_label.config(text=f"PDF encontrados: {pdf_encontrados}")
        xml_encontrados_label.config(text=f"XML encontrados: {xml_encontrados}")
    except Exception:
        pass


def mostrar_final(download_folder):
    final_win = tk.Toplevel(root)
    final_win.title("Proceso finalizado")
    final_win.resizable(False, False)
    tk.Label(final_win,
             text=f"✅ Descarga finalizada\n\n"
                  f"Archivos descargados: {facturas_descargadas}\n"
                  f"Archivos con error: {facturas_fallidas}\n\n"
                  f"Archivos guardados en:\n{download_folder}").pack()
    tk.Button(final_win, text="Aceptar", command=final_win.destroy).pack(pady=30)
    final_win.protocol("WM_DELETE_WINDOW", final_win.destroy)


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

    try:
        pdf_label.config(text=f"PDF Descargados: {pdf_descargados}")
        xml_label.config(text=f"XML Descargados: {xml_descargados}")
        progress['value'] = 0
    except Exception:
        pass

    if not fstart or not fend:
        messagebox.showerror("Error", "Debes ingresar fecha de inicio y final.")
        return

    download_folder = filedialog.askdirectory(title="Selecciona carpeta")
    if not download_folder:
        download_folder = os.path.join(os.path.expanduser("~"), "FacturasDescargadas")
    os.makedirs(download_folder, exist_ok=True)

    # Crear sesión HTTP local para este proceso (usa verify=False)
    session = requests.Session()
    payload_login_local = {
        "module": "mdlaccess",
        "fruc": login_config.get("fruc", ""),
        "flogin": login_config.get("flogin", ""),
        "fclave": login_config.get("fclave", "")
    }
    try:
        session.post(login_url, data=payload_login_local, headers=headers, verify=False, timeout=15)
    except Exception:
        # Si falla el login, dejamos que las posteriores requests fallen y se muestren errores
        pass

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
    try:
        progress['maximum'] = total_registros
    except Exception:
        pass

    for page in range(1, total_paginas + 1):
        if cerrar_app:
            break
        procesar_pagina(session, payload_facturas, page, pagsize, facturas_url, base_url, download_folder)

    if not cerrar_app:
        mostrar_final(download_folder)

# ============================================================
# FUNCIONES PESTAÑA 2 - LISTADO
# ============================================================
def listar_facturas_pestana2():
    global session2, cerrar_app2
    # Deshabilitar botón mientras se procesa
    btn_listar.config(state="disabled")
    estado_label.config(text="Estado: Listando facturas...")
    root.update_idletasks()

    session2 = requests.Session()
    cerrar_app2 = False

    # Limpiar tabla antes de listar
    for item in tree2.get_children():
        tree2.delete(item)

    fstart = entry_fstart2.get().strip()
    fend = entry_fend2.get().strip()
    fserie_input = entry_fserie2.get().strip()
    fruc = entry_fruc2.get().strip()
    filtrar_estbaja = solo_estbaja.get()  # True si el checkbox está marcado

    try:
        # Login (session2) usando credenciales desde config.json
        payload_login2 = {
            "module": "mdlaccess",
            "fruc": login_config.get("fruc", ""),
            "flogin": login_config.get("flogin", ""),
            "fclave": login_config.get("fclave", "")
        }
        try:
            session2.post(login_url, data=payload_login2, headers=headers, verify=False, timeout=15)
        except Exception:
            pass

        payload_facturas = {
            "pCurrentPage": '1', "pPageSize": '100', "order": 'f_emision desc',
            "action": 'mdlLoadData2', "fstart": fstart, "fend": fend,
            "ftipdoc": '', "festado": '', "fserie": '',  # siempre vacío para obtener todas
            "fnumDesde":'', "fnumHasta": '',
            "fusuario": '', "fruc": fruc, "festacion": ''
        }

        # Primera consulta para obtener cantidad de registros
        resp = session2.post(facturas_url, data=payload_facturas, headers=headers, verify=False, timeout=30)
        try:
            data = resp.json()
        except Exception:
            messagebox.showerror("Error", "No se pudo obtener datos. Verifica conexión y filtros.")
            estado_label.config(text="Estado: Error al listar")
            btn_listar.config(state="normal")
            return

        total_registros = data.get("records", 0)
        pagsize = 100
        total_paginas = (total_registros + pagsize - 1) // pagsize

        # Recorrer todas las páginas
        for page in range(1, total_paginas + 1):
            if cerrar_app2:
                break
            payload_facturas["pCurrentPage"] = str(page)
            resp_page = session2.post(facturas_url, data=payload_facturas, headers=headers, verify=False, timeout=30)
            try:
                data_page = resp_page.json()
            except Exception:
                continue  # Saltar página si no es JSON válido
            for row in data_page.get("rows", []):
                # Filtro de Serie
                if fserie_input and row.get("serie") != fserie_input:
                    continue
                # Filtro Solo Anulados (estbaja)
                if filtrar_estbaja and row.get("estbaja") != '1':
                    continue
                tree2.insert("", "end", values=(
                    f"{row.get('serie')}-{row.get('numero')}",
                    row.get("f_emision"),
                    row.get("razonsocial"),
                    row.get("estbaja"),
                    row.get("total")
                ))

        estado_label.config(text=f"Estado: Listado finalizado. {len(tree2.get_children())} facturas mostradas")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al listar facturas:\n{e}")
        estado_label.config(text="Estado: Error al listar")
    finally:
        btn_listar.config(state="normal")  # Volver a habilitar el botón

# Asociar botón a la función en un hilo
# (se configura después de definir la UI widgets)
# ============================================================
# GUI PRINCIPAL
# ============================================================
root = tk.Tk()
root.title("Descarga y Listado de Facturas")
root.geometry("800x600")

# Notebook y pestañas
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

tab1 = ttk.Frame(notebook)
tab2 = ttk.Frame(notebook)

notebook.add(tab1, text="Descarga")
notebook.add(tab2, text="Listado")

# ================= PESTAÑA 1 =================
descargar_pdf = tk.BooleanVar(value=True)
descargar_xml = tk.BooleanVar(value=True)

tk.Label(tab1, text="Fecha inicio:").grid(row=0, column=0, sticky="w")
entry_fstart = DateEntry(tab1, date_pattern='dd/mm/yyyy')
entry_fstart.grid(row=0, column=1)

tk.Label(tab1, text="Fecha fin:").grid(row=1, column=0, sticky="w")
entry_fend = DateEntry(tab1, date_pattern='dd/mm/yyyy')
entry_fend.grid(row=1, column=1)

tk.Label(tab1, text="Serie de factura:").grid(row=2, column=0, sticky="w")
entry_fserie = tk.Entry(tab1, width=15)
entry_fserie.grid(row=2, column=1)

tk.Label(tab1, text="RUC Cliente:").grid(row=3, column=0, sticky="w")
entry_fruc = tk.Entry(tab1, width=15)
entry_fruc.grid(row=3, column=1)

tk.Checkbutton(tab1, text="Descargar PDF", variable=descargar_pdf).grid(row=5, column=0, sticky="w")
tk.Checkbutton(tab1, text="Descargar XML", variable=descargar_xml).grid(row=5, column=1, sticky="w")

pdf_encontrados_label = tk.Label(tab1, text="PDF encontrados: 0")
pdf_encontrados_label.grid(row=6, column=0, sticky="w")
xml_encontrados_label = tk.Label(tab1, text="XML encontrados: 0")
xml_encontrados_label.grid(row=6, column=1, sticky="w")

pdf_label = tk.Label(tab1, text="PDF Descargados: 0")
pdf_label.grid(row=7, column=0, sticky="w")
xml_label = tk.Label(tab1, text="XML Descargados: 0")
xml_label.grid(row=7, column=1, sticky="w")

btn_descargar = tk.Button(tab1, text="Iniciar descarga", command=lambda: threading.Thread(target=iniciar_descarga).start())
btn_descargar.grid(row=8, column=0, columnspan=4, pady=20)

progress = ttk.Progressbar(tab1, orient="horizontal", length=400, mode="determinate")
progress.grid(row=9, column=0, columnspan=4, pady=10)

# ================= PESTAÑA 2 =================
tk.Label(tab2, text="Fecha inicio:").grid(row=0, column=0, sticky="w")
entry_fstart2 = DateEntry(tab2, date_pattern='dd/mm/yyyy')
entry_fstart2.grid(row=0, column=1)

tk.Label(tab2, text="Fecha fin:").grid(row=1, column=0, sticky="w")
entry_fend2 = DateEntry(tab2, date_pattern='dd/mm/yyyy')
entry_fend2.grid(row=1, column=1)

tk.Label(tab2, text="Serie:").grid(row=2, column=0, sticky="w")
entry_fserie2 = tk.Entry(tab2, width=15)
entry_fserie2.grid(row=2, column=1)

tk.Label(tab2, text="RUC:").grid(row=3, column=0, sticky="w")
entry_fruc2 = tk.Entry(tab2, width=15)
entry_fruc2.grid(row=3, column=1)

# Checkbox para filtrar solo estbaja = 1
solo_estbaja = tk.BooleanVar(value=False)
tk.Checkbutton(tab2, text="Solo Anulados", variable=solo_estbaja).grid(row=4, column=0, columnspan=2, sticky="w")

# Label de estado
estado_label = tk.Label(tab2, text="Estado: Esperando inicio")
estado_label.grid(row=6, column=0, columnspan=2, sticky="w")

# Botón Listar Facturas
btn_listar = tk.Button(tab2, text="Listar Facturas")
btn_listar.grid(row=6, column=0, columnspan=2, pady=10)

# Treeview para mostrar listado
columns = ("Serie-Numero", "Fecha", "Cliente", "Estado", "Total")
tree2 = ttk.Treeview(tab2, columns=columns, show="headings")
for col in columns:
    tree2.heading(col, text=col)
    tree2.column(col, width=120)
tree2.grid(row=7, column=0, columnspan=2, pady=10)

scrollbar = ttk.Scrollbar(tab2, orient="vertical", command=tree2.yview)
tree2.configure(yscroll=scrollbar.set)
scrollbar.grid(row=7, column=2, sticky='ns')

# Asociar botón a la función en un hilo
btn_listar.config(command=lambda: threading.Thread(target=listar_facturas_pestana2).start())

# ============================================================
# FUNCION EXPORTAR A EXCEL
# ============================================================
def exportar_a_excel():
    filas = tree2.get_children()
    if not filas:
        messagebox.showwarning("Atención", "No hay datos para exportar")
        return

    datos = []
    for f in filas:
        datos.append(tree2.item(f)["values"])

    df = pd.DataFrame(datos, columns=columns)

    ruta_guardar = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                filetypes=[("Archivos Excel", "*.xlsx")])
    if ruta_guardar:
        df.to_excel(ruta_guardar, index=False)
        messagebox.showinfo("Éxito", f"Listado exportado correctamente a:\n{ruta_guardar}")

# Botón exportar Excel
btn_exportar = tk.Button(tab2, text="Exportar a Excel", command=exportar_a_excel)
btn_exportar.grid(row=15, column=0, columnspan=2, pady=10)


# ============================================================
# CIERRE SEGURO
# ============================================================
def on_close():
    global cerrar_app, session, session2
    cerrar_app = True
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
