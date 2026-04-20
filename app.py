from flask import Flask, render_template, request, redirect, send_file
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

# LOGIN SIMPLE
class User(UserMixin):
    def __init__(self, id):
        self.id = id

USUARIO = "admin"
PASSWORD = "1234"

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# HOME
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cliente = request.form.get("cliente")
        auto = request.form.get("auto")
        servicio = request.form.get("servicio")
        precio = request.form.get("precio")

        # guardar cliente si no existe
        if cliente:
            cur.execute("""
                INSERT INTO clientes (nombre)
                VALUES (%s)
                ON CONFLICT (nombre) DO NOTHING
            """, (cliente,))

        cur.execute("""
            INSERT INTO servicios (cliente, auto, servicio, precio, estado, fecha)
            VALUES (%s,%s,%s,%s,'pendiente',NOW())
        """, (cliente, auto, servicio, precio))

        conn.commit()

    # traer servicios
    cur.execute("SELECT * FROM servicios ORDER BY id DESC")
    data = cur.fetchall()

    # traer clientes
    cur.execute("SELECT nombre FROM clientes ORDER BY nombre")
    clientes = cur.fetchall()

    conn.close()

    total = sum(s[4] for s in data) if data else 0
    pagados = sum(s[4] for s in data if s[5] == "pagado") if data else 0
    pendientes = total - pagados

    return render_template("index.html",
                           datos=data,
                           total=total,
                           pagados=pagados,
                           pendientes=pendientes,
                           clientes=clientes)

# BORRAR CLIENTE
@app.route("/borrar_cliente/<nombre>")
@login_required
def borrar_cliente(nombre):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM clientes WHERE nombre=%s", (nombre,))
    conn.commit()
    conn.close()
    return redirect("/")

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        if user == USUARIO and pw == PASSWORD:
            login_user(User(1))
            return redirect("/")
    return render_template("login.html")

# LOGOUT
@app.route("/logout")
def logout():
    logout_user()
    return redirect("/login")

if __name__ == "__main__":
    app.run()
