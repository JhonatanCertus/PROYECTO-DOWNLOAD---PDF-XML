import requests
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
import threading

# ======================
# VARIABLES GLOBALES
# ======================
session2 = None
cerrar_app2 = False

# ======================
# FUNCIONES
# ======================
def listar_facturas_optimo():
    global session2, cerrar_app2
    session2 = requests.Session()

    # Login (igual que pestaña 2 real)
    payload_login = {
        "module": "mdlaccess",
        "fruc": "20526276486",
        "flogin": "adminmiraflores@gmail.com",
        "fclave": "123456"
    }
    session2.post("https://facturacalvicperu.com/fealvic/factura/BL/BL_principal.php", data=payload_login)

    # Payload para listar facturas
    fstart = entry_fstart2.get()
    fend = entry_fend2.get()
    fserie = entry_fserie2.get()
    fruc = entry_fruc2.get()

    payload_facturas = {
        "pCurrentPage": '1', 
        "pPageSize": '1000',  # Alto para minimizar número de requests
        "order": 'f_emision desc',
        "action": 'mdlLoadData2',
        "fstart": fstart, "fend": fend,
        "ftipdoc": '', "festado": '',  # Filtrado opcional
        "fserie": fserie,
        "fnumDesde":'', "fnumHasta": '',
        "fusuario": '', "fruc": fruc, "festacion": ''
    }

    resp = session2.post("https://facturacalvicperu.com/fealvic/factura/BL/BL_principal2.php", data=payload_facturas)
    data = resp.json()

    # Limpiar treeview
    for item in tree.get_children():
        tree.delete(item)

    # Listar facturas y mostrar el formato completo en JSON por registro
    for row in data.get("rows", []):
        serie_num = f"{row.get('serie', 'NA')}-{row.get('numero', 'NA')}"
        fecha = row.get("f_emision", "")
        estado = row.get("festado", "")
        pdf = "Sí" if row.get("urlpdf") else "No"
        xml = "Sí" if row.get("urlxml") else "No"

        # Insertar en Treeview
        tree.insert("", "end", values=(serie_num, fecha, estado, pdf, xml))

        # Imprimir registro completo en consola para ver formato
        print(row)

# ======================
# GUI
# ======================
root = tk.Tk()
root.title("Listado Optimizado de Facturas - Pestaña 2 Test")

# Entradas
tk.Label(root, text="Fecha inicio:").grid(row=0, column=0, sticky="w")
entry_fstart2 = DateEntry(root, date_pattern='dd/mm/yyyy')
entry_fstart2.grid(row=0, column=1)

tk.Label(root, text="Fecha fin:").grid(row=1, column=0, sticky="w")
entry_fend2 = DateEntry(root, date_pattern='dd/mm/yyyy')
entry_fend2.grid(row=1, column=1)

tk.Label(root, text="Serie:").grid(row=2, column=0, sticky="w")
entry_fserie2 = tk.Entry(root)
entry_fserie2.grid(row=2, column=1)

tk.Label(root, text="RUC:").grid(row=3, column=0, sticky="w")
entry_fruc2 = tk.Entry(root)
entry_fruc2.grid(row=3, column=1)

# Botón listar
btn_listar = tk.Button(root, text="Listar facturas", command=lambda: threading.Thread(target=listar_facturas_optimo).start())
btn_listar.grid(row=4, column=0, columnspan=2, pady=10)

# Treeview para mostrar resultados
cols = ("Serie-Num", "Fecha", "Estado", "PDF", "XML")
tree = ttk.Treeview(root, columns=cols, show="headings")
for col in cols:
    tree.heading(col, text=col)
tree.grid(row=5, column=0, columnspan=2, pady=10)

# Cierre seguro
def on_close():
    global cerrar_app2, session2
    cerrar_app2 = True
    try:
        if session2:
            session2.close()
    except:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
