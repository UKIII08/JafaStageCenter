# Model danych — zakres M0 (users, churches, memberships, profiles, invitations)
# Pełny schemat: PLAN.md §1. Piosenki/setlisty/live dochodzą w M1/M2.
import uuid
from datetime import datetime, timedelta
from app import db


def new_uuid():
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    locale = db.Column(db.String(5), default='pl')
    email_verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    totp_secret = db.Column(db.String(32), nullable=True)   # 2FA (opcjonalne)

    memberships = db.relationship('Membership', back_populates='user')


class Church(db.Model):
    __tablename__ = 'churches'
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    owner_user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    plan = db.Column(db.String(20), default='free_beta')
    locale = db.Column(db.String(5), default='pl')
    timezone = db.Column(db.String(40), default='Europe/Warsaw')
    settings = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    memberships = db.relationship('Membership', back_populates='church')


ROLES = ('admin', 'prowadzacy', 'muzyk')


class Membership(db.Model):
    __tablename__ = 'memberships'
    __table_args__ = (db.UniqueConstraint('user_id', 'church_id'),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    role = db.Column(db.String(20), default='muzyk')
    status = db.Column(db.String(20), default='active')

    user = db.relationship('User', back_populates='memberships')
    church = db.relationship('Church', back_populates='memberships')


class Profile(db.Model):
    """Profil muzyka — klucz hybrydy: może istnieć BEZ konta (user_id NULL,
    np. utworzony w aplikacji desktop) i zostać później 'przejęty'."""
    __tablename__ = 'profiles'
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    instrument = db.Column(db.String(60), default='')
    color = db.Column(db.String(20), default='#6366f1')
    prefs = db.Column(db.JSON, default=dict)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False)


class Invitation(db.Model):
    __tablename__ = 'invitations'
    id = db.Column(db.Integer, primary_key=True)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    code = db.Column(db.String(8), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), nullable=True)   # NULL = link uniwersalny
    role = db.Column(db.String(20), default='muzyk')
    expires_at = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    max_uses = db.Column(db.Integer, nullable=True)
    uses = db.Column(db.Integer, default=0)

    @staticmethod
    def default_expiry():
        return datetime.utcnow() + timedelta(days=14)

    def is_valid(self):
        if datetime.utcnow() > self.expires_at:
            return False
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False
        return True


class Song(db.Model):
    __tablename__ = 'songs'
    __table_args__ = (db.Index('ix_songs_church_title', 'church_id', 'title'),)
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default='')        # ChordPro
    key = db.Column(db.String(10), default='')
    bpm = db.Column(db.Integer, default=0)
    tags = db.Column(db.JSON, default=list)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False)  # tombstone pod sync


class Setlist(db.Model):
    __tablename__ = 'setlists'
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    service_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='draft')
    items = db.Column(db.JSON, default=list)   # [{song_id, transpose}]
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False)
