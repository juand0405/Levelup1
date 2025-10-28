from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import WOMPI_PUBLIC_KEY, WOMPI_INTEGRITY_KEY, WOMPI_REDIRECT_URL, WOMPI_CURRENCY
import os
from datetime import datetime, timedelta
from flask_migrate import Migrate

from config import Config
from models import db, User, Game, Comment, Donation, PasswordResetToken, Notification, downloads
from flask_mail import Mail, Message
from flask_login import  login_required, LoginManager, login_user, current_user
from sqlalchemy import func, text, extract
from collections import defaultdict
import traceback  
import smtplib
import json
import uuid
import random
import hashlib

app = Flask(__name__)
app.config.from_object(Config)

mail = Mail(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
db.init_app(app)
admin_bp = Blueprint('admin', __name__)
migrate = Migrate(app, db)

login_manager = LoginManager()       
login_manager.init_app(app)         
login_manager.login_view = 'login'   



@login_manager.user_loader
def load_user(user_id):
    """Función requerida para recargar el objeto User desde la DB
    dado el ID almacenado en la sesión."""
    return User.query.get(int(user_id))

WOMPI_PUBLIC_KEY = 'pub_prod_rsFWKqoo2nBPc1ywo92AufU32xCP9Vaf'
WOMPI_INTEGRITY_KEY = 'prv_prod_Wyki3bEfGsCbWSdXDmTO3TNQkeok31hU'
WOMPI_REDIRECT_URL = 'https://levelup.isladigital.xyz/donacion_finalizada'
WOMPI_CURRENCY = 'COP'

def send_notification_email(subject, recipients, html_body):
    """Función de ayuda para enviar un correo electrónico con Flask-Mail."""
    try:
        
        msg = Message(subject,
                      sender=app.config.get('MAIL_DEFAULT_SENDER', 'tu_correo@ejemplo.com'),
                      recipients=recipients,
                      html=html_body)
        # Envía el correo
        mail.send(msg) #
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        # En un entorno de producción, podrías usar un logger aquí
        return False

# ... (código existente) ...
def create_default_admin():
    """Función para crear un usuario administrador por defecto si no existe."""
    with app.app_context():
        admin_user = User.query.filter_by(documento='123456789').first()
        if not admin_user:
            hashed_password = generate_password_hash('4512', method='pbkdf2:sha256')
            new_admin = User(username='edi', email='admin@levelup.com', documento='123456789', password=hashed_password, role='Administrador')
            db.session.add(new_admin)
            db.session.commit()

# --- CAMBIO IMPORTANTE: Solución al error ---
# Reemplazamos @app.before_first_request con with app.app_context()
with app.app_context():
    db.create_all()
    create_default_admin()
# --- FIN DEL CAMBIO ---

@app.route('/')

def home():
# ... (Función home completa) ...
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            if user.role == 'Usuario':
              
                return redirect(url_for('home_usuario')) 
            elif user.role == 'Creador':
                return redirect(url_for('home_creador'))
            elif user.role == 'Administrador':
                return redirect(url_for('admin_panel'))
    
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
# ... (Función register completa) ...
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        documento = request.form['documento']
        password = request.form['password']
        role = request.form['role']
        
        existing_user_by_username = User.query.filter_by(username=username).first()
        existing_user_by_email = User.query.filter_by(email=email).first()
        existing_user_by_documento = User.query.filter_by(documento=documento).first()

        if existing_user_by_username:
            flash('El nombre de usuario ya existe. Por favor, elige otro.', 'error')
        elif existing_user_by_email:
            flash('El correo electrónico ya está registrado. Por favor, usa otro.', 'error')
        elif existing_user_by_documento:
            flash('El documento ya está registrado. Por favor, usa otro.', 'error')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, documento=documento, password=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('register'))
            
    return render_template('register.html')


@app.route('/creador/publicar_avance', methods=['GET', 'POST'])
def publicar_avance():
# ... (Función publicar_avance completa) ...
    """Permite al Creador publicar un avance/notificación y notificar por correo."""
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder.', 'error')
        return redirect(url_for('login'))

    creator = User.query.get(session['user_id'])
    if creator.role != 'Creador':
        flash('No tienes permiso para realizar esta acción.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        image_url = None
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            filename = secure_filename(file.filename)
            # Asegura un nombre de archivo único
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            image_url = unique_filename

        # 1. Guardar la notificación en la base de datos (para la vista en la página)
        new_notification = Notification(
            title=title,
            content=content,
            image_url=image_url,
            creator_id=creator.id
        )
        db.session.add(new_notification)
        db.session.commit()

        # 2. Enviar notificaciones por correo electrónico a todos los usuarios/creadores
        # Obtener todos los correos registrados
        all_users = User.query.with_entities(User.email).all()
        recipients = [user[0] for user in all_users]

        # Crear el cuerpo del correo (HTML)
        image_html = f'<img src="{request.url_root}static/uploads/{image_url}" alt="Avance de Creador" style="max-width: 100%; height: auto;">' if image_url else ''
        email_html = render_template('email_notification.html', 
                                     creator_name=creator.username,
                                     notification_title=title, 
                                     notification_content=content,
                                     notification_image_html=image_html)
        
        send_notification_email(
            subject=f"[AVANCE DE CREADOR] {title}",
            recipients=recipients,
            html_body=email_html
        )
        
        flash('Avance publicado y notificaciones por correo enviadas exitosamente.', 'success')
        return redirect(url_for('home_creador'))

    # Renderiza la plantilla del formulario de publicación
    return render_template('publicar_avance.html', creator=creator)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = User.query.filter(func.lower(User.username) == username.lower()).first()

        if user and check_password_hash(user.password, password):
            # Guarda la sesión correctamente
            login_user(user)
            session['user_id'] = user.id  # ✅ Importante para mantener la sesión activa
            session['role'] = user.role.strip().lower()

            # Limpia posibles espacios o mayúsculas
            role = user.role.strip().lower()
            print(f"Usuario {user.username} ha iniciado sesión como {role}")

            # Redirección según el rol
            if role == 'administrador':
                flash('Inicio de sesión exitoso como Administrador.', 'success')
                return redirect(url_for('admin_panel'))
            elif role == 'creador':
                flash('Inicio de sesión exitoso como Creador.', 'success')
                return redirect(url_for('home_creador'))
            else:
                flash('Inicio de sesión exitoso como Usuario.', 'success')
                return redirect(url_for('home_usuario'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Cierra la sesión actual y redirige al login."""
    session.pop('user_id', None)
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('login'))


@app.route('/delete_notification/<int:notif_id>', methods=['POST'])
def delete_notification(notif_id):
    notif = Notification.query.get_or_404(notif_id)

    # Solo creador o admin pueden borrar
    if notif.creator_id != current_user.id and not getattr(current_user, 'is_admin', False):
        abort(403)

    # Eliminar imagen si existe
    if notif.image_url:
        image_path = os.path.join(app.root_path, 'static/uploads', notif.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(notif)
    db.session.commit()

    return redirect(url_for('home_usuario'))



@app.route('/donaciones', methods=['GET', 'POST'])
def donaciones():
    try:
        # --- Cargar datos necesarios para mostrar en la vista ---
        creators = User.query.filter_by(role='Creador').all()
        games = Game.query.all()
    except Exception as e:
        flash(f'Error al cargar datos: {e}', 'error')
        return redirect(url_for('home_usuario'))

    if request.method == 'POST':
        try:
            print(">>> POST /donaciones recibido.")

            # 🔹 Forzar lectura de JSON aunque el header sea incorrecto
            try:
                data = request.get_json(force=True)
                print(">>> Datos recibidos (JSON):", data)
                creator_id = data.get('creator_id')
                game_id = data.get('game_id')
                amount_str = data.get('amount')
            except Exception as e:
                print("⚠️ No se pudo parsear JSON, intentando con form:", e)
                creator_id = request.form.get('creator_id')
                game_id = request.form.get('game_id')
                amount_str = request.form.get('amount')

            # --- Validaciones ---
            if not creator_id or not amount_str:
                raise ValueError("Faltan datos: creator_id o amount")

            if 'user_id' not in session:
                raise KeyError("Usuario no autenticado")

            amount = float(amount_str)
            if amount < 100:
                raise ValueError("El monto mínimo de donación es 100 COP")

            if not WOMPI_PUBLIC_KEY or not WOMPI_INTEGRITY_KEY:
                raise ValueError("Claves de Wompi no configuradas correctamente")

            # --- Datos de la transacción ---
            amount_in_cents = int(amount * 100)
            currency = WOMPI_CURRENCY
            reference = f"DON-{session['user_id']}-{creator_id}-{uuid.uuid4().hex[:8]}"

            # --- Crear registro de donación PENDING ---
            new_donation = Donation(
                donor_id=session['user_id'],
                creator_id=creator_id,
                game_id=game_id,
                amount=amount,
                transaction_ref=reference,
                status='PENDING'
            )
            db.session.add(new_donation)
            db.session.commit()
            print(f"✅ Donación creada (PENDING) con ID {new_donation.id}, ref: {reference}")

            # --- Generar firma SHA256 para Wompi ---
            cadena = f"{reference}{amount_in_cents}{currency}{WOMPI_INTEGRITY_KEY}"
            signature = hashlib.sha256(cadena.encode('utf-8')).hexdigest()

            wompi_params = {
                "currency": currency,
                "amountInCents": amount_in_cents,
                "reference": reference,
                "publicKey": WOMPI_PUBLIC_KEY,
                "signature": signature,
                "redirectUrl": WOMPI_REDIRECT_URL,
                "customerData": {
                    "email": db.session.get(User, session['user_id']).email,
                    "fullName": db.session.get(User, session['user_id']).username
                },
                "data": {
                    "donor_id": session['user_id'],
                    "creator_id": creator_id,
                    "game_id": game_id
                }
            }

            print(">>> wompi_params_json generado:", wompi_params)

            # --- Si fue petición JSON (fetch desde JS) ---
            if request.is_json or request.headers.get("Content-Type") == "application/json":
                return jsonify({"success": True, "wompi": wompi_params}), 200

            # --- Si fue formulario HTML normal ---
            return render_template("wompi_redirect.html", wompi_params=wompi_params)

        except Exception as e:
            db.session.rollback()
            print("❌ Error en /donaciones:", e)
            traceback.print_exc()

            if request.is_json:
                return jsonify({"success": False, "error": str(e)}), 400

            flash(f"Error al iniciar el pago: {e}", "error")
            return render_template("wompi_redirect.html", wompi_params={})

    # --- GET: mostrar formulario ---
    return render_template(
        "donaciones.html",
        creators=creators,
        games=games
    )



@app.route('/donacion_finalizada')
def donacion_finalizada():
    status = request.args.get('status', 'ERROR')
    transaction_id = request.args.get('id', 'N/A')

    if status == 'APPROVED':
        flash('🎉 ¡Donación Exitosa! Gracias por tu apoyo.', 'success')
    elif status == 'PENDING':
        flash('⌛ Tu pago está en estado pendiente. Recibirás una notificación cuando se apruebe.', 'warning')
    else:
        flash('❌ La donación no pudo completarse o fue cancelada.', 'error')

    return render_template('wompi_return.html', status=status, transaction_id=transaction_id)

@app.route('/wompi_events', methods=['POST'])
def wompi_events():
    event = request.get_json()
    
    
    transaction = event.get('data', {}).get('transaction', {})
    status = transaction.get('status')
    reference = transaction.get('reference')
    
    if status == 'APPROVED':
        # Obtener los datos necesarios de la transacción (monto, IDs, etc.)
        amount = transaction.get('amount_in_cents') / 100
        # Los IDs están en el campo 'data' que enviamos en el paso anterior
        transaction_data = transaction.get('data', {}) 
        donor_id = transaction_data.get('donor_id')
        creator_id = transaction_data.get('creator_id')
        game_id = transaction_data.get('game_id')
        
        # 3. Guardar la donación final en la base de datos
        existing_donation = Donation.query.filter_by(transaction_ref=reference).first()

        if not existing_donation:
            # Crear la nueva donación SOLO si no existe (para evitar duplicados)
            new_donation = Donation(
                amount=amount, 
                donor_id=donor_id, 
                creator_id=creator_id, 
                game_id=game_id, 
                transaction_ref=reference,
                status='APPROVED'
            )
            db.session.add(new_donation)
            db.session.commit()
         
    elif status in ['DECLINED', 'VOIDED', 'ERROR']:
       pass
        
    return jsonify({"status": "OK"}), 200 


@app.route('/wompi_events_redirect', methods=['GET'])
def wompi_events_redirect():
    transaction_id = request.args.get('id') 
    
    flash('Tu pago fue procesado. Revisa el estado en tu historial.', 'info')
    return redirect(url_for('home_user')) # O a donde quieras que el usuario vaya
@app.route('/create-payment-preference', methods=['POST'])

@app.route('/wompi_redirect')
def wompi_redirect():
    status = request.args.get('status', 'ERROR')
    transaction_id = request.args.get('id', 'N/A')
    return render_template('wompi_return.html', status=status, transaction_id=transaction_id)


def create_payment_preference():
    """
    Ruta llamada por JavaScript para iniciar la transacción con la pasarela de pago.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    try:
        # Los datos se reciben en formato JSON (desde la llamada Fetch en donaciones.html)
        data = request.json
        amount = data.get('amount')
        creator_id = data.get('creator_id')
        game_id = data.get('game_id')
        
        # Validación de datos
        if not amount or (not creator_id and not game_id):
            return jsonify({'error': 'Faltan datos de donación.'}), 400

        try:
            amount = float(amount)
        except ValueError:
            return jsonify({'error': 'Monto inválido.'}), 400
            
        if amount <= 0:
            return jsonify({'error': 'El monto debe ser positivo.'}), 400

        donor_id = session['user_id']
        
       
        external_reference = f"DONATION-{donor_id}-{creator_id or 0}-{game_id or 0}-{uuid.uuid4()}"
        
        # 2. Configuración de la preferencia (Ejemplo con Mercado Pago o Wompi)
        preference_data = {
            "items": [
                {
                    "title": f"Donación a Creador: {creator_id or 'General'}",
                    "quantity": 1,
                    # Los proveedores esperan el monto en la unidad base (centavos/pesos), revisa su documentación
                    "unit_price": amount, 
                    "currency_id": "COP" 
                }
            ],
            # URL a la que la pasarela notificará la confirmación del pago (Webhook)
            "notification_url": url_for('payment_webhook', _external=True),
            # URL a la que el usuario es redirigido después de un pago
            "back_urls": {
                "success": url_for('home_usuario', _external=True, status='payment_success'),
                "failure": url_for('donaciones', _external=True, status='payment_failure'),
            },
            "external_reference": external_reference,
            # Guardar metadatos cruciales para usar en el Webhook
            "metadata": {
                "donor_id": donor_id,
                "creator_id": creator_id,
                "game_id": game_id,
                "amount": amount
            }
        }
        
        
        payment_url = f"https://checkout.example.com/pago?ref={external_reference}&amount={amount}"
        return jsonify({
            'success': True, 
            'payment_url': payment_url,
            'external_reference': external_reference
        }), 200

    except Exception as e:
        app.logger.error(f"Error en create_payment_preference: {e}")
        return jsonify({'error': 'Error interno del servidor.'}), 500


# =========================================================================
# === NUEVA RUTA: Webhook para confirmar el pago (La pasarela llama a esta) ===
# =========================================================================
@app.route('/webhook-pago', methods=['POST'])
def payment_webhook():
    """
    Esta ruta es llamada por el servidor de la pasarela de pago (ej: Mercado Pago) 
    para notificar el estado final de una transacción.
    """
    try:
        amount = 5000.0 # Monto confirmado
        donor_id = 1 
        creator_id = 2 
        game_id = None 
        transaction_id = str(uuid.uuid4()) # ID de la transacción del proveedor

        # 2. CREACIÓN FINAL DEL OBJETO DONATION (SOLO si el pago fue 'approved')
        new_donation = Donation(
            donor_id=donor_id,
            creator_id=creator_id,
            game_id=game_id,
            amount=amount,
            # Se recomienda agregar 'transaction_id' al modelo Donation
            donation_date=datetime.utcnow() 
        )
        
        db.session.add(new_donation)
        db.session.commit()
        
        # Devolver un 200 OK es fundamental para que la pasarela no reintente.
        return '', 200 
    
    except Exception as e:
        app.logger.error(f"Error al procesar webhook de pago: {e}")
        return '', 500 # Devolver un 500 para que la pasarela reintente.
@app.route('/donations/history')
def donation_history():
# ... (Función donation_history completa) ...
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if user.role != 'Creador':
        flash('No tienes permiso para ver esta página.', 'error')
        return redirect(url_for('home'))
        
    donations = Donation.query.filter_by(creator_id=user.id).all()
    
    return render_template('donations_history.html', donations=donations)

@app.route('/home_usuario')

def home_usuario():

    if current_user.role != 'Usuario':
        flash('No tienes permiso para acceder a esta página.', 'error')
        return redirect(url_for('home'))

    user = current_user
    
    if not user or user.role != 'Usuario':
        flash('No tienes permiso para acceder a esta página.', 'error')
        return redirect(url_for('home'))
        
    games_uploaded = Game.query.all()
    downloaded_games = user.downloaded_games 
    latest_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    
    return render_template('homeUser.html', user=user, all_games=games_uploaded, downloaded_games=downloaded_games, notifications=latest_notifications)


@app.route('/home_creador')
@login_required
def home_creador():
    if current_user.role.strip().lower() != 'creador':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('home_usuario'))  # ✅ ADIÓS LOOP INFINITO

    received_donations = current_user.received_donations

    donations_by_game = defaultdict(float)
    total_received = 0.0
    for donation in received_donations:
        game_name = donation.game.name if donation.game else "General"
        donations_by_game[game_name] += donation.amount
        total_received += donation.amount

    my_games = current_user.creator_games
    notifications = Notification.query.filter_by(
        creator_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()

    return render_template(
        'homeCreador.html', 
        user=current_user,
        received_donations=received_donations,
        donations_by_game=dict(donations_by_game),
        total_received=total_received,
        my_games=my_games,
        notifications=notifications
    )  

@app.route('/admin_panel')
def admin_panel():
# ... (Función admin_panel completa) ...
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder.', 'error')
        return redirect(url_for('login'))
        
    user = User.query.get(session['user_id'])
    
    if not user or user.role != 'Administrador':
        flash('No tienes permiso para acceder a esta página.', 'error')
        return redirect(url_for('home'))
        
    users = User.query.all()
    games = Game.query.all()
    donations = Donation.query.all()
    
    return render_template('admin_dashboard.html', users=users, games=games, donations=donations)



@admin_bp.route('/admin/dashboard/data')
def dashboard_data():
    """Genera los datos estadísticos del panel de administración."""
    # --- Donaciones por mes ---
    donations_month = (
        db.session.query(
            extract('month', Donation.timestamp).label('month'),
            func.sum(Donation.amount)
        )
        .group_by('month')
        .order_by('month')
        .all()
    )
    donations_month_labels = [str(int(row[0])) for row in donations_month]
    donations_month_data = [float(row[1]) for row in donations_month]

    # --- Donaciones por semana ---
    donations_week = (
        db.session.query(
            func.strftime('%Y-%W', Donation.timestamp).label('week'),
            func.sum(Donation.amount)
        )
        .group_by('week')
        .order_by('week')
        .all()
    )
    donations_week_labels = [row[0] for row in donations_week]
    donations_week_data = [float(row[1]) for row in donations_week]

    # --- Conteo de usuarios por rol ---
    logins_by_role = (
        db.session.query(User.role, func.count(User.id))
        .group_by(User.role)
        .all()
    )
    logins_labels = [row[0] for row in logins_by_role]
    logins_data = [row[1] for row in logins_by_role]

    # --- Top 10 juegos más descargados ---
    downloads_count = (
        db.session.query(
            Game.name,
            func.count(downloads.c.game_id).label('count')
        )
        .join(downloads, Game.id == downloads.c.game_id)
        .group_by(Game.id)
        .order_by(func.count(downloads.c.game_id).desc())
        .limit(10)
        .all()
    )
    downloads_labels = [row[0] for row in downloads_count]
    downloads_data = [row[1] for row in downloads_count]

    # --- Actividad diaria del mes actual ---
    today = datetime.utcnow()
    start_of_month = today.replace(day=1)
    next_month = (start_of_month + timedelta(days=32)).replace(day=1)

    # --- Donaciones por día ---
    donations_daily = (
        db.session.query(
            func.date(Donation.timestamp).label('date'),
            func.sum(Donation.amount).label('total')
        )
        .filter(Donation.timestamp >= start_of_month, Donation.timestamp < next_month)
        .group_by('date')
        .order_by('date')
        .all()
    )
    donation_daily_dict = {str(row.date): float(row.total or 0) for row in donations_daily}

    # --- Descargas por día ---
    downloads_daily = []
    try:
        downloads_daily = db.session.execute(text("""
            SELECT DATE(timestamp) AS date, COUNT(*) AS total
            FROM downloads
            WHERE timestamp >= :start AND timestamp < :end
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp)
        """), {'start': start_of_month, 'end': next_month}).fetchall()
    except Exception as e:
        print("⚠️ No se encontró columna timestamp en downloads:", e)
    downloads_daily_dict = {str(row.date): row.total for row in downloads_daily}

    # --- Logins por día (vacío si no tienes tabla LoginLog) ---
    logins_daily_dict = {}

    # --- Etiquetas del mes actual ---
    days_in_month = [(start_of_month + timedelta(days=i)).date() for i in range((next_month - start_of_month).days)]
    labels_daily = [str(day) for day in days_in_month]

    # --- Preparar datos combinados ---
    activity_day = {
        'labels': labels_daily,
        'donations': [donation_daily_dict.get(str(day), 0) for day in days_in_month],
        'downloads': [downloads_daily_dict.get(str(day), 0) for day in days_in_month],
        'logins': [logins_daily_dict.get(str(day), 0) for day in days_in_month],
    }

    # --- Enviar datos a frontend ---
    return jsonify({
        'donations_month': {'labels': donations_month_labels, 'data': donations_month_data},
        'donations_week': {'labels': donations_week_labels, 'data': donations_week_data},
        'logins': {'labels': logins_labels, 'data': logins_data},
        'downloads': {'labels': downloads_labels, 'data': downloads_data},
        'activity_day': activity_day
    })

def insert_data():
# ... (Función insert_data completa) ...
    with app.app_context():
        print("Iniciando inserción de datos de prueba...")
        
        # 1. Obtener o Crear un Usuario Administrador (debería existir)
        admin_user = User.query.filter_by(role='Administrador').first()
        if not admin_user:
            print("ERROR: No se encontró el Administrador por defecto.")
            return

        # 2. Crear Usuarios (si no existen)
        creator_user = User.query.filter_by(username='TestCreator').first()
        if not creator_user:
            creator_password = generate_password_hash('pass123', method='pbkdf2:sha256')
            creator_user = User(username='TestCreator', email='creator@test.com', documento='111222333', password=creator_password, role='Creador')
            db.session.add(creator_user)
            print("Creado usuario 'TestCreator'.")
            
        regular_user = User.query.filter_by(username='TestUser').first()
        if not regular_user:
            user_password = generate_password_hash('pass123', method='pbkdf2:sha256')
            regular_user = User(username='TestUser', email='user@test.com', documento='999888777', password=user_password, role='Usuario')
            db.session.add(regular_user)
            print("Creado usuario 'TestUser'.")
            
        db.session.commit()
        
        # 3. Crear un Juego (si no existe)
        game = Game.query.filter_by(name='Mi Juego de Prueba').first()
        if not game:
            game = Game(name='Mi Juego de Prueba', description='Juego para testear donaciones.', image_url='default.png', creator_id=creator_user.id)
            db.session.add(game)
            db.session.commit()
            print("Creado juego 'Mi Juego de Prueba'.")

        # 4. Crear Donaciones (para la gráfica de Barras)
        # 4.1 Donación de este mes
        if Donation.query.count() < 5:
            db.session.add_all([
                Donation(amount=15.00, donor_id=regular_user.id, creator_id=creator_user.id, game_id=game.id, timestamp=datetime.utcnow()),
                Donation(amount=25.00, donor_id=regular_user.id, creator_id=creator_user.id, game_id=game.id, timestamp=datetime.utcnow()),
            ])
            
            last_month = datetime.utcnow() - timedelta(days=35)
            db.session.add(Donation(amount=50.00, donor_id=regular_user.id, creator_id=creator_user.id, game_id=game.id, timestamp=last_month))
            print("Creadas donaciones de prueba.")
        
        # 5. Crear una descarga de prueba
        if regular_user not in game.downloaded_by:
            regular_user.downloaded_games.append(game)
            print("Creada descarga de prueba.")

        db.session.commit()
        print("Datos de prueba insertados con éxito en las tablas User y Donation.")

    
@app.route('/upload_game', methods=['GET', 'POST'])
def upload_game():
# ... (Función upload_game completa) ...
    if 'user_id' not in session:
        flash('Debes iniciar sesión para subir un juego.', 'error')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        game_name = request.form['game-name']
        game_description = request.form['game-description']
        
        if 'game-image' in request.files:
            file = request.files['game-image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                new_game = Game(
                    name=game_name,
                    description=game_description,
                    image_url=filename,
                    creator_id=session['user_id']
                )
                
                db.session.add(new_game)
                db.session.commit()
                flash('Juego subido exitosamente.', 'success')
                return redirect(url_for('home_creador'))
            
    return render_template('formu.html')

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
# ... (Función edit_profile completa) ...
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        new_password = request.form['password']

        if new_password:
            user.password = generate_password_hash(new_password)

        db.session.commit()
        flash('Perfil actualizado con éxito.', 'success')
        
        if user.role == 'Usuario':
            return redirect(url_for('home_usuario'))
        elif user.role == 'Creador':
            return redirect(url_for('home_creador'))
            
    return render_template('edit_profile.html', user=user)

@app.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
# ... (Función request_password_reset completa) ...
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            PasswordResetToken.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            
            code = str(random.randint(100000, 999999))
            
            new_token = PasswordResetToken(user_id=user.id, token=code, expiration=datetime.utcnow() + timedelta(minutes=15))
            db.session.add(new_token)
            db.session.commit()
            
            msg = Message(
                'Código de Restablecimiento de Contraseña',
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[user.email]
            )
            msg.html = render_template('password_reset_email.html', username=user.username, code=code)
            
            try:
                mail.send(msg)
                flash('Se ha enviado un código de verificación a tu correo electrónico.', 'success')
                return redirect(url_for('verify_code', email=email))
            except Exception as e:
                flash(f'Error al enviar el correo: {e}', 'error')
        else:
            flash('Si el correo electrónico existe, se ha enviado un código de verificación.', 'info')

    return render_template('request_password_reset.html')

@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
# ... (Función verify_code completa) ...
    if request.method == 'POST':
        email = request.form.get('email')
        code = request.form.get('code')
        
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Correo electrónico no encontrado.', 'error')
            return redirect(url_for('verify_code'))
            
        reset_token = PasswordResetToken.query.filter_by(user_id=user.id, token=code).first()
        
        if not reset_token:
            flash('El código es incorrecto. Intenta de nuevo.', 'error')
            return render_template('verify_code.html', email=email)
        
        if reset_token.expiration < datetime.utcnow():
            flash('El código ha expirado. Por favor, solicita uno nuevo.', 'error')
            return redirect(url_for('request_password_reset'))
            
        return redirect(url_for('reset_password_code', token=reset_token.token))
        
    email = request.args.get('email', '')
    return render_template('verify_code.html', email=email)
    
@app.route('/reset_password_code/<token>', methods=['GET', 'POST'])
def reset_password_code(token):
# ... (Función reset_password_code completa) ...
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_token or reset_token.expiration < datetime.utcnow():
        flash('El enlace es inválido o ha expirado.', 'error')
        return redirect(url_for('request_password_reset'))
        
    user = reset_token.user
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        
        if not new_password:
            flash('La contraseña no puede estar vacía.', 'error')
            return render_template('reset_password.html', token=token)
        
        user.password = generate_password_hash(new_password)
        
        db.session.delete(reset_token)
        db.session.commit()
        
        flash('Tu contraseña ha sido actualizada exitosamente.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_password.html', token=token)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)