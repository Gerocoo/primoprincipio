import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AlertThreshold',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('threshold', models.FloatField()),
                ('email', models.EmailField(max_length=254)),
                ('active', models.BooleanField(default=True)),
                ('last_triggered_doy', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='ModelRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_date', models.DateField()),
                ('first_doy', models.IntegerField()),
                ('last_doy', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='EventSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doy', models.IntegerField()),
                ('event_index', models.IntegerField()),
                ('x_value', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='snapshots', to='simulation.modelrun')),
            ],
            options={
                'ordering': ['doy', 'event_index'],
                'unique_together': {('run', 'doy', 'event_index')},
            },
        ),
    ]
