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

#import eventlet
#eventlet.monkey_patch()
from eventlet.green import urllib2

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import logging
import os
import subprocess

try:
    from PIL import Image
except:
    import Image

from celery.task import task
from celery.task.sets import subtask
from django.db.models.loading import get_model
from haystack import site

@task
def check_call(args, env={}):
    args = [str(arg) for arg in args]
    environ = os.environ.copy()
    environ.update(env)
    process = subprocess.Popen(
        args,
        executable=args[0],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environ)

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

@task
def vidscraper_load(obj):
    try:
        obj.load()
    except Exception:
        logging.exception('while importing %r' % obj)
    return obj

@task
def http_read(url, timeout=10):
    return urllib2.urlopen(url, timeout=timeout).read()

@task(max_retries=None)
def thumbnails_from_url(url, thumb_sizes, result=None, retry=1.0,
                        max_retries=None):
    if not result:
        result = http_read.delay(url)

    if not result.ready():
        thumbnails_from_url.retry(
            (url, thumb_sizes, result, retry, max_retries),
            countdown=retry, max_retries=max_retries)

    data = result.get()
    from localtv.utils import resize_image_returning_list_of_strings
    image_file = Image.open(StringIO(data))
    thumbnails = [('original', data)]
    return thumbnails + resize_image_returning_list_of_strings(
        image_file, thumb_sizes)

@task(ignore_result=True)
def haystack_update_index(app_label, model_name, pk, is_removal):
    """
    Updates a haystack index for the given model (specified by ``app_label``
    and ``model_name``). If ``is_removal`` is ``True``, a fake instance is
    constructed with the given ``pk`` and passed to the index's
    :meth:`remove_object` method. Otherwise, the latest version of the instance
    is fetched from the database and passed to the index's
    :meth:`update_object` method.

    """
    model_class = get_model(app_label, model_name)
    search_index = site.get_index(model_class)
    if is_removal:
        instance = model_class(pk=pk)
        search_index.remove_object(instance)
    else:
        try:
            instance = search_index.read_queryset().get(pk=pk)
        except model_class.DoesNotExist:
            pass
        else:
            search_index.update_object(instance)

