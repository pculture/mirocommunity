import subprocess
import logging
from celery.decorators import task
from django.core.mail import mail_admins

@task()
def check_call(args):
    args = [str(arg) for arg in args]
    process = subprocess.Popen(
        args,
        executable=args[0],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)

    return_code = process.wait()
    stdout = [process.stdout.read()]
    while stdout[-1] != '':
        stdout.append(process.stdout.read())
    if return_code: # some problem with the code
        logging.info('Error running bulk import:\n%s' % ''.join(stdout))
        mail_admins('Error running bulk_import: %s' % (' '.join(args)),
                    ''.join(stdout))
        raise RuntimeError('error during bulk import')
    else: # imported the feed correctly
        return ''.join(stdout)

