# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
from celery.decorators import task

@task()
def check_call(args):
    args = [str(arg) for arg in args]
    process = subprocess.Popen(
        args,
        executable=args[0],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    stderr = []
    while process.poll() is None:
        # #17982: the stderr buffer can fill, so make sure to pull the data
        # out of the buffer
        err = process.stderr.read()
        if err:
            stderr.append(err)

    return_code = process.wait()
    if return_code: # some problem with the code
        while stderr[-1] != '':
            stderr.append(process.stderr.read())

        raise RuntimeError('Error during: %s\n\nTraceback:\n%s' % (
                ' '.join(args), ''.join(stderr)))
    else: # imported the feed correctly
        stdout = [process.stdout.read()]
        while stdout[-1] != '':
            stdout.append(process.stdout.read())
        return ''.join(stdout)

