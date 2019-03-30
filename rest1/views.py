from django.http import JsonResponse, HttpResponse
from rest_framework import exceptions
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
import hashlib
import time
from .models import UserInfo, UserToken
from rest_framework.versioning import URLPathVersioning
from rest_framework.request import Request
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination, CursorPagination
from rest_framework.response import Response


# 实验一下SQL注入
from django.db import connection
def index(request):
    user_id = request.GET.get('user_id')
    if user_id:
        cursor = connection.cursor()
        cursor.execute("select id, username from rest1_userinfo where id=%s" %user_id)
        rows = cursor.fetchall()
        return HttpResponse(rows)


def md5(user):
    ctime = str(time.time())
    token = hashlib.md5()
    token.update(user.encode('utf-8'))
    token.update(ctime.encode('utf-8'))
    return token.hexdigest()

# 如果你不想让未登录的用户访问某些页面
# 那么就可以对未登录用户进行验证，下面是认证器，是否携带登录时产生的token码
class UserAuthentication(BaseAuthentication):

    def authenticate(self, request):
        # 提取token，
        token = request._request.GET.get('token')
        # 验证token是否正确
        token_obj = UserToken.objects.filter(token=token).first()
        if not token_obj:
                raise exceptions.AuthenticationFailed('用户未登录')
        else:
            # 下面的元组内的元素会分别赋值给 request.user request.auth
            return (token_obj.user, token_obj)


# 只有黄金会员权限访问
class UserPermission(BasePermission):

    message = '没有权限访问'

    def has_permission(self, request, view):
        # 只有登录后才可以访问的，所以先经过登录认证，这时可以从request.user获取用户
        user = request.user
        user_type = user.user_type
        if user_type == 3:
            return True
        else:
            # raise exceptions.PermissionDenied('没有权限访问')  这里最好不要这么写，因为验证失败，系统自己会抛出错误，定义一个message就好
            # if not permission.has_permission(request, self):  这里会用has_permission()返回的值进行判断
            # check_permissions()方法下的如果has_permission返回False，会执行permission_denied()函数，并判断是不是定义了message
            # 看源码分析
            return False


class UserThrottle(SimpleRateThrottle):
    scope = 'stu'
    def get_cache_key(self, request, view):
        return self.get_ident(request)


# 先写一个rest framework登录视图
class LoginView(APIView):

    def post(self, request, *args, **kwargs):
        # 定义一个result，返回给前端
        restful = {'code': 100, 'message': None, 'data': None}
        username = request._request.POST.get('username')
        password = request._request.POST.get('password')
        try:
            user_obj = UserInfo.objects.get(username=username, password=password)
            if user_obj:
                token = md5(username)
                # 如果用户登录，创建一个token值，第一次登录就创建，否则就是更新
                UserToken.objects.update_or_create(user=user_obj, defaults={'token': token})
                restful['code'] = 200
                restful['message'] = "登录成功"
            else:
                restful['code'] = 400
                restful['message'] = "用户输入错误"
        except Exception as e:
            pass
        return JsonResponse(restful)


# 再写一个类视图，用来限制未登录的用户访问 个人中心吧
class UserCenter(APIView):
    authentication_classes=[UserAuthentication,]
    def get(self, request, *args, **kwargs):
        return HttpResponse('欢迎来到个人中心')

    def post(self, request, *args, **kwargs):
        return HttpResponse('post')


class UserSVip(APIView):

    authentication_classes = [UserAuthentication,]
    permission_classes = [UserPermission,]
    throttle_classes = [UserThrottle,]

    def get(self, request, *args, **kwargs):
        return HttpResponse('这是只有黄金会员才能访问的页面。。。')

    def post(self, request, *args, **kwargs):
        pass


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInfo
        fields = '__all__'


# 查第n页，每页显示多少条数据
class MyPageNumberPagination(PageNumberPagination):
    # 每页多少条数据，比如说三条
    page_size = 1
    # 表示get传参时自定义每页显示多少数据， 比如/?page=2&size=4  显示第二页并显示4条数据
    # 可以定义为size，自定义每页显示多少数据
    page_size_query_param = 'size'
    # 每页最多显示5条数据
    max_page_size = 5  # page_size_query_param和本条可以不用设置，直接按定义的显示多少条
    # 查询页码的key  ?page=2  查询第二页的数据
    page_query_param = 'page'


# 分页，在n个位置，向后查看n条数据
class MyPageNumberPagination1(LimitOffsetPagination):

    # 默认向后取3条数据 /?offset=0&limit=2 就是从第1条数据开始往后显示2条，就是显示id=1,2的数据
    default_limit = 3
    limit_query_param = 'limit'
    # 默认的位置，0表示从数据的一个数据开始显示，那么1就表示从第2个数据开始显示
    offset_query_param = 'offset'
    # 设置最大往后取多少条
    max_limit = 5


class MyPageNumberPagination2(CursorPagination):
    # 当前游标的位置，对页码进行加密，用户无法恶意传参
    cursor_query_param = 'cursor'

    page_size = 2  # 默认每页显示的数量

    ordering = '-created'  # 排序顺序
    page_size_query_param = None  # 可以定义为size，自定义每页显示多少数据
    max_page_size = None  # 定义每页最大的显示数量

class PageView(APIView):

    def get(self, request, *args, **kwargs):
        users = UserInfo.objects.all()
        # 实列化
        pager = MyPageNumberPagination()
        # 获取分页后的数据
        pg = pager.paginate_queryset(queryset=users, request=request, view=self)
        # 对数据序列化
        ser = PageSerializer(instance=pg, many = True)

        # get_paginated_response()方法，可以显示多条数据，如下
        # return Response(OrderedDict([
        #     ('count', self.page.paginator.count),  # 总共多少条数据
        #     ('next', self.get_next_link()),  # 下一页的url
        #     ('previous', self.get_previous_link()),  # 上一页的url
        #     ('results', data)  # 当前页的结果
        # ]))
        return Response(ser.data)

'''
ModelViewSet 继承了多个类，可以实现多种请求方法,这样只需要配置分页，序列化，写好url就OK了
1.url两种写法，as_view({'get': 'list'})  当是get请求时，执行ModelViewSet的父类mixins.ListModelMixin中的list方法，我们不用写get()方法了，全部写好的
2.配置两个url，
    path('page1/', views.Page1View.as_view({'get': 'list', 'post': 'create'})),  
    #re_path(r'page1/(?P<pk>\d+)/$', views.Page1View.as_view({'get': 'retrieve''})), django2.0中1.x版本的url写法，跟下面这个一样的
    path('page1/<int:pk>/', views.Page1View.as_view({'get': 'retrieve', 'put':'update', 'delete':'destory', 'patch':'perform_update'})), get 实现获取单个数据， put 全部更新 patch局部更新 delete删除
'''
from rest_framework.viewsets import ModelViewSet
class Page1View(ModelViewSet):
    queryset = UserInfo.objects.all()
    pagination_class = MyPageNumberPagination
    serializer_class = PageSerializer



from django.db import connection

def dbtest(request):
    user_id = request.GET.get('user_id')
    cursor = connection.cursor()
    sql = "select id, username from front_user where %s"
    cursor.execute(sql, (user_id,))
    rows = cursor.fetchall()
    return rows