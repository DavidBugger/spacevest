from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_add_is_verified_to_bankaccount'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankaccount',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
    ]
