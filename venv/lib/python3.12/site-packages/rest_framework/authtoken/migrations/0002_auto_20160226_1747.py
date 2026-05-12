from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authtoken', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='token',
            options={'verbose_name_plural': 'Tokens', 'verbose_name': 'Token'},
        ),
        migrations.AlterField(
            model_name='token',
            name='created',
            field=models.DateTimeField(verbose_name='Created', auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='token',
            name='key',
            field=models.CharField(verbose_name='Key', max_length=40, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='token',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL, verbose_name='User', related_name='auth_token', on_delete=models.CASCADE),
        ),
    ]
