# Wysyłka e-maili (reset hasła itp.) — zaprojektowana pod ZEROWY koszt:
# darmowy SMTP (np. Brevo: 300 maili/dzień) konfigurowany zmiennymi
# środowiskowymi. Bez konfiguracji (dev) mail ląduje w logu serwera.
import os
import smtplib
from email.message import EmailMessage


def send_email(to, subject, body):
    host = os.environ.get('SMTP_HOST')
    if not host:
        print(f'[MAIL-DEV] to={to} subject={subject}\n{body}')
        return False
    msg = EmailMessage()
    msg['From'] = os.environ.get('SMTP_FROM', 'JafaStage <no-reply@localhost>')
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, int(os.environ.get('SMTP_PORT', 587))) as s:
        s.starttls()
        s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        s.send_message(msg)
    return True
