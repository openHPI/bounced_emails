import click
import smtplib
from systemd import journal
from datetime import datetime, timedelta


@click.command()
@click.option('--filepath', default='./testmail', help='Filepath to bounced email')
def smtptest(filepath):
    with open(filepath) as f:
        message = f.read()

    try:
        with smtplib.SMTP('127.0.0.1', 2525) as server:
            server.sendmail(
                'bouncedemails@bouncedemails.aux.xopic.de',
                'bouncedemails@bouncedemails.aux.xopic.de',
                message)
        print('Testmail sent')
        print('---')
        print('Journallog entries')
        j = journal.Reader()
        j.seek_realtime(datetime.now() - timedelta(seconds=2))
        for entry in j:
            print(entry["MESSAGE"])

    except smtplib.SMTPException as e:
        print('SMTP error occurred: ' + str(e))

if __name__ == '__main__':
    smtptest()
