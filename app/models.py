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


class LiveSession(db.Model):
    __tablename__ = 'live_sessions'
    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    setlist_id = db.Column(db.String(36), db.ForeignKey('setlists.id'))
    started_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    is_practice = db.Column(db.Boolean, default=False)
    # stan bieżącego slajdu trzymamy w app/live/state.py (Redis/pamięć) —
    # w bazie tylko cykl życia sesji


class ScreenToken(db.Model):
    """Stały token dla rzutnika/TV — urządzenie otwiera URL raz i nasłuchuje
    aktywnej sesji swojej wspólnoty; odwoływalny z panelu."""
    __tablename__ = 'screen_tokens'
    id = db.Column(db.Integer, primary_key=True)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    token = db.Column(db.String(43), unique=True, nullable=False, index=True)
    type = db.Column(db.String(20), default='projector')  # projector|stage
    name = db.Column(db.String(120), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    revoked_at = db.Column(db.DateTime, nullable=True)


class SongPersonal(db.Model):
    """"Moje tonacje" + prywatne notatki: preferencje muzyka per piosenka.
    Kluczowane po profilu (nie koncie) — patrz PLAN §1: identycznie działa
    dla muzyka zalogowanego na stronie i profilu z aplikacji desktop."""
    __tablename__ = 'song_personal'
    __table_args__ = (db.UniqueConstraint('profile_id', 'song_id'),)
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.String(36), db.ForeignKey('profiles.id'),
                           nullable=False, index=True)
    song_id = db.Column(db.String(36), db.ForeignKey('songs.id'),
                        nullable=False, index=True)
    preferred_transpose = db.Column(db.Integer, nullable=True)
    preferred_key = db.Column(db.String(10), nullable=True)
    note = db.Column(db.Text, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    # Studio (port panelu desktop): capo per piosenka + notatki per sekcja
    capo_fret = db.Column(db.Integer, nullable=True)
    section_notes = db.Column(db.Text, default='{}')   # JSON {"0": "...", ...}


class BandPreset(db.Model):
    """Presety widoku członka zespołu (port BandPreset z desktopu),
    per wspólnota."""
    __tablename__ = 'band_presets'
    id = db.Column(db.Integer, primary_key=True)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    show_chords = db.Column(db.Boolean, default=True)
    nashville_mode = db.Column(db.Boolean, default=False)
    chord_notation = db.Column(db.String(15), default='international')
    lowercase_minor = db.Column(db.Boolean, default=False)
    capo_fret = db.Column(db.Integer, default=0)
    beginner_mode = db.Column(db.Boolean, default=False)
    diagram_instrument = db.Column(db.String(10), default='guitar')
    font_size = db.Column(db.Integer, default=6)


class StudioSetlist(db.Model):
    """Historia setlist Studia (port SetlistHistory z desktopu) — snapshot
    piosenek z transpozycjami + opcjonalny kod udostępniania."""
    __tablename__ = 'studio_setlists'
    id = db.Column(db.Integer, primary_key=True)
    church_id = db.Column(db.String(36), db.ForeignKey('churches.id'),
                          nullable=False, index=True)
    name = db.Column(db.String(200), default='')
    date = db.Column(db.String(30), nullable=False, default='')
    songs = db.Column(db.Text, nullable=False, default='[]')  # JSON [{id,title,key,bpm,transpose}]
    share_code = db.Column(db.String(8), unique=True, nullable=True, index=True)
