import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://juand:juandc@isladigital.xyz:3311/f58_juand'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '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'

    # Configuración de Flask-Mail (Gmail)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'david22guerreroml@gmail.com'
    MAIL_PASSWORD = 'akkgsgpjgsqeqfyb'
    MAIL_DEFAULT_SENDER = 'david22guerreroml@gmail.com'


# 🔹 Configuración de Wompi (fuera de la clase Config)
WOMPI_PUBLIC_KEY = 'pub_prod_rsFWKqoo2nBPc1ywo92AufU32xCP9Vaf'
WOMPI_INTEGRITY_KEY = 'prod_integrity_Wyki3bEfGsCbWSdXDmTO3TNQkeok31hU'
WOMPI_REDIRECT_URL = 'https://levelup.isladigital.xyz/donacion_finalizada'
WOMPI_CURRENCY = 'COP'
