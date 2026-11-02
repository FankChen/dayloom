import smtplib
import ssl

from dayloom.registry import connectors


@connectors.register
class SmtpSsl:
    def open(self, host):
        return smtplib.SMTP_SSL(host, 465, context=ssl.create_default_context(), timeout=20)


@connectors.register
class SmtpStartTls:
    def open(self, host):
        client = smtplib.SMTP(host, 587, timeout=20)
        try:
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
            return client
        except Exception:
            client.close()
            raise
