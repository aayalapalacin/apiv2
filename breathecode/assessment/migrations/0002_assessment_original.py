# Generated by Django 3.2.4 on 2021-06-16 20:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='assessment',
            name='original',
            field=models.ForeignKey(
                blank=True,
                default=None,
                help_text=
                'If original is != None it means this particular assignment will become a translation of another (E.g: The spanish version of a quiz)',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='translations',
                to='assessment.assessment'),
        ),
    ]
