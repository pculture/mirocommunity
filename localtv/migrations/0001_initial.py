from south.db import db
from django.db import models
from localtv.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Video'
        db.create_table('localtv_video', (
            ('feed', orm['localtv.Video:feed']),
            ('when_approved', orm['localtv.Video:when_approved']),
            ('site', orm['localtv.Video:site']),
            ('has_thumbnail', orm['localtv.Video:has_thumbnail']),
            ('guid', orm['localtv.Video:guid']),
            ('id', orm['localtv.Video:id']),
            ('embed_code', orm['localtv.Video:embed_code']),
            ('file_url_length', orm['localtv.Video:file_url_length']),
            ('flash_enclosure_url', orm['localtv.Video:flash_enclosure_url']),
            ('when_submitted', orm['localtv.Video:when_submitted']),
            ('website_url', orm['localtv.Video:website_url']),
            ('status', orm['localtv.Video:status']),
            ('description', orm['localtv.Video:description']),
            ('last_featured', orm['localtv.Video:last_featured']),
            ('when_published', orm['localtv.Video:when_published']),
            ('openid_user', orm['localtv.Video:openid_user']),
            ('search', orm['localtv.Video:search']),
            ('name', orm['localtv.Video:name']),
            ('file_url_mimetype', orm['localtv.Video:file_url_mimetype']),
            ('file_url', orm['localtv.Video:file_url']),
            ('thumbnail_extension', orm['localtv.Video:thumbnail_extension']),
            ('thumbnail_url', orm['localtv.Video:thumbnail_url']),
        ))
        db.send_create_signal('localtv', ['Video'])
        
        # Adding model 'Category'
        db.create_table('localtv_category', (
            ('description', orm['localtv.Category:description']),
            ('parent', orm['localtv.Category:parent']),
            ('site', orm['localtv.Category:site']),
            ('id', orm['localtv.Category:id']),
            ('logo', orm['localtv.Category:logo']),
            ('slug', orm['localtv.Category:slug']),
            ('name', orm['localtv.Category:name']),
        ))
        db.send_create_signal('localtv', ['Category'])
        
        # Adding model 'SiteLocation'
        db.create_table('localtv_sitelocation', (
            ('status', orm['localtv.SiteLocation:status']),
            ('sidebar_html', orm['localtv.SiteLocation:sidebar_html']),
            ('footer_html', orm['localtv.SiteLocation:footer_html']),
            ('tagline', orm['localtv.SiteLocation:tagline']),
            ('about_html', orm['localtv.SiteLocation:about_html']),
            ('site', orm['localtv.SiteLocation:site']),
            ('frontpage_style', orm['localtv.SiteLocation:frontpage_style']),
            ('submission_requires_login', orm['localtv.SiteLocation:submission_requires_login']),
            ('display_submit_button', orm['localtv.SiteLocation:display_submit_button']),
            ('background', orm['localtv.SiteLocation:background']),
            ('logo', orm['localtv.SiteLocation:logo']),
            ('id', orm['localtv.SiteLocation:id']),
            ('css', orm['localtv.SiteLocation:css']),
        ))
        db.send_create_signal('localtv', ['SiteLocation'])
        
        # Adding model 'OpenIdUser'
        db.create_table('localtv_openiduser', (
            ('status', orm['localtv.OpenIdUser:status']),
            ('superuser', orm['localtv.OpenIdUser:superuser']),
            ('url', orm['localtv.OpenIdUser:url']),
            ('email', orm['localtv.OpenIdUser:email']),
            ('nickname', orm['localtv.OpenIdUser:nickname']),
            ('id', orm['localtv.OpenIdUser:id']),
        ))
        db.send_create_signal('localtv', ['OpenIdUser'])
        
        # Adding model 'SavedSearch'
        db.create_table('localtv_savedsearch', (
            ('query_string', orm['localtv.SavedSearch:query_string']),
            ('openid_user', orm['localtv.SavedSearch:openid_user']),
            ('when_created', orm['localtv.SavedSearch:when_created']),
            ('id', orm['localtv.SavedSearch:id']),
            ('site', orm['localtv.SavedSearch:site']),
        ))
        db.send_create_signal('localtv', ['SavedSearch'])
        
        # Adding model 'Tag'
        db.create_table('localtv_tag', (
            ('id', orm['localtv.Tag:id']),
            ('name', orm['localtv.Tag:name']),
        ))
        db.send_create_signal('localtv', ['Tag'])
        
        # Adding model 'Feed'
        db.create_table('localtv_feed', (
            ('status', orm['localtv.Feed:status']),
            ('openid_user', orm['localtv.Feed:openid_user']),
            ('last_updated', orm['localtv.Feed:last_updated']),
            ('name', orm['localtv.Feed:name']),
            ('feed_url', orm['localtv.Feed:feed_url']),
            ('webpage', orm['localtv.Feed:webpage']),
            ('site', orm['localtv.Feed:site']),
            ('etag', orm['localtv.Feed:etag']),
            ('when_submitted', orm['localtv.Feed:when_submitted']),
            ('auto_approve', orm['localtv.Feed:auto_approve']),
            ('id', orm['localtv.Feed:id']),
            ('description', orm['localtv.Feed:description']),
        ))
        db.send_create_signal('localtv', ['Feed'])
        
        # Adding model 'Author'
        db.create_table('localtv_author', (
            ('logo', orm['localtv.Author:logo']),
            ('id', orm['localtv.Author:id']),
            ('name', orm['localtv.Author:name']),
            ('site', orm['localtv.Author:site']),
        ))
        db.send_create_signal('localtv', ['Author'])
        
        # Adding model 'Watch'
        db.create_table('localtv_watch', (
            ('openid_user', orm['localtv.Watch:openid_user']),
            ('timestamp', orm['localtv.Watch:timestamp']),
            ('ip_address', orm['localtv.Watch:ip_address']),
            ('video', orm['localtv.Watch:video']),
            ('id', orm['localtv.Watch:id']),
        ))
        db.send_create_signal('localtv', ['Watch'])
        
        # Adding ManyToManyField 'Video.authors'
        db.create_table('localtv_video_authors', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('video', models.ForeignKey(orm.Video, null=False)),
            ('author', models.ForeignKey(orm.Author, null=False))
        ))
        
        # Adding ManyToManyField 'Video.categories'
        db.create_table('localtv_video_categories', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('video', models.ForeignKey(orm.Video, null=False)),
            ('category', models.ForeignKey(orm.Category, null=False))
        ))
        
        # Adding ManyToManyField 'Feed.auto_categories'
        db.create_table('localtv_feed_auto_categories', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('feed', models.ForeignKey(orm.Feed, null=False)),
            ('category', models.ForeignKey(orm.Category, null=False))
        ))
        
        # Adding ManyToManyField 'Video.tags'
        db.create_table('localtv_video_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('video', models.ForeignKey(orm.Video, null=False)),
            ('tag', models.ForeignKey(orm.Tag, null=False))
        ))
        
        # Adding ManyToManyField 'SiteLocation.admins'
        db.create_table('localtv_sitelocation_admins', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('sitelocation', models.ForeignKey(orm.SiteLocation, null=False)),
            ('openiduser', models.ForeignKey(orm.OpenIdUser, null=False))
        ))
        
        # Adding ManyToManyField 'Feed.auto_authors'
        db.create_table('localtv_feed_auto_authors', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('feed', models.ForeignKey(orm.Feed, null=False)),
            ('author', models.ForeignKey(orm.Author, null=False))
        ))
        
        # Creating unique_together for [name, site] on Author.
        db.create_unique('localtv_author', ['name', 'site_id'])
        
        # Creating unique_together for [name, site] on Category.
        db.create_unique('localtv_category', ['name', 'site_id'])
        
        # Creating unique_together for [name, site] on Feed.
        db.create_unique('localtv_feed', ['name', 'site_id'])
        
        # Creating unique_together for [feed_url, site] on Feed.
        db.create_unique('localtv_feed', ['feed_url', 'site_id'])
        
        # Creating unique_together for [slug, site] on Category.
        db.create_unique('localtv_category', ['slug', 'site_id'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'Video'
        db.delete_table('localtv_video')
        
        # Deleting model 'Category'
        db.delete_table('localtv_category')
        
        # Deleting model 'SiteLocation'
        db.delete_table('localtv_sitelocation')
        
        # Deleting model 'OpenIdUser'
        db.delete_table('localtv_openiduser')
        
        # Deleting model 'SavedSearch'
        db.delete_table('localtv_savedsearch')
        
        # Deleting model 'Tag'
        db.delete_table('localtv_tag')
        
        # Deleting model 'Feed'
        db.delete_table('localtv_feed')
        
        # Deleting model 'Author'
        db.delete_table('localtv_author')
        
        # Deleting model 'Watch'
        db.delete_table('localtv_watch')
        
        # Dropping ManyToManyField 'Video.authors'
        db.delete_table('localtv_video_authors')
        
        # Dropping ManyToManyField 'Video.categories'
        db.delete_table('localtv_video_categories')
        
        # Dropping ManyToManyField 'Feed.auto_categories'
        db.delete_table('localtv_feed_auto_categories')
        
        # Dropping ManyToManyField 'Video.tags'
        db.delete_table('localtv_video_tags')
        
        # Dropping ManyToManyField 'SiteLocation.admins'
        db.delete_table('localtv_sitelocation_admins')
        
        # Dropping ManyToManyField 'Feed.auto_authors'
        db.delete_table('localtv_feed_auto_authors')
        
        # Deleting unique_together for [name, site] on Author.
        db.delete_unique('localtv_author', ['name', 'site_id'])
        
        # Deleting unique_together for [name, site] on Category.
        db.delete_unique('localtv_category', ['name', 'site_id'])
        
        # Deleting unique_together for [name, site] on Feed.
        db.delete_unique('localtv_feed', ['name', 'site_id'])
        
        # Deleting unique_together for [feed_url, site] on Feed.
        db.delete_unique('localtv_feed', ['feed_url', 'site_id'])
        
        # Deleting unique_together for [slug, site] on Category.
        db.delete_unique('localtv_category', ['slug', 'site_id'])
        
    
    
    models = {
        'localtv.video': {
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Author']", 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Category']", 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'embed_code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.Feed']", 'null': 'True', 'blank': 'True'}),
            'file_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'file_url_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'file_url_mimetype': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'flash_enclosure_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'has_thumbnail': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_featured': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openid_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.OpenIdUser']", 'null': 'True', 'blank': 'True'}),
            'search': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.SavedSearch']", 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Tag']", 'blank': 'True'}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '400', 'blank': 'True'}),
            'website_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'when_approved': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'when_published': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'when_submitted': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'localtv.category': {
            'Meta': {'unique_together': "(('slug', 'site'), ('name', 'site'))"},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'child_set'", 'blank': 'True', 'null': 'True', 'to': "orm['localtv.Category']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'localtv.sitelocation': {
            'about_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.OpenIdUser']", 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'display_submit_button': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'footer_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'frontpage_style': ('django.db.models.fields.CharField', [], {'default': "'list'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'sidebar_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']", 'unique': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'submission_requires_login': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'})
        },
        'localtv.openiduser': {
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'unique': 'True'})
        },
        'localtv.tag': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'localtv.feed': {
            'Meta': {'unique_together': "(('feed_url', 'site'), ('name', 'site'))"},
            'auto_approve': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_authors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Author']", 'blank': 'True'}),
            'auto_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['localtv.Category']", 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'openid_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.OpenIdUser']", 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'status': ('django.db.models.fields.IntegerField', [], {}),
            'webpage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'when_submitted': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'localtv.author': {
            'Meta': {'unique_together': "(('name', 'site'),)"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"})
        },
        'localtv.watch': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'openid_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.OpenIdUser']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.Video']"})
        },
        'localtv.savedsearch': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'openid_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['localtv.OpenIdUser']", 'null': 'True', 'blank': 'True'}),
            'query_string': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'when_created': ('django.db.models.fields.DateTimeField', [], {})
        }
    }
    
    complete_apps = ['localtv']
