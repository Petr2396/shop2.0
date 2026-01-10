from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        # укажите последнюю миграцию
        ('orders', '0006_order_customer_alter_order_address_alter_order_phone'),
    ]
    
    operations = [
        migrations.AddField(
            model_name='order',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
    ]