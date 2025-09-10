import requests
import os
import json

# ============================================================
# INICIO DEL SCRIPT DE SCRAPING DE FACTURAS
# ============================================================

# --- Configuración ---
login_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal.php"
facturas_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal2.php"
base_url = "https://facturacalvicperu.com/fealvic/factura/BL/"

# Carpeta para descargar archivos
os.makedirs("facturas_descargadas", exist_ok=True)

# Sesión para mantener cookies
session = requests.Session()

# Datos de login
payload_login = {
    "module": "mdlaccess",
    "fruc": "20526276486",
    "flogin": "adminmiraflores@gmail.com",
    "fclave": "123456"
}

# Headers para requests
headers = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://facturacalvicperu.com",
    "Referer": "https://facturacalvicperu.com/fealvic/factura/inicio.php",
}

# ============================================================
# LOGIN
# ============================================================
resp_login = session.post(login_url, data=payload_login, headers=headers)
if resp_login.status_code != 200:
    print("Error en login")
    exit()
#print("Login exitoso")

# ============================================================
# FUNCION PARA DESCARGAR ARCHIVOS
# ============================================================
def descargar_archivo(session, url, nombre_archivo):
    r = session.get(url)
    if r.status_code == 200:
        ruta = os.path.join("facturas_descargadas", nombre_archivo)
        with open(ruta, 'wb') as f:
            f.write(r.content)
        print(f"Archivo descargado: {ruta}")
    else:
        print(f"Error al descargar {nombre_archivo}: {r.status_code}")

# ============================================================
# PAYLOAD INICIAL PARA OBTENER TOTAL DE REGISTROS
# ============================================================
payload_facturas = {
    "pCurrentPage": '1',
    "pPageSize": '10',  # puedes aumentar si el servidor soporta más
    "order": 'f_emision desc',
    "action": 'mdlLoadData2',
    "fstart": '09/09/2024',
    "fend": '30/09/2024',
    "ftipdoc": '',
    "festado": '',
    "fserie": 'FM22',
    "fnumDesde": '7336',
    "fnumHasta": '',
    "fusuario": '',
    "fruc": '20603452365',
    "festacion": ''
}

# ============================================================
# OBTENER TOTAL DE REGISTROS Y CALCULAR PAGINAS
# ============================================================
resp_facturas = session.post(facturas_url, data=payload_facturas, headers=headers)
data = resp_facturas.json()
total_registros = data["records"]
pagsize = 10
total_paginas = (total_registros + pagsize - 1) // pagsize

print(f"Total de registros: {total_registros}, Total páginas: {total_paginas}")

# ============================================================
# ITERAR TODAS LAS PAGINAS Y DESCARGAR PDF / XML
# ============================================================
for page in range(1, total_paginas + 1):
    print(f"Procesando página {page}/{total_paginas}...")
    payload_facturas["pCurrentPage"] = str(page)
    payload_facturas["pPageSize"] = str(pagsize)
    
    resp_facturas = session.post(facturas_url, data=payload_facturas, headers=headers)
    data = resp_facturas.json()
    
    for row in data["rows"]:
        serie_num = f"{row['serie']}-{row['numero']}"
        pdf_link = row.get('urlpdf')
        xml_link = row.get('urlxml')

        # ====================================================
        # CONVERTIR URLs RELATIVAS A ABSOLUTAS
        # ====================================================
        if pdf_link and pdf_link.startswith('/'):
            pdf_link = base_url + pdf_link.lstrip('/')
        if xml_link and xml_link.startswith('/'):
            xml_link = base_url + xml_link.lstrip('/')

        # ====================================================
        # DESCARGAR ARCHIVOS
        # ====================================================
        if pdf_link:
            descargar_archivo(session, pdf_link, f"{serie_num}.pdf")
        else:
            print(f"No hay PDF para {serie_num}")
        if xml_link:
            descargar_archivo(session, xml_link, f"{serie_num}.xml")
        else:
            print(f"No hay XML para {serie_num}")

# ============================================================
# FIN DEL SCRIPT
# ============================================================
print("Proceso completado. Todos los archivos descargados en la carpeta 'facturas_descargadas'.")
