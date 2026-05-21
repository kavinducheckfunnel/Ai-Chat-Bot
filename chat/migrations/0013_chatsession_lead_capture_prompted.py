from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0012_add_llmcalllog'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='lead_capture_prompted',
            field=models.BooleanField(default=False),
        ),
    ]
