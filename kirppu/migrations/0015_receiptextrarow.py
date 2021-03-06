# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-01-01 18:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kirppu', '0014_add_receipt_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReceiptExtraRow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('PRO', 'Provision'), ('PRO_FIX', 'Provision balancing')], max_length=8)),
                ('value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extra_rows', to='kirppu.Receipt')),
            ],
        ),
    ]
