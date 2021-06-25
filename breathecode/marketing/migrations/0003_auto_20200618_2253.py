# Generated by Django 3.0.7 on 2020-06-18 22:53

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0002_auto_20200618_2235'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormEntry',
            fields=[
                ('id',
                 models.AutoField(auto_created=True,
                                  primary_key=True,
                                  serialize=False,
                                  verbose_name='ID')),
                ('first_name', models.CharField(max_length=150)),
                ('last_name',
                 models.CharField(default=None, max_length=150, null=True)),
                ('email', models.CharField(max_length=150)),
                ('phone',
                 phonenumber_field.modelfields.PhoneNumberField(blank=True,
                                                                default=None,
                                                                max_length=128,
                                                                null=True,
                                                                region=None)),
                ('course',
                 models.CharField(default=None, max_length=30, null=True)),
                ('client_comments',
                 models.CharField(default=None, max_length=250, null=True)),
                ('language', models.CharField(max_length=2)),
                ('utm_url', models.CharField(max_length=250)),
                ('utm_medium',
                 models.CharField(default=None, max_length=2, null=True)),
                ('utm_campaign',
                 models.CharField(default=None, max_length=2, null=True)),
                ('street_address',
                 models.CharField(default=None, max_length=250, null=True)),
                ('country', models.CharField(max_length=30)),
                ('city', models.CharField(max_length=30)),
                ('latitude',
                 models.DecimalField(decimal_places=6,
                                     default=None,
                                     max_digits=9,
                                     null=True)),
                ('longitude',
                 models.DecimalField(decimal_places=6,
                                     default=None,
                                     max_digits=9,
                                     null=True)),
                ('state',
                 models.CharField(default=None, max_length=30, null=True)),
                ('zip_code', models.IntegerField(default=None, null=True)),
                ('storage_status',
                 models.CharField(choices=[('PENDING', 'Pending'),
                                           ('PERSISTED', 'Persisted')],
                                  default='PENDING',
                                  max_length=15)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.DeleteModel(name='Contact', ),
    ]
