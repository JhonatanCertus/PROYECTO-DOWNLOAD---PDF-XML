session_local = requests.Session()
login_url = "https://facturacalvicperu.com/fealvic/factura/BL/BL_principal.php"
payload_login = {
    "module": "mdlaccess",
    "fruc": "TU_RUC",
    "clave": "TU_CLAVE"
}

# Hacer login
r = session_local.post(login_url, data=payload_login)
print(r.text[:500])  # Verifica si contiene JSON o HTML