# ============================================================
# GENERADOR DE LICENCIAS CIFRADAS - AES-128 ECB + PKCS7
# ============================================================
# Crea licencias temporales o perpetuas y las cifra con AES-128
# Entrega base64 listo para copiar y pegar en la app del cliente
# ============================================================

import json
import uuid
from datetime import datetime, timedelta
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ============================================================
# CONFIGURACIÓN DE CIFRADO
# ============================================================

# Puedes usar cualquier contraseña larga como "clave secreta"
PASSPHRASE = "JWMxx4QRZ9ElaxZYuYVLnsnu9j4pTpVGq+L2Arx3aCHgAIeb+zehjjlwtPUi0g3k9W0x5zIftJegP5wg2vrdX+P0EzG7VOOCD9dU7xR4EMDlxVu9PgPzNEZH9X+A9ItB7L+w3gyX18bUbPTnz3itQyQceGHDBOzQbQNsZasA61Suc4GqmE9mY5seN9TuexgsWZ9GyxDvLH5MaH04e8kt8INXTG8TNc1xjZ54nkDC8cDb4Gj0lP1LlAYwBBi9Ry2"

# Derivar clave AES-128 (16 bytes) de la contraseña larga
AES_KEY = hashlib.md5(PASSPHRASE.encode("utf-8")).digest()  # 16 bytes exactos
AES_MODE = AES.MODE_ECB

# ============================================================
# FUNCIONES
# ============================================================

def generar_id_licencia():
    """Genera un UUID único para la licencia."""
    return str(uuid.uuid4())

def crear_licencia(usuario, tipo, duracion_dias):
    """
    Crea un diccionario con la información de la licencia.
    tipo: "perpetua" o "temporal"
    """
    fecha_inicio = datetime.now()
    fecha_fin = fecha_inicio + timedelta(days=duracion_dias)

    licencia = {
        "id": generar_id_licencia(),
        "usuario": usuario,
        "tipo": tipo,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin": fecha_fin.isoformat(),
        "activo": True
    }
    return licencia

def cifrar_licencia(licencia):
    """
    Convierte el diccionario de licencia en JSON, lo transforma en bytes
    y lo cifra con AES-128 en modo ECB usando PKCS7.
    Devuelve base64 para entregar al cliente.
    """
    data = json.dumps(licencia).encode("utf-8")
    data_padded = pad(data, AES.block_size)  # PKCS7
    cipher = AES.new(AES_KEY, AES_MODE)
    ciphertext = cipher.encrypt(data_padded)
    return base64.b64encode(ciphertext).decode("utf-8")

# ============================================================
# FLUJO PRINCIPAL
# ============================================================

def main():
    print("=== Generador de Licencias Cifradas ===\n")

    usuario = input("Ingrese nombre de usuario/cliente: ").strip()
    tipo = input("Tipo de licencia (perpetua/temporal): ").strip().lower()

    if tipo == "perpetua":
        duracion = 365 * 100  # 100 años
    elif tipo == "temporal":
        duracion = int(input("Duración en días de la licencia: "))
    else:
        print("Tipo no reconocido, se usará 'temporal' de 30 días")
        tipo = "temporal"
        duracion = 30

    licencia = crear_licencia(usuario, tipo, duracion)
    licencia_cifrada = cifrar_licencia(licencia)

    print("\n✅ Licencia generada con éxito!")
    print("Licencia (copiar y pegar en la app del cliente): /n")
    print(licencia_cifrada)

# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()
