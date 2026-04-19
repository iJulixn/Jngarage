from flask import Flask, render_template, request, redirect, url_for, send_file
from datetime import datetime
import psycopg2
import os
from reportlab.pdfgen import canvas
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

app = Flask(__name__)
app.secret_key = "jngarage_secret"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

USUARIO = "admin"
PASSWORD = "1234"

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def crear_tablas():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicios (
        id SERIAL PRIMARY KEY,
        fecha TEXT,
        cliente TEXT,
        auto TEXT,
        tipo TEXT,
        precio FLOAT
    )
    """)

    conn.commit()
    conn.close()

crear_tablas()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]

        if user == USUARIO and password == PASSWORD:
            login_user(User(1))
            return redirect("/")
        else:
            return "Datos incorrectos"

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

def generar_pdf(data):
    nombre = "ticket.pdf"
    c = canvas.Canvas(nombre)

    c.drawString(100, 800, "JN Garage Detail")
    c.drawString(100, 770, f"Fecha: {data[1]}")
    c.drawString(100, 750, f"Cliente: {data[2]}")
    c.drawString(100, 730, f"Auto: {data[3]}")
    c.drawString(100, 710, f"Servicio: {data[4]}")
    c.drawString(100, 690, f"Total: ${data[5]}")

    c.save()
    return nombre

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        cliente = request.form["cliente"]
        auto = request.form["auto"]
        tipo = request.form["tipo"]
        precio = float(request.form["precio"])
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

        cursor.execute(
            "INSERT INTO servicios (fecha, cliente, auto, tipo, precio) VALUES (%s,%s,%s,%s,%s)",
            (fecha, cliente, auto, tipo, precio)
        )

        conn.commit()
        return redirect("/")

    cursor.execute("SELECT * FROM servicios ORDER BY id DESC")
    servicios = cursor.fetchall()

    hoy = datetime.now().strftime("%Y-%m-%d")
    mes = datetime.now().strftime("%Y-%m")

    total_dia = sum(s[5] for s in servicios if hoy in s[1])
    total_mes = sum(s[5] for s in servicios if mes in s[1])

    conn.close()

    return render_template("index.html",
                           datos=servicios,
                           total_dia=total_dia,
                           total_mes=total_mes)

@app.route("/ticket/<int:id>")
@login_required
def ticket(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM servicios WHERE id=%s", (id,))
    data = cursor.fetchone()

    conn.close()

    pdf = generar_pdf(data)
    return send_file(pdf, as_attachment=True)

app.run(host="0.0.0.0", port=5000)
