from django.db import models

# Create your models here.
class alpha(models.Model):

    tokenId = models.CharField(max_length=50)
    chainName = models.CharField(max_length=10)
    contractAddress = models.CharField(max_length=100)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=50)
    mulPoint = models.IntegerField()
    price = models.CharField(max_length=50)
    percentChange24h = models.CharField(max_length=50)
    volume24h = models.CharField(max_length=50)
    liquidity = models.CharField(max_length=50)


    def __str__(self):
        return self.symbol
    class Meta:
        db_table = "alpha"
        verbose_name = "alpha"
        verbose_name_plural = "alpha"