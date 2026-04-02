from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_client_portal_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='voice_input_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='client',
            name='image_input_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
