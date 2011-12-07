# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'FeedImport.feed'
        db.delete_column('localtv_feedimport', 'feed_id')

        # Adding field 'FeedImport.source'
        db.add_column('localtv_feedimport', 'source',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='imports', to=orm['localtv.Feed']),
                      keep_default=False)

        # Deleting field 'SearchImport.search'
        db.delete_column('localtv_searchimport', 'search_id')

        # Adding field 'SearchImport.source'
        db.add_column('localtv_searchimport', 'source',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, related_name='imports', to=orm['localtv.SavedSearch']),
                      keep_default=False)

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'FeedImport.feed'
        raise RuntimeError("Cannot reverse this migration. 'FeedImport.feed' and its values cannot be restored.")
        # Deleting field 'FeedImport.source'
        db.delete_column('localtv_feedimport', 'source_id')


        # User chose to not deal with backwards NULL issues for 'SearchImport.search'
        raise RuntimeError("Cannot reverse this migration. 'SearchImport.search' and its values cannot be restored.")
        # Deleting field 'SearchImport.source'
        db.delete_column('localtv_searchimport', 'source_id')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'localtv.category': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('slug', 'site'), ('name', 'site'))", 'object_name': 'Category'},
            'contest_mode': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_set'", 'null': 'True', 'to': "orm['localtv.Category']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'localtv.feed': {
            'Meta': {'unique_together': "(('feed_url', 'site'),)", 'object_name': 'Feed'},
            'auto_approve': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'auto_feed_set'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'auto_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Category']", 'symmetrical': 'False', 'blank': 'True'}),
            'avoid_frontpage': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'calculated_source_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'has_thumbnail': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'webpage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'when_submitted': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'localtv.feedimport': {
            'Meta': {'ordering': "['-start']", 'object_name': 'FeedImport'},
            'auto_approve': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'imports'", 'to': "orm['localtv.Feed']"}),
            'start': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'started'", 'max_length': '10'}),
            'total_videos': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'videos_imported': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'videos_skipped': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'localtv.feedimporterror': {
            'Meta': {'object_name': 'FeedImportError'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_skip': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'source_import': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'errors'", 'to': "orm['localtv.FeedImport']"}),
            'traceback': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'localtv.feedimportindex': {
            'Meta': {'object_name': 'FeedImportIndex'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'source_import': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.FeedImport']"}),
            'video': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['localtv.Video']", 'unique': 'True'})
        },
        'localtv.newslettersettings': {
            'Meta': {'object_name': 'NewsletterSettings'},
            'facebook_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intro': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'last_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'repeat': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'show_icon': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'sitelocation': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['localtv.SiteLocation']", 'unique': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'twitter_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'video1': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter1'", 'null': 'True', 'to': "orm['localtv.Video']"}),
            'video2': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter2'", 'null': 'True', 'to': "orm['localtv.Video']"}),
            'video3': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter3'", 'null': 'True', 'to': "orm['localtv.Video']"}),
            'video4': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter4'", 'null': 'True', 'to': "orm['localtv.Video']"}),
            'video5': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsletter5'", 'null': 'True', 'to': "orm['localtv.Video']"})
        },
        'localtv.originalvideo': {
            'Meta': {'object_name': 'OriginalVideo'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'remote_thumbnail_hash': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64'}),
            'remote_video_was_deleted': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'thumbnail_updated': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '400', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'original'", 'unique': 'True', 'to': "orm['localtv.Video']"})
        },
        'localtv.savedsearch': {
            'Meta': {'object_name': 'SavedSearch'},
            'auto_approve': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'auto_savedsearch_set'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'auto_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Category']", 'symmetrical': 'False', 'blank': 'True'}),
            'has_thumbnail': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'query_string': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'when_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'localtv.searchimport': {
            'Meta': {'ordering': "['-start']", 'object_name': 'SearchImport'},
            'auto_approve': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'imports'", 'to': "orm['localtv.SavedSearch']"}),
            'start': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'started'", 'max_length': '10'}),
            'total_videos': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'videos_imported': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'videos_skipped': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'localtv.searchimporterror': {
            'Meta': {'object_name': 'SearchImportError'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_skip': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'source_import': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'errors'", 'to': "orm['localtv.SearchImport']"}),
            'traceback': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'localtv.searchimportindex': {
            'Meta': {'object_name': 'SearchImportIndex'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'source_import': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.SearchImport']"}),
            'suite': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'video': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['localtv.Video']", 'unique': 'True'})
        },
        'localtv.sitelocation': {
            'Meta': {'object_name': 'SiteLocation'},
            'about_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'admin_for'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'comments_required_login': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'css': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'display_submit_button': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'footer_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'has_thumbnail': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hide_get_started': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'playlists_enabled': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'screen_all_comments': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'sidebar_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']", 'unique': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'submission_requires_login': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'blank': 'True'}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'tier_name': ('django.db.models.fields.CharField', [], {'default': "'basic'", 'max_length': '255'}),
            'use_original_date': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'localtv.tierinfo': {
            'Meta': {'object_name': 'TierInfo'},
            'already_sent_tiers_compliance_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'already_sent_welcome_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'current_paypal_profile_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'free_trial_available': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'free_trial_started_on': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'free_trial_warning_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'fully_confirmed_tier_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_free_trial': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'inactive_site_warning_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'payment_due_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'payment_secret': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'should_send_welcome_email_on_paypal_event': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sitelocation': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['localtv.SiteLocation']", 'unique': 'True'}),
            'user_has_successfully_performed_a_paypal_transaction': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'video_allotment_warning_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'waiting_on_payment_until': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'localtv.video': {
            'Meta': {'ordering': "['-when_submitted']", 'object_name': 'Video'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'authored_set'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'calculated_source_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Category']", 'symmetrical': 'False', 'blank': 'True'}),
            'contact': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'embed_code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.Feed']", 'null': 'True', 'blank': 'True'}),
            'file_url': ('localtv.models.BitLyWrappingURLField', [], {'max_length': '200', 'blank': 'True'}),
            'file_url_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'file_url_mimetype': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'flash_enclosure_url': ('localtv.models.BitLyWrappingURLField', [], {'max_length': '200', 'blank': 'True'}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'has_thumbnail': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_featured': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'search': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.SavedSearch']", 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '400', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'video_service_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'video_service_user': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'blank': 'True'}),
            'website_url': ('localtv.models.BitLyWrappingURLField', [], {'max_length': '200', 'blank': 'True'}),
            'when_approved': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'when_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'when_published': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'when_submitted': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'localtv.watch': {
            'Meta': {'object_name': 'Watch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.Video']"})
        },
        'localtv.widgetsettings': {
            'Meta': {'object_name': 'WidgetSettings'},
            'bg_color': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'bg_color_editable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'border_color': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'border_color_editable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'css': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'css_editable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_thumbnail': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'icon_editable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'site': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sites.Site']", 'unique': 'True'}),
            'text_color': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'text_color_editable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'title_editable': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['localtv']