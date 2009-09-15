import os.path
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):

    args = '[version]'
    help = 'Freeze the current templates and static resources.'

    def handle(self, *args, **kwargs):
        if len(args) != 1 or not args[0]:
            raise CommandError('You must provide a version string.')

        version = args[0]

        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../..'))

        versioned_static_dir = os.path.join(repo_root, 'static', 'versioned',
                                            version)
        versioned_templates_dir = os.path.join(repo_root, 'localtv',
                                               'versioned_templates',
                                               version)

        if os.path.exists(versioned_static_dir) or os.path.exists(
            versioned_templates_dir):
            raise CommandError('version %s is already frozen' % version)

        os.mkdir(versioned_static_dir)

        for static_path in ('css', 'images', 'js', 'swf'):
            shutil.copytree(
                os.path.join(settings.MEDIA_ROOT, static_path),
                os.path.join(versioned_static_dir, static_path))

        for template_dir in settings.TEMPLATE_DIRS[::-1]:
            # do it in reverse order, so that the first template that would
            # load overwrites the others
            if versioned_templates_dir.startswith(
                os.path.realpath(template_dir)):
                continue
            if not os.path.exists(template_dir):
                continue
            shutil.copytree(template_dir, versioned_templates_dir)
