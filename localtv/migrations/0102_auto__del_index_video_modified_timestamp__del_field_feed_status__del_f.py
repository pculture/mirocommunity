# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.db.utils import DatabaseError


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Feed', fields ['feed_url', 'site']
        try:
            db.delete_unique('localtv_feed', ['feed_url', 'site_id'])
        except DatabaseError:
            pass

        # Removing index on 'Video', fields ['modified_timestamp']
        try:
            db.delete_index('localtv_video', ['modified_timestamp'])
        except DatabaseError:
            pass

        # Deleting field 'Feed.status'
        db.delete_column('localtv_feed', 'status')

        # Deleting field 'Feed.last_updated'
        db.delete_column('localtv_feed', 'last_updated')

        # Deleting field 'Feed.user'
        db.delete_column('localtv_feed', 'user_id')

        # Adding field 'Feed.modified_timestamp'
        db.add_column('localtv_feed', 'modified_timestamp',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, default=datetime.datetime(2013, 7, 16, 0, 0), blank=True),
                      keep_default=False)

        # Adding field 'Feed.moderate_imported_videos'
        db.add_column('localtv_feed', 'moderate_imported_videos',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Feed.disable_imports'
        db.add_column('localtv_feed', 'disable_imports',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Deleting field 'SavedSearch.user'
        db.delete_column('localtv_savedsearch', 'user_id')

        # Adding field 'SavedSearch.modified_timestamp'
        db.add_column('localtv_savedsearch', 'modified_timestamp',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, default=datetime.datetime(2013, 7, 16, 0, 0), blank=True),
                      keep_default=False)

        # Adding field 'SavedSearch.moderate_imported_videos'
        db.add_column('localtv_savedsearch', 'moderate_imported_videos',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'SavedSearch.disable_imports'
        db.add_column('localtv_savedsearch', 'disable_imports',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        db.rename_column('localtv_feed', 'feed_url', 'original_url')
        db.rename_column('localtv_feed', 'webpage', 'external_url')
        db.rename_column('localtv_feed', 'when_submitted', 'created_timestamp')
        db.rename_column('localtv_savedsearch', 'when_created', 'created_timestamp')

    def backwards(self, orm):
        # Adding index on 'Video', fields ['modified_timestamp']
        db.create_index('localtv_video', ['modified_timestamp'])

        db.rename_column('localtv_feed', 'original_url', 'feed_url')
        db.rename_column('localtv_feed', 'external_url', 'webpage')
        db.rename_column('localtv_feed', 'created_timestamp', 'when_submitted')
        db.rename_column('localtv_savedsearch', 'created_timestamp', 'when_created')

        # Adding field 'Feed.status'
        db.add_column('localtv_feed', 'status',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'Feed.last_updated'
        db.add_column('localtv_feed', 'last_updated',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(1972, 1, 1, 0, 0)),
                      keep_default=False)

        # Adding field 'Feed.user'
        db.add_column('localtv_feed', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Feed.modified_timestamp'
        db.delete_column('localtv_feed', 'modified_timestamp')

        # Deleting field 'Feed.moderate_imported_videos'
        db.delete_column('localtv_feed', 'moderate_imported_videos')

        # Deleting field 'Feed.disable_imports'
        db.delete_column('localtv_feed', 'disable_imports')

        # Adding unique constraint on 'Feed', fields ['feed_url', 'site']
        db.create_unique('localtv_feed', ['feed_url', 'site_id'])

        # Adding field 'SavedSearch.user'
        db.add_column('localtv_savedsearch', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)

        # Deleting field 'SavedSearch.modified_timestamp'
        db.delete_column('localtv_savedsearch', 'modified_timestamp')

        # Deleting field 'SavedSearch.moderate_imported_videos'
        db.delete_column('localtv_savedsearch', 'moderate_imported_videos')

        # Deleting field 'SavedSearch.disable_imports'
        db.delete_column('localtv_savedsearch', 'disable_imports')


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
            'Meta': {'unique_together': "(('slug', 'site'), ('name', 'site'))", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_set'", 'null': 'True', 'to': "orm['localtv.Category']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'localtv.feed': {
            'Meta': {'object_name': 'Feed'},
            'auto_approve': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'auto_feed_set'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'auto_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Category']", 'symmetrical': 'False', 'blank': 'True'}),
            'auto_update': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'calculated_source_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disable_imports': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'external_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderate_imported_videos': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'original_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'})
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
            'source_import': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'indexes'", 'to': "orm['localtv.FeedImport']"}),
            'video': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['localtv.Video']", 'unique': 'True'})
        },
        'localtv.savedsearch': {
            'Meta': {'object_name': 'SavedSearch'},
            'auto_approve': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'auto_savedsearch_set'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'auto_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Category']", 'symmetrical': 'False', 'blank': 'True'}),
            'auto_update': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'disable_imports': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderate_imported_videos': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'query_string': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'})
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
            'source_import': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'indexes'", 'to': "orm['localtv.SearchImport']"}),
            'video': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['localtv.Video']", 'unique': 'True'})
        },
        'localtv.sitesettings': {
            'Meta': {'object_name': 'SiteSettings'},
            'about_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'admin_for'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'comments_required_login': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'css': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'display_submit_button': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'footer_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'hide_get_started': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'playlists_enabled': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'screen_all_comments': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'sidebar_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'site': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sites.Site']", 'unique': 'True'}),
            'submission_requires_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'submission_requires_login': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '4096', 'blank': 'True'}),
            'use_original_date': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'localtv.video': {
            'Meta': {'ordering': "['-created_timestamp']", 'object_name': 'Video'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'authored_set'", 'blank': 'True', 'to': "orm['auth.User']"}),
            'calculated_source_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Category']", 'symmetrical': 'False', 'blank': 'True'}),
            'created_timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'embed_code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'external_published_datetime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'external_thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '400', 'blank': 'True'}),
            'external_url': ('django.db.models.fields.URLField', [], {'max_length': '2048', 'blank': 'True'}),
            'external_user': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'external_user_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'featured_datetime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.Feed']", 'null': 'True', 'blank': 'True'}),
            'flash_enclosure_url': ('django.db.models.fields.URLField', [], {'max_length': '2048', 'blank': 'True'}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'original_url': ('django.db.models.fields.URLField', [], {'max_length': '2048', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'owner_email': ('django.db.models.fields.EmailField', [], {'max_length': '250', 'blank': 'True'}),
            'owner_session': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sessions.Session']", 'null': 'True', 'blank': 'True'}),
            'published_datetime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'search': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.SavedSearch']", 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'unpublished'", 'max_length': '16'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'})
        },
        'localtv.videofile': {
            'Meta': {'object_name': 'VideoFile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mimetype': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '2048'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['localtv.Video']"})
        },
        'localtv.watch': {
            'Meta': {'object_name': 'Watch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
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
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'icon_editable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'site': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sites.Site']", 'unique': 'True'}),
            'text_color': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'text_color_editable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'title_editable': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'sessions.session': {
            'Meta': {'object_name': 'Session', 'db_table': "'django_session'"},
            'expire_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'session_data': ('django.db.models.fields.TextField', [], {}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'tagging.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'tagging.taggeditem': {
            'Meta': {'unique_together': "(('tag', 'content_type', 'object_id'),)", 'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['tagging.Tag']"})
        }
    }

    complete_apps = ['localtv']