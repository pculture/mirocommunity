# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ContestSettings'
        db.create_table('contest_contestsettings', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('site', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['sites.Site'], unique=True)),
            ('max_votes', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('contest', ['ContestSettings'])

        # Adding M2M table for field categories on 'ContestSettings'
        db.create_table('contest_contestsettings_categories', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('contestsettings', models.ForeignKey(orm['contest.contestsettings'], null=False)),
            ('category', models.ForeignKey(orm['localtv.category'], null=False))
        ))
        db.create_unique('contest_contestsettings_categories', ['contestsettings_id', 'category_id'])

    def backwards(self, orm):
        # Deleting model 'ContestSettings'
        db.delete_table('contest_contestsettings')

        # Removing M2M table for field categories on 'ContestSettings'
        db.delete_table('contest_contestsettings_categories')

    models = {
        'contest.contestsettings': {
            'Meta': {'object_name': 'ContestSettings'},
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['localtv.Category']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_votes': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'site': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sites.Site']", 'unique': 'True'})
        },
        'localtv.category': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('slug', 'site'), ('name', 'site'))", 'object_name': 'Category'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_set'", 'null': 'True', 'to': "orm['localtv.Category']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['contest']