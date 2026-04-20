from flask import Flask, render_template, request, redirect, send_file, jsonify
from datetime import datetime
import psycopg2, os, mercadopago, uuid
from reportlab.pdfgen import canvas
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

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

def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def crear_tablas():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS servicios (id SERIAL PRIMARY KEY, fecha TEXT, cliente TEXT, auto TEXT, tipo TEXT, precio FLOAT, estado TEXT DEFAULT 'pendiente', mp_id TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nombre TEXT UNIQUE)")
    conn.commit()
    conn.close()

crear_tablas()

def generar_pdf(d):
    name = f"ticket_{uuid.uuid4()}.pdf"
    c = canvas.Canvas(name)
    c.drawString(100,800,"JN Garage Detail")
    c.drawString(100,750,f"{d[2]} - {d[3]}")
    c.drawString(100,700,f"{d[4]} $ {d[5]}")
    c.drawString(100,650,f"Estado: {d[6]}")
    c.save()
    return name

def crear_pago(desc, precio, servicio_id):
    pref = sdk.preference().create({
        "items":[{"title":desc,"quantity":1,"unit_price":float(precio)}],
        "metadata":{"servicio_id":servicio_id}
    })
    return pref["response"]["init_point"], pref["response"]["id"]

@app.route("/login", methods=["GET","POST"])
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

@app.route("/", methods=["GET","POST"])
@login_required
def index():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        cliente = request.form["cliente"]
        cur.execute("INSERT INTO clientes (nombre) VALUES (%s) ON CONFLICT DO NOTHING",(cliente,))
        cur.execute("INSERT INTO servicios (fecha,cliente,auto,tipo,precio) VALUES (%s,%s,%s,%s,%s)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M"),
                     cliente,
                     request.form["auto"],
                     request.form["tipo"],
                     float(request.form["precio"])))
        conn.commit()

    cur.execute("SELECT * FROM servicios ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()

    total = sum(s[5] for s in data)
    pagados = sum(s[5] for s in data if s[6]=="pagado")
    pendientes = sum(s[5] for s in data if s[6]=="pendiente")

    return render_template("index.html",datos=data,total=total,pagados=pagados,pendientes=pendientes)

@app.route("/qr/<int:id>")
@login_required
def qr(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM servicios WHERE id=%s",(id,))
    d = cur.fetchone()

    link, mp_id = crear_pago(d[4],d[5],id)
    cur.execute("UPDATE servicios SET mp_id=%s WHERE id=%s",(mp_id,id))
    conn.commit()
    conn.close()

    return render_template("qr.html",link=link)

@app.route("/ticket/<int:id>")
@login_required
def ticket(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM servicios WHERE id=%s",(id,))
    d = cur.fetchone()
    conn.close()
    return send_file(generar_pdf(d),as_attachment=True)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data and data.get("type")=="payment":
        payment_id = data["data"]["id"]
        pago = sdk.payment().get(payment_id)
        info = pago["response"]
        if info["status"]=="approved":
            servicio_id = info["metadata"]["servicio_id"]
            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE servicios SET estado='pagado' WHERE id=%s",(servicio_id,))
            conn.commit()
            conn.close()
    return jsonify({"status":"ok"})
