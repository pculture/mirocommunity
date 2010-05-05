"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from notification import models as notification

from localtv.user_profile import forms

from localtv import util

Profile = util.get_profile_model()

class ProfileFormTestCase(TestCase):

    fixtures = ['site', 'users']

    def setUp(self):
        self.user = User.objects.get(username='user')
        self.profile = Profile.objects.create(
            user=self.user,
            description='Description',
            location='Location',
            website='http://www.pculture.org/')

    def test_save(self):
        """
        Filling the ProfileForm with data should cause the Profile to be
        updated.
        """
        data = {
            'username': 'newusername',
            'name': 'First Last',
            'email': 'test@foo.bar.com',
            'description': 'New Description',
            'location': 'Where I am',
            'website': 'http://www.google.com'
            }
        form = forms.ProfileForm(data, instance=self.profile)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEquals(instance.user.username, 'newusername')
        self.assertEquals(instance.user.first_name, 'First')
        self.assertEquals(instance.user.last_name, 'Last')
        self.assertEquals(instance.user.email, 'test@foo.bar.com')
        self.assertEquals(instance.description, 'New Description')
        self.assertEquals(instance.location, 'Where I am')
        self.assertEquals(instance.website, 'http://www.google.com/')

    def test_save_no_changes(self):
        """
        A blank form should have all the data to simply resave and not cause
        any changes.
        """
        blank_form = forms.ProfileForm(instance=self.profile)
        form = forms.ProfileForm(blank_form.initial, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertEquals(instance.user.username, self.user.username)
        self.assertEquals(instance.user.first_name, self.user.first_name)
        self.assertEquals(instance.user.last_name, self.user.last_name)
        self.assertEquals(instance.user.email, self.user.email)
        self.assertEquals(instance.description, self.profile.description)
        self.assertEquals(instance.location, self.profile.location)
        self.assertEquals(instance.website, self.profile.website)

class NotificationsFormTestCase(TestCase):

    fixtures = ['site', 'users']

    def test_user_settings(self):
        """
        A regular user should only see the 'video_approved' and 'video_comment'
        notifications.  The initial data for the form should have those
        settings enabled, since they're on by default.
        """
        user = User.objects.get(username='user')
        form = forms.NotificationsForm(instance=user)
        self.assertEquals(len(form.fields['notifications'].choices), 2)
        self.assertEquals(form.initial, {
                'notifications': ['video_approved', 'video_comment']
                })

    def test_save_user_settings(self):
        """
        Saving the form should save the user's settings.
        """
        user = User.objects.get(username='user')
        form = forms.NotificationsForm({'notifications': []}, instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        for label in 'video_comment', 'video_approved':
            notice_type = notification.NoticeType.objects.get(label=label)
            self.assertFalse(notification.should_send(user, notice_type, "1"))

        form = forms.NotificationsForm({'notifications': ['video_approved']},
                                       instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        notice_type = notification.NoticeType.objects.get(
            label='video_approved')
        self.assertTrue(notification.should_send(user, notice_type, "1"))

    def test_admin_settings(self):
        """
        Admins should have the full range of settings available.
        """
        admin = User.objects.get(username='admin')
        form = forms.NotificationsForm(instance=admin)
        self.assertEquals(len(form.fields['notifications'].choices), 6)
        self.assertEquals(form.initial, {
                'notifications': ['video_approved', 'video_comment']
                })

        superuser = User.objects.get(username='superuser')
        form = forms.NotificationsForm(instance=superuser)
        self.assertEquals(len(form.fields['notifications'].choices), 6)
        self.assertEquals(form.initial, {
                'notifications': ['video_approved', 'video_comment']
                })

    def test_save_admin_settings(self):
        """
        Saving the form should save the admin's settings.
        """
        for username in 'admin', 'superuser':
            admin = User.objects.get(username=username)
            form = forms.NotificationsForm({'notifications': [
                        'admin_new_comment',
                        'admin_new_submission',
                        'admin_queue_daily',
                        'admin_queue_weekly']}, instance=admin)
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            for label in 'video_comment', 'video_approved':
                notice_type = notification.NoticeType.objects.get(label=label)
                self.assertFalse(notification.should_send(admin, notice_type,
                                                          "1"))
            for label in ('admin_new_comment', 'admin_new_submission',
                          'admin_queue_daily', 'admin_queue_weekly'):
                notice_type = notification.NoticeType.objects.get(label=label)
                self.assertTrue(notification.should_send(admin, notice_type,
                                                         "1"))

