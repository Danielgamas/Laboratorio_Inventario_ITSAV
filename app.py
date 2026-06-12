import os
from functools import wraps
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

os.makedirs(app.instance_path, exist_ok=True)

app.config["SECRET_KEY"] = "itsav_lab_isc_secret_key_2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "inventario.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Equipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(80), nullable=False)
    marca = db.Column(db.String(80), nullable=True)
    modelo = db.Column(db.String(80), nullable=True)
    numero_serie = db.Column(db.String(100), nullable=True, unique=True)
    ubicacion = db.Column(db.String(120), nullable=True)
    estado = db.Column(db.String(40), nullable=False, default="Disponible")
    observaciones = db.Column(db.Text, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.now)

    prestamos = db.relationship("Prestamo", backref="equipo", lazy=True)


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(150), nullable=False)
    matricula = db.Column(db.String(50), nullable=False, unique=True)
    carrera_area = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(120), nullable=True, unique=True)
    tipo_usuario = db.Column(db.String(40), nullable=False, default="Estudiante")
    activo = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.now)

    cuentas = db.relationship(
        "Cuenta",
        backref="usuario_ref",
        lazy=True,
        cascade="all, delete-orphan"
    )

    prestamos = db.relationship("Prestamo", backref="usuario", lazy=True)


class Cuenta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(40), nullable=False, default="Estudiante")
    activo = db.Column(db.Boolean, default=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Prestamo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey("equipo.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.now)
    fecha_prestamo = db.Column(db.DateTime, nullable=True)
    fecha_devolucion_estimada = db.Column(db.DateTime, nullable=True)
    fecha_devolucion_real = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(40), nullable=False, default="Pendiente")
    observaciones = db.Column(db.Text, nullable=True)


def crear_datos_iniciales():
    db.create_all()

    admin_usuario = Usuario.query.filter_by(matricula="ADMIN001").first()

    if not admin_usuario:
        admin_usuario = Usuario(
            nombre_completo="Administrador del Laboratorio ISC",
            matricula="ADMIN001",
            carrera_area="Laboratorio de Ingeniería en Sistemas Computacionales",
            correo="admin@itsav.edu.mx",
            tipo_usuario="Administrador",
            activo=True
        )
        db.session.add(admin_usuario)
        db.session.commit()

    admin_cuenta = Cuenta.query.filter_by(usuario="admin").first()

    if not admin_cuenta:
        admin_cuenta = Cuenta(
            usuario="admin",
            rol="Administrador",
            activo=True,
            usuario_id=admin_usuario.id
        )
        admin_cuenta.set_password("1234")
        db.session.add(admin_cuenta)

    demo_cuenta = Cuenta.query.filter_by(usuario="estudiante").first()
    if demo_cuenta:
        db.session.delete(demo_cuenta)

    demo_usuario = Usuario.query.filter_by(matricula="EST001").first()
    if demo_usuario:
        prestamos_demo = Prestamo.query.filter_by(usuario_id=demo_usuario.id).all()

        for prestamo in prestamos_demo:
            if prestamo.equipo:
                prestamo.equipo.estado = "Disponible"
            db.session.delete(prestamo)

        db.session.delete(demo_usuario)

    if Equipo.query.count() == 0:
        equipos_demo = [
            Equipo(
                nombre="Laptop Dell Latitude 3420",
                tipo="Laptop",
                marca="Dell",
                modelo="Latitude 3420",
                numero_serie="ISC-001",
                ubicacion="Laboratorio ISC",
                estado="Disponible",
                observaciones="Equipo funcional para prácticas académicas."
            ),
            Equipo(
                nombre="Kit Arduino Mega 2560 R3",
                tipo="Microcontrolador",
                marca="Arduino",
                modelo="Mega 2560 R3",
                numero_serie="ISC-002",
                ubicacion="Laboratorio ISC",
                estado="Disponible",
                observaciones="Incluye cable USB."
            ),
            Equipo(
                nombre="Monitor HP 24 pulgadas",
                tipo="Monitor",
                marca="HP",
                modelo="24",
                numero_serie="ISC-003",
                ubicacion="Laboratorio ISC",
                estado="Disponible",
                observaciones="Monitor para prácticas de laboratorio."
            ),
            Equipo(
                nombre="Cable de Red UTP Cat 6",
                tipo="Cable",
                marca="Genérico",
                modelo="Cat 6",
                numero_serie="ISC-004",
                ubicacion="Laboratorio ISC",
                estado="Disponible",
                observaciones="Cable de red para prácticas de conectividad."
            )
        ]

        db.session.add_all(equipos_demo)

    db.session.commit()


with app.app_context():
    crear_datos_iniciales()


@app.context_processor
def variables_globales():
    return {
        "usuario_sesion": session.get("usuario"),
        "rol_sesion": session.get("rol"),
        "nombre_sesion": session.get("nombre_completo")
    }


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("cuenta_id"):
            flash("Inicia sesión para continuar.", "warning")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("cuenta_id"):
            flash("Inicia sesión para acceder al sistema.", "warning")
            return redirect(url_for("login"))

        if session.get("rol") not in ["Administrador", "Encargado"]:
            flash("No tienes permisos administrativos para esta sección.", "danger")
            return redirect(url_for("estudiante_dashboard"))

        return view(*args, **kwargs)

    return wrapped_view


def estudiante_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("cuenta_id"):
            flash("Inicia sesión para continuar.", "warning")
            return redirect(url_for("login", perfil="estudiante"))

        if session.get("rol") not in ["Estudiante", "Docente"]:
            flash("Esta sección corresponde al perfil académico.", "warning")
            return redirect(url_for("dashboard"))

        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/consulta-publica")
def consulta_publica():
    equipos = (
        Equipo.query
        .filter_by(estado="Disponible")
        .order_by(Equipo.nombre.asc())
        .all()
    )

    return render_template("consulta_publica.html", equipos=equipos)


@app.route("/login", methods=["GET", "POST"])
def login():
    perfil = request.args.get("perfil", "").strip()

    if request.method == "POST":
        identificador = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        cuenta = Cuenta.query.filter_by(usuario=identificador.lower()).first()

        if not cuenta:
            cuenta = (
                Cuenta.query
                .join(Usuario)
                .filter(
                    or_(
                        Usuario.correo == identificador.lower(),
                        Usuario.matricula == identificador
                    )
                )
                .first()
            )

        if cuenta and not cuenta.activo:
            flash("Tu cuenta existe, pero todavía está pendiente de activación.", "warning")
            return redirect(url_for("login"))

        if cuenta and cuenta.check_password(password):
            session.clear()

            session["cuenta_id"] = cuenta.id
            session["usuario"] = cuenta.usuario
            session["rol"] = cuenta.rol

            if cuenta.usuario_ref:
                session["usuario_id"] = cuenta.usuario_ref.id
                session["nombre_completo"] = cuenta.usuario_ref.nombre_completo

            flash("Sesión iniciada correctamente.", "success")

            if cuenta.rol in ["Estudiante", "Docente"]:
                return redirect(url_for("estudiante_dashboard"))

            return redirect(url_for("dashboard"))

        flash("Credenciales incorrectas. Verifica tus datos de acceso.", "danger")

    return render_template("login.html", perfil=perfil)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre_completo = request.form.get("nombre_completo", "").strip()
        matricula = request.form.get("matricula", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        carrera_area = request.form.get("carrera_area", "").strip()
        tipo_usuario = request.form.get("tipo_usuario", "Estudiante").strip()
        password = request.form.get("password", "")
        confirmar_password = request.form.get("confirmar_password", "")

        tipos_validos = ["Estudiante", "Docente", "Encargado"]

        if tipo_usuario not in tipos_validos:
            tipo_usuario = "Estudiante"

        if not nombre_completo or not matricula or not correo or not carrera_area or not password:
            flash("Todos los campos son obligatorios.", "warning")
            return redirect(url_for("registro"))

        if password != confirmar_password:
            flash("Las contraseñas no coinciden.", "warning")
            return redirect(url_for("registro"))

        if len(password) < 4:
            flash("La contraseña debe tener al menos 4 caracteres.", "warning")
            return redirect(url_for("registro"))

        usuario_existente = Usuario.query.filter(
            or_(
                Usuario.matricula == matricula,
                Usuario.correo == correo
            )
        ).first()

        if usuario_existente:
            flash("Ya existe un usuario registrado con esa matrícula o correo.", "danger")
            return redirect(url_for("registro"))

        cuenta_existente = Cuenta.query.filter_by(usuario=correo).first()

        if cuenta_existente:
            flash("Ya existe una cuenta registrada con ese correo.", "danger")
            return redirect(url_for("registro"))

        activo_inicial = False if tipo_usuario == "Encargado" else True

        try:
            nuevo_usuario = Usuario(
                nombre_completo=nombre_completo,
                matricula=matricula,
                carrera_area=carrera_area,
                correo=correo,
                tipo_usuario=tipo_usuario,
                activo=activo_inicial
            )

            db.session.add(nuevo_usuario)
            db.session.flush()

            nueva_cuenta = Cuenta(
                usuario=correo,
                rol=tipo_usuario,
                activo=activo_inicial,
                usuario_id=nuevo_usuario.id
            )
            nueva_cuenta.set_password(password)

            db.session.add(nueva_cuenta)
            db.session.commit()

            if tipo_usuario == "Encargado":
                flash("Registro enviado. La cuenta de encargado debe ser activada por el administrador.", "info")
            else:
                flash("Registro creado correctamente. Ya puedes iniciar sesión.", "success")

            return redirect(url_for("login", perfil="estudiante"))

        except Exception as e:
            db.session.rollback()
            print("ERROR EN REGISTRO:", str(e))
            flash("No se pudo registrar el usuario. Verifica los datos e intenta nuevamente.", "danger")
            return redirect(url_for("registro"))

    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@admin_required
def dashboard():
    total_equipos = Equipo.query.count()
    disponibles = Equipo.query.filter_by(estado="Disponible").count()
    prestados = Equipo.query.filter_by(estado="Prestado").count()
    mantenimiento = Equipo.query.filter_by(estado="Mantenimiento").count()

    total_usuarios = Usuario.query.count()
    prestamos_pendientes = Prestamo.query.filter_by(estado="Pendiente").count()
    prestamos_activos = Prestamo.query.filter_by(estado="Aprobado").count()
    prestamos_devueltos = Prestamo.query.filter_by(estado="Devuelto").count()

    ultimos_prestamos = (
        Prestamo.query
        .order_by(Prestamo.fecha_solicitud.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_equipos=total_equipos,
        disponibles=disponibles,
        prestados=prestados,
        mantenimiento=mantenimiento,
        total_usuarios=total_usuarios,
        prestamos_pendientes=prestamos_pendientes,
        prestamos_activos=prestamos_activos,
        prestamos_devueltos=prestamos_devueltos,
        ultimos_prestamos=ultimos_prestamos
    )


@app.route("/equipos", methods=["GET", "POST"])
@admin_required
def equipos():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        tipo = request.form.get("tipo", "").strip()
        marca = request.form.get("marca", "").strip()
        modelo = request.form.get("modelo", "").strip()
        numero_serie = request.form.get("numero_serie", "").strip()
        ubicacion = request.form.get("ubicacion", "").strip()
        estado = request.form.get("estado", "Disponible").strip()
        observaciones = request.form.get("observaciones", "").strip()

        if not nombre or not tipo:
            flash("El nombre y el tipo de equipo son obligatorios.", "warning")
            return redirect(url_for("equipos"))

        nuevo_equipo = Equipo(
            nombre=nombre,
            tipo=tipo,
            marca=marca,
            modelo=modelo,
            numero_serie=numero_serie if numero_serie else None,
            ubicacion=ubicacion,
            estado=estado,
            observaciones=observaciones
        )

        try:
            db.session.add(nuevo_equipo)
            db.session.commit()
            flash("Equipo registrado correctamente.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe un equipo con ese número de serie.", "danger")

        return redirect(url_for("equipos"))

    q = request.args.get("q", "").strip()

    consulta = Equipo.query

    if q:
        consulta = consulta.filter(
            or_(
                Equipo.nombre.ilike(f"%{q}%"),
                Equipo.tipo.ilike(f"%{q}%"),
                Equipo.marca.ilike(f"%{q}%"),
                Equipo.modelo.ilike(f"%{q}%"),
                Equipo.numero_serie.ilike(f"%{q}%"),
                Equipo.estado.ilike(f"%{q}%")
            )
        )

    equipos = consulta.order_by(Equipo.fecha_registro.desc()).all()

    return render_template("equipos.html", equipos=equipos, q=q)


@app.route("/equipos/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar_equipo(id):
    equipo = Equipo.query.get_or_404(id)

    if request.method == "POST":
        equipo.nombre = request.form.get("nombre", "").strip()
        equipo.tipo = request.form.get("tipo", "").strip()
        equipo.marca = request.form.get("marca", "").strip()
        equipo.modelo = request.form.get("modelo", "").strip()
        equipo.numero_serie = request.form.get("numero_serie", "").strip() or None
        equipo.ubicacion = request.form.get("ubicacion", "").strip()
        equipo.estado = request.form.get("estado", "Disponible").strip()
        equipo.observaciones = request.form.get("observaciones", "").strip()

        if not equipo.nombre or not equipo.tipo:
            flash("El nombre y tipo son obligatorios.", "warning")
            return redirect(url_for("editar_equipo", id=equipo.id))

        try:
            db.session.commit()
            flash("Equipo actualizado correctamente.", "success")
            return redirect(url_for("equipos"))
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe otro equipo con ese número de serie.", "danger")

    return render_template("editar_equipo.html", equipo=equipo)


@app.route("/equipos/<int:id>/eliminar", methods=["POST"])
@admin_required
def eliminar_equipo(id):
    equipo = Equipo.query.get_or_404(id)

    prestamo_activo = Prestamo.query.filter(
        Prestamo.equipo_id == equipo.id,
        Prestamo.estado.in_(["Pendiente", "Aprobado"])
    ).first()

    if prestamo_activo:
        flash("No puedes eliminar un equipo con préstamo pendiente o activo.", "warning")
        return redirect(url_for("equipos"))

    db.session.delete(equipo)
    db.session.commit()

    flash("Equipo eliminado correctamente.", "info")
    return redirect(url_for("equipos"))


@app.route("/usuarios", methods=["GET", "POST"])
@admin_required
def usuarios():
    if request.method == "POST":
        nombre_completo = request.form.get("nombre_completo", "").strip()
        matricula = request.form.get("matricula", "").strip()
        carrera_area = request.form.get("carrera_area", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        tipo_usuario = request.form.get("tipo_usuario", "Estudiante").strip()
        activo = True if request.form.get("activo") == "1" else False

        if not nombre_completo or not matricula or not carrera_area:
            flash("Nombre, matrícula y carrera/área son obligatorios.", "warning")
            return redirect(url_for("usuarios"))

        nuevo_usuario = Usuario(
            nombre_completo=nombre_completo,
            matricula=matricula,
            carrera_area=carrera_area,
            correo=correo if correo else None,
            tipo_usuario=tipo_usuario,
            activo=activo
        )

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash("Usuario registrado correctamente.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe un usuario con esa matrícula o correo.", "danger")

        return redirect(url_for("usuarios"))

    q = request.args.get("q", "").strip()

    consulta = Usuario.query

    if q:
        consulta = consulta.filter(
            or_(
                Usuario.nombre_completo.ilike(f"%{q}%"),
                Usuario.matricula.ilike(f"%{q}%"),
                Usuario.correo.ilike(f"%{q}%"),
                Usuario.carrera_area.ilike(f"%{q}%"),
                Usuario.tipo_usuario.ilike(f"%{q}%")
            )
        )

    usuarios = consulta.order_by(Usuario.fecha_registro.desc()).all()

    return render_template("usuarios.html", usuarios=usuarios, q=q)


@app.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)

    if request.method == "POST":
        usuario.nombre_completo = request.form.get("nombre_completo", "").strip()
        usuario.matricula = request.form.get("matricula", "").strip()
        usuario.carrera_area = request.form.get("carrera_area", "").strip()
        usuario.correo = request.form.get("correo", "").strip().lower() or None
        usuario.tipo_usuario = request.form.get("tipo_usuario", "Estudiante").strip()
        usuario.activo = True if request.form.get("activo") == "1" else False

        for cuenta in usuario.cuentas:
            cuenta.rol = usuario.tipo_usuario
            cuenta.activo = usuario.activo

        try:
            db.session.commit()
            flash("Usuario actualizado correctamente.", "success")
            return redirect(url_for("usuarios"))
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe otro usuario con esa matrícula o correo.", "danger")

    return render_template("editar_usuario.html", usuario=usuario)


@app.route("/usuarios/<int:id>/eliminar", methods=["POST"])
@admin_required
def eliminar_usuario(id):
    usuario = Usuario.query.get_or_404(id)

    if usuario.tipo_usuario == "Administrador":
        flash("No se puede eliminar el administrador principal.", "warning")
        return redirect(url_for("usuarios"))

    prestamo_activo = Prestamo.query.filter(
        Prestamo.usuario_id == usuario.id,
        Prestamo.estado.in_(["Pendiente", "Aprobado"])
    ).first()

    if prestamo_activo:
        flash("No puedes eliminar un usuario con préstamo pendiente o activo.", "warning")
        return redirect(url_for("usuarios"))

    db.session.delete(usuario)
    db.session.commit()

    flash("Usuario eliminado correctamente.", "info")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:id>/activar", methods=["POST"])
@admin_required
def activar_usuario(id):
    usuario = Usuario.query.get_or_404(id)

    usuario.activo = True

    for cuenta in usuario.cuentas:
        cuenta.activo = True

    db.session.commit()

    flash("Usuario activado correctamente.", "success")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:id>/desactivar", methods=["POST"])
@admin_required
def desactivar_usuario(id):
    usuario = Usuario.query.get_or_404(id)

    if usuario.tipo_usuario == "Administrador":
        flash("No se puede desactivar el administrador principal.", "warning")
        return redirect(url_for("usuarios"))

    usuario.activo = False

    for cuenta in usuario.cuentas:
        cuenta.activo = False

    db.session.commit()

    flash("Usuario desactivado correctamente.", "info")
    return redirect(url_for("usuarios"))


@app.route("/prestamos", methods=["GET", "POST"])
@admin_required
def prestamos():
    if request.method == "POST":
        equipo_id = request.form.get("equipo_id")
        usuario_id = request.form.get("usuario_id")
        fecha_devolucion = request.form.get("fecha_devolucion_estimada")
        observaciones = request.form.get("observaciones", "").strip()

        if not equipo_id or not usuario_id or not fecha_devolucion:
            flash("Debes seleccionar equipo, usuario y fecha estimada de devolución.", "warning")
            return redirect(url_for("prestamos"))

        equipo = Equipo.query.get(equipo_id)
        usuario = Usuario.query.get(usuario_id)

        if not equipo:
            flash("El equipo seleccionado no existe.", "danger")
            return redirect(url_for("prestamos"))

        if not usuario:
            flash("El usuario seleccionado no existe.", "danger")
            return redirect(url_for("prestamos"))

        if equipo.estado != "Disponible":
            flash("El equipo seleccionado no está disponible.", "warning")
            return redirect(url_for("prestamos"))

        try:
            fecha_devolucion_estimada = datetime.strptime(fecha_devolucion, "%Y-%m-%d")
        except ValueError:
            flash("La fecha de devolución no es válida.", "danger")
            return redirect(url_for("prestamos"))

        nuevo_prestamo = Prestamo(
            equipo_id=equipo.id,
            usuario_id=usuario.id,
            fecha_solicitud=datetime.now(),
            fecha_prestamo=datetime.now(),
            fecha_devolucion_estimada=fecha_devolucion_estimada,
            estado="Aprobado",
            observaciones=observaciones
        )

        equipo.estado = "Prestado"

        db.session.add(nuevo_prestamo)
        db.session.commit()

        flash("Préstamo directo registrado correctamente.", "success")
        return redirect(url_for("prestamos"))

    estado = request.args.get("estado", "").strip()

    consulta = Prestamo.query

    if estado:
        consulta = consulta.filter_by(estado=estado)

    prestamos_lista = consulta.order_by(Prestamo.fecha_solicitud.desc()).all()

    equipos_disponibles = (
        Equipo.query
        .filter_by(estado="Disponible")
        .order_by(Equipo.nombre.asc())
        .all()
    )

    usuarios_activos = (
        Usuario.query
        .filter(
            Usuario.activo == True,
            Usuario.tipo_usuario.in_(["Estudiante", "Docente", "Encargado"])
        )
        .order_by(Usuario.nombre_completo.asc())
        .all()
    )

    return render_template(
        "prestamos.html",
        prestamos=prestamos_lista,
        estado=estado,
        equipos_disponibles=equipos_disponibles,
        usuarios_activos=usuarios_activos
    )


@app.route("/prestamos/<int:id>/aprobar", methods=["POST"])
@admin_required
def aprobar_prestamo(id):
    prestamo = Prestamo.query.get_or_404(id)

    if prestamo.estado != "Pendiente":
        flash("Solo se pueden aprobar solicitudes pendientes.", "warning")
        return redirect(url_for("prestamos"))

    if prestamo.equipo.estado != "Disponible":
        flash("El equipo ya no se encuentra disponible.", "danger")
        return redirect(url_for("prestamos"))

    prestamo.estado = "Aprobado"
    prestamo.fecha_prestamo = datetime.now()
    prestamo.fecha_devolucion_estimada = datetime.now() + timedelta(days=7)
    prestamo.equipo.estado = "Prestado"

    db.session.commit()

    flash("Préstamo aprobado correctamente.", "success")
    return redirect(url_for("prestamos"))


@app.route("/prestamos/<int:id>/rechazar", methods=["POST"])
@admin_required
def rechazar_prestamo(id):
    prestamo = Prestamo.query.get_or_404(id)

    if prestamo.estado != "Pendiente":
        flash("Solo se pueden rechazar solicitudes pendientes.", "warning")
        return redirect(url_for("prestamos"))

    prestamo.estado = "Rechazado"
    prestamo.observaciones = request.form.get("observaciones", "").strip() or "Solicitud rechazada por administración."

    db.session.commit()

    flash("Solicitud rechazada correctamente.", "info")
    return redirect(url_for("prestamos"))


@app.route("/prestamos/<int:id>/devolver", methods=["POST"])
@admin_required
def devolver_prestamo(id):
    prestamo = Prestamo.query.get_or_404(id)

    if prestamo.estado != "Aprobado":
        flash("Solo se pueden devolver préstamos activos.", "warning")
        return redirect(url_for("prestamos"))

    prestamo.estado = "Devuelto"
    prestamo.fecha_devolucion_real = datetime.now()
    prestamo.equipo.estado = "Disponible"

    observaciones = request.form.get("observaciones", "").strip()
    if observaciones:
        prestamo.observaciones = observaciones

    db.session.commit()

    flash("Devolución registrada correctamente.", "success")
    return redirect(url_for("prestamos"))


@app.route("/reportes")
@admin_required
def reportes():
    total_equipos = Equipo.query.count()
    disponibles = Equipo.query.filter_by(estado="Disponible").count()
    prestados = Equipo.query.filter_by(estado="Prestado").count()
    mantenimiento = Equipo.query.filter_by(estado="Mantenimiento").count()

    pendientes = Prestamo.query.filter_by(estado="Pendiente").count()
    aprobados = Prestamo.query.filter_by(estado="Aprobado").count()
    devueltos = Prestamo.query.filter_by(estado="Devuelto").count()
    rechazados = Prestamo.query.filter_by(estado="Rechazado").count()

    total_usuarios = Usuario.query.count()
    estudiantes = Usuario.query.filter_by(tipo_usuario="Estudiante").count()
    docentes = Usuario.query.filter_by(tipo_usuario="Docente").count()
    encargados = Usuario.query.filter_by(tipo_usuario="Encargado").count()
    administradores = Usuario.query.filter_by(tipo_usuario="Administrador").count()

    estado_counts = {
        "Disponible": disponibles,
        "Prestado": prestados,
        "Mantenimiento": mantenimiento
    }

    tipo_counts = {
        "Estudiantes": estudiantes,
        "Docentes": docentes,
        "Encargados": encargados,
        "Administradores": administradores
    }

    prestamo_counts = {
        "Pendientes": pendientes,
        "Aprobados": aprobados,
        "Devueltos": devueltos,
        "Rechazados": rechazados
    }

    prestamos_recientes = (
        Prestamo.query
        .order_by(Prestamo.fecha_solicitud.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "reportes.html",
        total_equipos=total_equipos,
        disponibles=disponibles,
        prestados=prestados,
        mantenimiento=mantenimiento,
        pendientes=pendientes,
        aprobados=aprobados,
        devueltos=devueltos,
        rechazados=rechazados,
        total_usuarios=total_usuarios,
        estudiantes=estudiantes,
        docentes=docentes,
        encargados=encargados,
        administradores=administradores,
        estado_counts=estado_counts,
        tipo_counts=tipo_counts,
        prestamo_counts=prestamo_counts,
        prestamos_recientes=prestamos_recientes
    )


@app.route("/portal")
@estudiante_required
def estudiante_dashboard():
    usuario_id = session.get("usuario_id")

    equipos_disponibles = Equipo.query.filter_by(estado="Disponible").count()
    mis_pendientes = Prestamo.query.filter_by(usuario_id=usuario_id, estado="Pendiente").count()
    mis_aprobados = Prestamo.query.filter_by(usuario_id=usuario_id, estado="Aprobado").count()
    mis_devueltos = Prestamo.query.filter_by(usuario_id=usuario_id, estado="Devuelto").count()

    ultimas_solicitudes = (
        Prestamo.query
        .filter_by(usuario_id=usuario_id)
        .order_by(Prestamo.fecha_solicitud.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "estudiante_dashboard.html",
        equipos_disponibles=equipos_disponibles,
        mis_pendientes=mis_pendientes,
        mis_aprobados=mis_aprobados,
        mis_devueltos=mis_devueltos,
        ultimas_solicitudes=ultimas_solicitudes
    )


@app.route("/portal/equipos")
@estudiante_required
def estudiante_equipos():
    q = request.args.get("q", "").strip()

    consulta = Equipo.query.filter_by(estado="Disponible")

    if q:
        consulta = consulta.filter(
            or_(
                Equipo.nombre.ilike(f"%{q}%"),
                Equipo.tipo.ilike(f"%{q}%"),
                Equipo.marca.ilike(f"%{q}%"),
                Equipo.modelo.ilike(f"%{q}%"),
                Equipo.numero_serie.ilike(f"%{q}%")
            )
        )

    equipos = consulta.order_by(Equipo.nombre.asc()).all()

    return render_template("estudiante_equipos.html", equipos=equipos, q=q)


def crear_solicitud_prestamo(id):
    equipo = Equipo.query.get_or_404(id)
    usuario_id = session.get("usuario_id")

    if equipo.estado != "Disponible":
        flash("El equipo seleccionado ya no está disponible.", "warning")
        return redirect(url_for("estudiante_equipos"))

    solicitud_existente = Prestamo.query.filter_by(
        equipo_id=equipo.id,
        usuario_id=usuario_id,
        estado="Pendiente"
    ).first()

    if solicitud_existente:
        flash("Ya tienes una solicitud pendiente para este equipo.", "warning")
        return redirect(url_for("estudiante_equipos"))

    observaciones = request.form.get("observaciones", "").strip()

    nuevo_prestamo = Prestamo(
        equipo_id=equipo.id,
        usuario_id=usuario_id,
        estado="Pendiente",
        observaciones=observaciones
    )

    db.session.add(nuevo_prestamo)
    db.session.commit()

    flash("Solicitud enviada correctamente. Espera aprobación del administrador.", "success")
    return redirect(url_for("mis_solicitudes"))


@app.route("/portal/equipos/<int:id>/solicitar", methods=["GET", "POST"])
@estudiante_required
def estudiante_solicitar(id):
    equipo = Equipo.query.get_or_404(id)

    if request.method == "POST":
        return crear_solicitud_prestamo(id)

    return render_template("estudiante_solicitar.html", equipo=equipo)


@app.route("/portal/equipos/<int:id>/solicitar-directo", methods=["POST"])
@estudiante_required
def solicitar_prestamo(id):
    return crear_solicitud_prestamo(id)


@app.route("/portal/mis-solicitudes")
@estudiante_required
def mis_solicitudes():
    usuario_id = session.get("usuario_id")

    prestamos_lista = (
        Prestamo.query
        .filter_by(usuario_id=usuario_id)
        .order_by(Prestamo.fecha_solicitud.desc())
        .all()
    )

    return render_template("estudiante_solicitudes.html", prestamos=prestamos_lista)


@app.route("/portal/solicitudes")
@estudiante_required
def estudiante_solicitudes():
    return redirect(url_for("mis_solicitudes"))


@app.errorhandler(404)
def error_404(error):
    return """
    <h1>Página no encontrada</h1>
    <p>La ruta solicitada no existe dentro del sistema.</p>
    <a href="/">Volver al inicio</a>
    """, 404


@app.errorhandler(500)
def error_500(error):
    return """
    <h1>Error interno del servidor</h1>
    <p>Ocurrió un problema al procesar la solicitud.</p>
    <a href="/">Volver al inicio</a>
    """, 500


if __name__ == "__main__":
    app.run(debug=True)