import os

class Config:
    # Conexión a MySQL (XAMPP)
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///flaskdb.sqlite'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://juand:juandc@isladigital.xyz:3311/f58_juand'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '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'

    # Configuración de Flask-Mail (Gmail)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'david22guerreroml@gmail.com'
    MAIL_PASSWORD = 'akkgsgpjgsqeqfyb'  # contraseña de aplicación (16 dígitos)
    MAIL_DEFAULT_SENDER = 'david22guerreroml@gmail.com'
# --- EN config.py ---

# ...
    # 1. Llave Pública (Ambiente de Pruebas / Sandbox)
    WOMPI_PUBLIC_KEY = 'pub_test_f11B5tW6t8X2A7z2e8O4d9R6q1V3C0Y0' 
    
    # 2. Clave de Integridad (Ambiente de Pruebas / Sandbox)
    WOMPI_INTEGRITY_KEY = 'test_integrity_g7f18F12X6D33H65f3a09F4d7E8d2d9' 
    
    # 3. Llave Privada (Puedes dejar este valor por ahora)
    WOMPI_PRIVATE_KEY = 'prv_test_Q6t4I8h8V7m6P9j1x3M6K2r8L0o5A0b7' 
    
    # 4. URL de Redirección (Debe ser HTTPS en producción, usa tu dominio real)
    WOMPI_REDIRECT_URL = 'https://isladigital.xyz/wompi_events_redirect' 
# ...