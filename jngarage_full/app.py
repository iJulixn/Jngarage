from flask import Flask, render_template, request, redirect, send_file
from datetime import datetime
import psycopg2
import os
import mercadopago
from reportlab.pdfgen import canvas
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import uuid

app = Flask(__name__)
app.secret_key = "jngarage_secret"

sdk = mercadopago.SDK(os.environ.get("MP_ACCESS_TOKEN"))

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
        if request.form["user"] == USUARIO and request.form["password"] == PASSWORD:
            login_user(User(1))
            return redirect("/")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

def generar_pdf(data):
    nombre = f"ticket_{uuid.uuid4()}.pdf"
    c = canvas.Canvas(nombre)
    c.drawString(100, 800, "JN Garage Detail")
    c.drawString(100, 770, f"Cliente: {data[2]}")
    c.drawString(100, 750, f"Auto: {data[3]}")
    c.drawString(100, 730, f"Servicio: {data[4]}")
    c.drawString(100, 710, f"Total: ${data[5]}")
    c.save()
    return nombre

def crear_pago(desc, precio):
    pref = sdk.preference().create({
        "items": [{"title": desc, "quantity": 1, "unit_price": float(precio)}]
    })
    return pref["response"]["init_point"]

@app.route("/pagar/<int:id>")
@login_required
def pagar(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM servicios WHERE id=%s", (id,))
    data = cur.fetchone()
    conn.close()
    return redirect(crear_pago(data[4], data[5]))

@app.route("/", methods=["GET","POST"])
@login_required
def index():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute(
            "INSERT INTO servicios (fecha, cliente, auto, tipo, precio) VALUES (%s,%s,%s,%s,%s)",
            (datetime.now().strftime("%Y-%m-%d %H:%M"),
             request.form["cliente"],
             request.form["auto"],
             request.form["tipo"],
             float(request.form["precio"]))
        )
        conn.commit()
        return redirect("/")

    cur.execute("SELECT * FROM servicios ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()

    return render_template("index.html", datos=data)

@app.route("/ticket/<int:id>")
@login_required
def ticket(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM servicios WHERE id=%s", (id,))
    data = cur.fetchone()
    conn.close()
    return send_file(generar_pdf(data), as_attachment=True)
