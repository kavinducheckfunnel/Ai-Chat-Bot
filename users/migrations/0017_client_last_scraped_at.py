from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_platformconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='last_scraped_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
