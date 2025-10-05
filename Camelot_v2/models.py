from django.db import models

# Create your models here.

class Camelot(models.Model):
    pair_address = models.CharField(max_length=50, unique=True)
    pair_name = models.CharField(max_length=100)
    token0_name = models.CharField(max_length=50)
    token1_name = models.CharField(max_length=50)
    # uint112 最大 34 位，这里留冗余
    token0_reserve = models.DecimalField(max_digits=40, decimal_places=0)
    token1_reserve = models.DecimalField(max_digits=40, decimal_places=0)
    token1FeePercent = models.DecimalField(max_digits=40, decimal_places=10, default=0)
    token0FeePercent = models.DecimalField(max_digits=40, decimal_places=10, default=0)
    token0_decimals = models.IntegerField()
    token1_decimals = models.IntegerField()
    block_timestamp_last = models.BigIntegerField(default=0)
    exchange_rate = models.JSONField(null=True, blank=True)
    token0_address = models.CharField(max_length=50,default='None')  # 新增字段
    token1_address = models.CharField(max_length=50, default='None')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'camelot'