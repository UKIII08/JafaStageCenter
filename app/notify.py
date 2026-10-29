"""Powiadomienia e-mail dla zespołu: nowe granie (zaznacz dostępność)
i przydzielona partia. Wysyłka w tle, żeby lider nie czekał na SMTP.

Każdy może je wyłączyć w swoim profilu (User.notify_email).
"""
import threading

from flask import current_app, url_for

from app import db
from app.emails import send_email
from app.i18n import instrument_label, nice_date, translate as _
from app.models import Membership, User


def _footer(church_id):
    link = url_for('panel.my_profile', church_id=church_id, _external=True)
    return '\n\n' + _('Don’t want these e-mails? Turn them off in your profile:') + '\n' + link


def _send_all(mails):
    """mails: [(to, subject, body)]. W testach od razu, w aplikacji w tle."""
    def run():
        for to, subject, body in mails:
            try:
                send_email(to, subject, body)
            except Exception as e:      # jeden zły adres nie blokuje reszty
                print(f'[MAIL-ERROR] to={to}: {e}')
    if not mails:
        return
    if current_app.config.get('TESTING'):
        run()
    else:
        threading.Thread(target=run, daemon=True).start()


def _when(ev):
    return nice_date(ev.date) + (f', {ev.time}' if ev.time else '')


def new_service(ev, church, actor_id):
    """Cały zespół (poza autorem): nowe granie, zaznacz, czy możesz grać."""
    link = url_for('events.event_detail', church_id=church.id, eid=ev.id, _external=True)
    users = (User.query.join(Membership, Membership.user_id == User.id)
             .filter(Membership.church_id == church.id, Membership.status == 'active',
                     User.id != actor_id).all())
    mails = []
    for u in users:
        if u.notify_email is False:
            continue
        body = (_('Hi %(name)s!') % {'name': u.display_name} + '\n\n'
                + _('A new service is planned: %(name)s, %(when)s.') % {'name': ev.name, 'when': _when(ev)}
                + '\n')
        if ev.signup_deadline:
            body += _('Let the leader know if you can play, by %(day)s:') % {
                'day': nice_date(ev.signup_deadline, 'daymonth')}
        else:
            body += _('Let the leader know if you can play:')
        body += '\n' + link + _footer(church.id)
        mails.append((u.email, _('%(church)s: can you play on %(day)s?') % {
            'church': church.name, 'day': nice_date(ev.date, 'daymonth')}, body))
    _send_all(mails)


def assigned(ev, church, user_id, instrument, actor_id):
    """Osoba dostała partię w graniu."""
    if user_id == actor_id:
        return
    u = db.session.get(User, user_id)
    if not u or u.notify_email is False:
        return
    part = instrument_label(instrument).lower() if instrument else ''
    link = url_for('events.event_detail', church_id=church.id, eid=ev.id, _external=True)
    body = (_('Hi %(name)s!') % {'name': u.display_name} + '\n\n'
            + (_('You play %(part)s at %(name)s, %(when)s.') % {'part': part, 'name': ev.name, 'when': _when(ev)}
               if part else
               _('You are on the team for %(name)s, %(when)s.') % {'name': ev.name, 'when': _when(ev)})
            + '\n' + _('The setlist and practice are here:') + '\n' + link + _footer(church.id))
    _send_all([(u.email, _('%(church)s: you play on %(day)s') % {
        'church': church.name, 'day': nice_date(ev.date, 'daymonth')}, body)])
