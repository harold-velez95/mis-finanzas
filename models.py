from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from db import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    cobros = relationship('Cobros', back_populates='user')
    pagos = relationship('Pagos', back_populates='user')
    tesoreria = relationship('Tesoreria', back_populates='user')


    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Cobros(db.Model):

    __tablename__ = 'cuentas por cobrar'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    concepto = db.Column(db.String(100), nullable=False)
    importe = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, ForeignKey('user.id'))

    user = relationship('User', back_populates='cobros')

    
    def __init__(self,nombre,fecha,concepto,importe, user_id):
        self.nombre = nombre
        self.fecha = fecha
        self.concepto = concepto
        self.importe = importe
        self.user_id= user_id



class Pagos(db.Model):

    __tablename__ = 'cuentas por pagar'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    concepto = db.Column(db.String(100), nullable=False)
    importe = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, ForeignKey('user.id'))

    user = relationship('User', back_populates='pagos')

    def __init__(self, nombre, fecha, concepto, importe, user_id):
        self.nombre = nombre
        self.fecha = fecha
        self.concepto = concepto
        self.importe = importe
        self.user_id= user_id


class Tesoreria(db.Model):
    
    __tablename__ = 'tesoreria'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    importe = db.Column(db.Float, nullable=False)
    tiporegistro = db.Column(db.String(20), nullable=False)  # "entrada" o "salida"
    descripcion = db.Column(db.String(100), nullable=False)
    concepto = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, ForeignKey('user.id'))

    user = relationship('User', back_populates='tesoreria')

    def __init__(self,tiporegistro, fecha, concepto, importe,descripcion, user_id):
        self.tiporegistro= tiporegistro
        self.fecha = fecha
        self.concepto = concepto
        self.importe = importe
        self.descripcion= descripcion
        self.user_id= user_id






