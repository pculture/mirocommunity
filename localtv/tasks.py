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
        stderr=subprocess.PIPE)

    return_code = process.wait()
    if return_code: # some problem with the code
        stderr = [process.stderr.read()]
        while stderr[-1] != '':
            stderr.append(process.stderr.read())

        raise RuntimeError('Error during: %s\n\nTraceback:\n%s' % (
                ' '.join(args), ''.join(stderr)))
    else: # imported the feed correctly
        stdout = [process.stdout.read()]
        while stdout[-1] != '':
            stdout.append(process.stdout.read())
        return ''.join(stdout)

