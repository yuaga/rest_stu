from django.db import models


class UserToken(models.Model):
    user = models.OneToOneField('UserInfo', on_delete=models.CASCADE)
    token = models.CharField(max_length=128)
    token_num = models.IntegerField(default=5)


class UserInfo(models.Model):
    user_type_choice = (
        ('1', '普通会员'),
        ('2', '白金会员'),
        ('3', '黄金会员'),
    )
    username = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=16)
    user_type = models.IntegerField(choices=user_type_choice)

