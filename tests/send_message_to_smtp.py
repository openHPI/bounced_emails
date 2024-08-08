import click
import smtplib
from systemd import journal


@click.command()
@click.option('-f', '--filepath', default='./testmail', help='Filepath to bounced email')
@click.option('-l', '--lines', default=8, help='Seek the last x lines from journal')
def smtptest(filepath, lines):
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
        j.seek_tail()
        entries = []

        i = 1
        while i <= lines:
            entries.append(j.get_previous())
            i += 1

        for e in reversed(entries):
            print(e['MESSAGE'])

    except smtplib.SMTPException as e:
        print('SMTP error occurred: ' + str(e))

if __name__ == '__main__':
    smtptest()
