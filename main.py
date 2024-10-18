import base64
import io
from docx import Document
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, abort, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from matplotlib import pyplot as plt
from sqlalchemy import func, extract
from models import Cobros, Pagos, Tesoreria,User
import db
from db import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


#-----------------funciones-----------------------------------
def obtener_patrimonio(user_id):
    resultados = db.session.query(
        Tesoreria.descripcion,
        Tesoreria.tiporegistro,
        Tesoreria.concepto,
        func.sum(Tesoreria.importe).label('importe')
    ).filter_by(user_id=user_id).group_by(Tesoreria.descripcion, Tesoreria.tiporegistro, Tesoreria.concepto).all()

    conceptos = db.session.query(Tesoreria.concepto,
        func.sum(Tesoreria.importe).label('importe')
    ).filter(Tesoreria.concepto == "Activos no corrientes",
             Tesoreria.tiporegistro == 'salida').filter_by(user_id= user_id).all()

    tesoreria = {'Bitcoin': 0, 'Activos': 0, 'Tarjetas': 0, 'Efectivo': 0, "Activos no corrientes": 0}
    tipo_concepto = {'Fondos_propios': 0, 'largo_plazo': 0, 'corto_plazo': 0}

    for resultado in resultados:
        if resultado.tiporegistro == 'entrada':
            tesoreria[resultado.descripcion] += resultado.importe
        elif resultado.tiporegistro == 'salida':
            tesoreria[resultado.descripcion] -= resultado.importe

    for r in conceptos:
        if r.concepto:
            tesoreria[r.concepto] += r.importe


    cobros = db.session.query(func.sum(Cobros.importe)).filter_by(user_id=user_id).scalar() or 0
    pagos = db.session.query(func.sum(Pagos.importe).label('importe'), Pagos.concepto).filter_by(user_id=user_id).group_by(Pagos.concepto).all()
    for p in pagos:
        if p.concepto == "Fondo de capital":
            tipo_concepto["Fondos_propios"] += p.importe
        elif p.concepto == 'Inversiones':
            tipo_concepto["largo_plazo"] += p.importe
        else:
            tipo_concepto["corto_plazo"] += p.importe


    return tesoreria, cobros, tipo_concepto


def obtener_resultado(mes):
    user = current_user
    # Inicializar los datos financieros
    datos_financieros = {
        'ventas_totales': 0,
        'otras_entradas': 0,
        'gastos_totales': 0,
        'margen': 0,
        'nomina': 0,
        'servicios': 0,
        'transporte': 0,
        'Arriendo': 0,
        'bai': 0,
        'gestoria': 0,
        'autonomo': 0,
        'impuestos': 0,
        'margen_neto': 0
    }
    datos_meses = {
        "1": 'Enero',
        "2": 'Febrero',
        "3": 'Marzo',
        "4": 'Abril',
        "5": 'Mayo',
        "6": 'Junio',
        "7": 'Julio',
        "8": 'Agosto',
        "9": 'Septiembre',
        "10": 'Octubre',
        "11": 'Noviembre',
        "12": 'Diciembre'
    }

    # Obtener los datos financieros del usuario para el mes y año dados
    datos = db.session.query(
        func.sum(Tesoreria.importe).label('total_importe'),
        Tesoreria.tiporegistro,
        Tesoreria.concepto
    ).filter(
        Tesoreria.user_id == user.id,
        extract('month', Tesoreria.fecha) == mes
    ).group_by(Tesoreria.tiporegistro, Tesoreria.concepto).all()

    # Mapear los resultados de la consulta a 'datos_financieros'
    for total_importe, tiporegistro, concepto in datos:
        if tiporegistro == 'entrada' and concepto == 'Ventas':
            datos_financieros['ventas_totales'] = total_importe
        elif tiporegistro == 'entrada' and concepto in ['Fondo de capital', 'Inversiones', 'Acreedores', 'Préstamo',
                                                        'Entrada extraordinaria']:
            datos_financieros['otras_entradas'] += total_importe
        elif tiporegistro == 'salida' and concepto in ['Mercadona', 'Ecopack', 'Consum', 'Proveedores']:
            datos_financieros['gastos_totales'] += total_importe
        elif tiporegistro == 'salida' and concepto == 'Transporte':
            datos_financieros['transporte'] = total_importe
        elif tiporegistro == 'salida' and concepto == 'Arriendo':
            datos_financieros['Arriendo'] += total_importe
        elif tiporegistro == 'salida' and concepto in ('Nómina', 'Fondo de capital'):
            datos_financieros['nomina'] += total_importe
        elif tiporegistro == 'salida' and concepto == 'Gestoría':
            datos_financieros['gestoria'] = total_importe
        elif tiporegistro == 'salida' and concepto == 'Impuestos':
            datos_financieros['impuestos'] = total_importe
        elif tiporegistro == 'salida' and concepto == 'Cuota de autónomo':
            datos_financieros['autonomo'] = total_importe
        elif tiporegistro == 'salida' and concepto == 'Servicios':
            datos_financieros['servicios'] = total_importe

    datos_financieros['margen'] = datos_financieros['ventas_totales'] - datos_financieros['gastos_totales']
    datos_financieros['bai'] = datos_financieros['margen'] + datos_financieros['otras_entradas'] - datos_financieros[
        'nomina'] - datos_financieros['servicios'] - datos_financieros['transporte'] - datos_financieros['Arriendo']
    datos_financieros['margen_neto'] = datos_financieros['bai'] - datos_financieros['gestoria'] - datos_financieros[
        'autonomo'] - datos_financieros['impuestos']

    return datos_financieros, datos_meses[mes]

#---------ruta de login y register----------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form.get('password')

        if username and email and password:
            # Verificar si el email ya existe
            existing_user_email = User.query.filter_by(email=email).first()
            if existing_user_email:
                flash('Este Email ya está en uso.', 'register_error')
                return redirect(url_for('register'))

            # Verificar si el nombre de usuario ya existe
            existing_user_username = User.query.filter_by(username=username).first()
            if existing_user_username:
                flash('Este nombre de usuario ya está en uso.', 'register_error')
                return redirect(url_for('register'))

            # Crear el nuevo usuario
            user = User(username=username, email=email)
            user.password = password  # Utiliza el setter para generar el hash de la contraseña
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('main'))

        flash('Por favor, proporcione un nombre de usuario, correo electrónico y contraseña válidos', 'register_error')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main'))
        flash('Usuario o Contraseña incorrectas.','login_error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


#--------- Pagina principal---------------
@app.route("/main")
@login_required
def main():
    return render_template('index.html')


# ----------- Opciones de la pagina -----------------

@app.route('/cobros')
@login_required
def cobros():
    user = current_user
    cobros = db.session.query(Cobros).filter_by(user_id=user.id).all()
    return render_template('cobros.html', cobros=cobros, user=user)


@app.route('/pagos')
@login_required
def pagos():
    user = current_user
    pagos = db.session.query(Pagos).filter_by(user_id=user.id).all()
    return render_template('pagos.html', pagos=pagos, user=user)


@app.route('/tesoreria')
@login_required
def tesoreria():
    user = current_user
    tesoreria = db.session.query(Tesoreria).filter_by(user_id=user.id).all()
    # Ejecuta la consulta para obtener las sumas agrupadas por tiporegistro
    resultado_entrada = db.session.query(
        func.sum(Tesoreria.importe).label('importe'),
        Tesoreria.tiporegistro.label('tiporegistro')
    ).filter_by(user_id=user.id).group_by(Tesoreria.tiporegistro).all()

    # Inicializamos las variables para las sumas de entradas y salidas
    total_entrada = 0
    total_salida = 0

    # Iteramos sobre los resultados de la consulta
    for resultado in resultado_entrada:
        if resultado.tiporegistro == 'entrada':
            total_entrada += resultado.importe
        elif resultado.tiporegistro == 'salida':
            total_salida += resultado.importe

    # Calculamos la diferencia entre entradas y salidas
    valor_final = total_entrada - total_salida

    return render_template('tesoreria.html', tesoreria=tesoreria, resultado_entrada=valor_final, user=user)


@app.route('/resultados', methods=['GET', 'POST'])
def resultados():
    datos_financieros = {}
    datos_meses = {}

    if request.method == 'POST':
        # Suponiendo que el usuario selecciona un mes
        mes = request.form.get('month')  # Capturar el mes del formulario
        datos_financieros, mes_nombre = obtener_resultado(mes)  # Obtener los datos y el nombre del mes

        # Renderizar la plantilla con los datos financieros y el nombre del mes seleccionado
        return render_template('resultados.html', datos_financieros=datos_financieros, datos_meses=mes_nombre)

    # Si es una solicitud GET, devolver una plantilla vacía o con valores por defecto
    return render_template('resultados.html', datos_financieros={}, datos_meses="")

@app.route('/patrimonio')
@login_required
def patrimonio():
    user = current_user
    tesoreria, cobros, tipo_concepto = obtener_patrimonio(user.id)

    return render_template('patrimonio.html', tesoreria=tesoreria, cobros=cobros, tipo_concepto = tipo_concepto)


@app.route('/generate_report/<mes>', methods=['GET'])
@login_required
def generate_report(mes):
    try:
        user = current_user
        # Inicializar los datos financieros
        datos_financieros = {
            'ventas_totales': 0,
            'otras_entradas': 0,
            'gastos_totales': 0,
            'margen': 0,
            'nomina': 0,
            'servicios': 0,
            'transporte': 0,
            'Arriendo': 0,
            'bai': 0,
            'gestoria': 0,
            'autonomo': 0,
            'impuestos': 0,
            'margen_neto': 0
        }
        datos_meses = {
            "1": 'Enero',
            "2": 'Febrero',
            "3": 'Marzo',
            "4": 'Abril',
            "5": 'Mayo',
            "6": 'Junio',
            "7": 'Julio',
            "8": 'Agosto',
            "9": 'Septiembre',
            "10": 'Octubre',
            "11": 'Noviembre',
            "12": 'Diciembre'
        }

        # Obtener los datos financieros del usuario para el mes y año dados
        datos = db.session.query(
            func.sum(Tesoreria.importe).label('total_importe'),
            Tesoreria.tiporegistro,
            Tesoreria.concepto
        ).filter(
            Tesoreria.user_id == user.id,
            extract('month', Tesoreria.fecha) == mes
        ).group_by(Tesoreria.tiporegistro, Tesoreria.concepto).all()

        # Mapear los resultados de la consulta a 'datos_financieros'
        for total_importe, tiporegistro, concepto in datos:
            if tiporegistro == 'entrada' and concepto == 'Ventas':
                datos_financieros['ventas_totales'] = total_importe
            elif tiporegistro == 'entrada' and concepto in ['Fondo de capital', 'Inversiones', 'Acreedores','Préstamo','Entrada extraordinaria']:
                datos_financieros['otras_entradas'] += total_importe
            elif tiporegistro == 'salida' and concepto in ['Mercadona', 'Ecopack', 'Consum', 'Proveedores']:
                datos_financieros['gastos_totales'] += total_importe
            elif tiporegistro == 'salida' and concepto == 'Transporte':
                datos_financieros['transporte'] = total_importe
            elif tiporegistro == 'salida' and concepto == 'Arriendo':
                datos_financieros['Arriendo'] += total_importe
            elif tiporegistro == 'salida' and concepto in ('Nómina', 'Fondo de capital'):
                datos_financieros['nomina'] += total_importe
            elif tiporegistro == 'salida' and concepto == 'Gestoría':
                datos_financieros['gestoria'] = total_importe
            elif tiporegistro == 'salida' and concepto == 'Impuestos':
                datos_financieros['impuestos'] = total_importe
            elif tiporegistro == 'salida' and concepto == 'Cuota de autónomo':
                datos_financieros['autonomo'] = total_importe
            elif tiporegistro == 'salida' and concepto == 'Servicios':
                datos_financieros['servicios'] = total_importe

        datos_financieros['margen']= datos_financieros['ventas_totales']-datos_financieros['gastos_totales']
        datos_financieros['bai'] = datos_financieros['margen'] + datos_financieros['otras_entradas'] - datos_financieros['nomina'] - datos_financieros['servicios'] - datos_financieros['transporte'] - datos_financieros['Arriendo']
        datos_financieros['margen_neto'] = datos_financieros['bai'] - datos_financieros['gestoria'] - datos_financieros['autonomo'] - datos_financieros['impuestos']

        tesoreria, cobros, tipo_concepto = obtener_patrimonio(user.id)
        # Obtener el nombre del mes
        mes_nombre = datos_meses.get(mes, 'Mes desconocido')

        # Cargar el documento Word
        template_path = 'REPORTE FINANCIERO_{{mes}}.docx'
        doc = Document(template_path)

        # Reemplazar los placeholders con los datos reales
        for p in doc.paragraphs:
            p.text = p.text.replace('{{total_ventas}}', str(datos_financieros['ventas_totales']))
            p.text = p.text.replace('{{otras_entradas}}', str(datos_financieros['otras_entradas']))
            p.text = p.text.replace('{{total_gastos}}', str(datos_financieros['gastos_totales']))
            p.text = p.text.replace('{{margen_mes}}', str(datos_financieros['margen']))
            p.text = p.text.replace('{{nomina}}', str(datos_financieros['nomina']))
            p.text = p.text.replace('{{servicios}}', str(datos_financieros['servicios']))
            p.text = p.text.replace('{{transporte}}', str(datos_financieros['transporte']))
            p.text = p.text.replace('{{arriendo}}', str(datos_financieros['Arriendo']))
            p.text = p.text.replace('{{bai}}', str(datos_financieros['bai']))
            p.text = p.text.replace('{{gestoria}}', str(datos_financieros['gestoria']))
            p.text = p.text.replace('{{autonomo}}', str(datos_financieros['autonomo']))
            p.text = p.text.replace('{{impuestos}}', str(datos_financieros['impuestos']))
            p.text = p.text.replace('{{margen_neto}}', str(datos_financieros['margen_neto']))
            p.text = p.text.replace('{{mes}}', mes_nombre)
            p.text = p.text.replace('{{bitcoin}}', str(tesoreria['Bitcoin']))
            p.text = p.text.replace('{{activos}}', str(tesoreria['Activos no corrientes']))
            p.text = p.text.replace('{{tarjetas}}', str(tesoreria['Tarjetas']))
            p.text = p.text.replace('{{efectivo}}', str(tesoreria['Efectivo']))
            p.text = p.text.replace('{{cobros}}', str(cobros))
            p.text = p.text.replace('{{fondos}}', str(tipo_concepto['Fondos_propios']))
            p.text = p.text.replace('{{largo}}', str(tipo_concepto['largo_plazo']))
            p.text = p.text.replace('{{corto}}', str(tipo_concepto['corto_plazo']))
            p.text = p.text.replace('{{pagos}}', str(sum(tipo_concepto.values())))
            p.text = p.text.replace('{{suma}}', str(cobros + sum(tesoreria.values())))

        # Guardar el documento modificado
        output_path = f'REPORTE_FINANCIERO_{mes_nombre}.docx'
        doc.save(output_path)
        print(f'Reporte guardado como {output_path}')

        # Devolver el archivo como una descarga
        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


# ------------ FORMULARIOS DE CREACION -----------------
@app.route("/formulariocobros")
@login_required
def formulariocobros():
    return render_template("formcobros.html")


@app.route('/crearpagos')
@login_required
def crearpagos():
    return render_template('formpagos.html')


@app.route('/creartesoreria')
@login_required
def creartesoreria():
    return render_template('formtesoreria.html')


# ----------------------------------TABLAS DE INFORMACION----------------------------------------------------
@app.route("/info/<name>/<var>")
@login_required
def info(name, var):
    if var == '5':
        tesoreria = db.session.query(Tesoreria).filter_by(id=name, user_id=current_user.id)
        if not tesoreria:
            abort(404)
        return render_template('info_tesoreria.html', tesoreria=tesoreria)
    elif var == '6':
        pagos2 = db.session.query(Pagos).filter_by(id=name, user_id=current_user.id)
        if not pagos2:
            abort(404)
        return render_template("info_pagos.html", pagos2=pagos2)
    elif var == '7':
        todas_explotaciones = db.session.query(Cobros).filter_by(id=name, user_id=current_user.id)
        if not todas_explotaciones:
            abort(404)
        return render_template("info_cobros.html", lista_explotaciones=todas_explotaciones)
    else:
        flash('parametros no validos')
        return redirect(url_for('main'))



# ----------------------------------CREAR----------------------------------------------------
@app.route('/crear/<var>/', methods=['POST'])
@login_required
def crear(var):
    if var == '5':
        fecha_str = request.form["fecha"]
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        user_id = current_user.id
        tesoreria = Tesoreria(tiporegistro=request.form["tiporegistro"], fecha=fecha,
                              descripcion=request.form["descripcion"],
                              concepto=request.form["concepto"], importe=request.form["importe"], user_id=user_id)
        db.session.add(tesoreria)
        db.session.commit()
        db.session.close()
        return redirect(url_for('tesoreria'))

    elif var == '6':
        fecha_str = request.form["fecha"]
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        user_id = current_user.id
        pagos = Pagos(nombre=request.form["nombre"], fecha=fecha,
                      concepto=request.form["concepto"], importe=request.form["importe"], user_id=user_id)
        if request.form["concepto"] not in ("Nómina" , "Proveedores"):
            tesoreria = Tesoreria(tiporegistro= "entrada", fecha=fecha,
                                  descripcion="Efectivo",
                                  concepto=request.form["concepto"], importe=request.form["importe"], user_id=user_id)
            db.session.add(tesoreria)
            db.session.commit()
            db.session.close()
        db.session.add(pagos)
        db.session.commit()
        db.session.close()
        return redirect(url_for('pagos'))

    elif var == '7':
        fecha_str = request.form["fecha"]
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        user_id= current_user.id
        cobros = Cobros(nombre=request.form["nombre"], fecha=fecha,
                        concepto=request.form["concepto"], importe=request.form["importe"],user_id=user_id)

        db.session.add(cobros)
        db.session.commit()
        db.session.close()
        return redirect(url_for('cobros'))
    return render_template('')


# ----------------------------------ELIMINAR----------------------------------------------------

@app.route('/eliminar/<tipo>/<id>')
@login_required
def eliminar(tipo, id):
    if tipo == '5':
        tesoreria = db.session.query(Tesoreria).filter_by(id=id).first()
        db.session.delete(tesoreria)
        db.session.commit()
        db.session.close()
        return redirect(url_for('tesoreria'))
    elif tipo == '6':
        pagos = db.session.query(Pagos).filter_by(id=id).first()
        db.session.delete(pagos)
        db.session.commit()
        db.session.close()
        return redirect(url_for('pagos'))
    elif tipo == '7':
        cobros = db.session.query(Cobros).filter_by(id=id).first()
        db.session.delete(cobros)
        db.session.commit()
        db.session.close()
        return redirect(url_for('cobros'))
    else:
        return redirect(url_for(''))


# ----------------------------------EDITAR------------------------------------------------
@app.route('/editar/<tipo>/<id>', methods=['POST'])
@login_required
def editar(tipo,id):
    if tipo == '5':
        tesoreria = db.session.query(Tesoreria).filter_by(id=id).first()
        if tesoreria:
            fecha_str = request.form["fecha"]
            tesoreria.fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            tesoreria.descripcion = request.form['descripcion']
            tesoreria.concepto = request.form['concepto']
            tesoreria.importe = request.form['importe']
            db.session.commit()
            db.session.close()
        return redirect(url_for('tesoreria'))
    elif tipo == '6':
        pagos = db.session.query(Pagos).filter_by(id=id).first()
        if pagos:
            pagos.importe = int(pagos.importe) - int(request.form['importe'])
            tesoreria = Tesoreria(tiporegistro="salida", fecha=pagos.fecha,
                                  descripcion=request.form["descripcion"],
                                  concepto=pagos.concepto, importe=request.form["importe"], user_id=pagos.user_id)
            db.session.add(tesoreria)
            db.session.commit()
            db.session.close()
        return redirect(url_for('pagos'))
    elif tipo == '7':
        cobros = db.session.query(Cobros).filter_by(id=id).first()
        if cobros:
            cobros.importe = int(cobros.importe) - int(request.form['importe'])
            tesoreria = Tesoreria(tiporegistro="entrada", fecha=cobros.fecha,
                                  descripcion=request.form["descripcion"],
                                  concepto=cobros.concepto, importe=request.form["importe"], user_id=cobros.user_id)
            db.session.add(tesoreria)
            db.session.commit()
            db.session.close()
        return redirect(url_for('cobros'))
    else:
        return redirect(url_for(''))
#-------------------errores--------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crea las tablas de la base de datos
    app.run(debug=True)
    app.jinja_env.globals.update(zip=zip)
    app.run(debug=True)
