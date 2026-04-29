from django.db import migrations
import cloudinary.models


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0002_alter_doctor_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doctor',
            name='photo',
            field=cloudinary.models.CloudinaryField('image', blank=True, max_length=255, null=True, verbose_name='Фото'),
        ),
    ]
