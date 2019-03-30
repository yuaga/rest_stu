from django.urls import path,re_path
from . import views

app_name = 'api'
urlpatterns = [
    path('index/', views.index),
    path('auth/', views.LoginView.as_view()),
    path('user_center/', views.UserCenter.as_view()),
    path('user_svip/', views.UserSVip.as_view()),
    path('page/', views.PageView.as_view()),
    path('page1/', views.Page1View.as_view({'get': 'list', 'post': 'create'})),
    # re_path(r'page1/(?P<pk>\d+)/$', views.Page1View.as_view({'get': 'retrieve', 'post': 'create'})),
    path('page1/<int:pk>/', views.Page1View.as_view({'get': 'retrieve', 'put':'update', 'delete':'destory', 'patch':'perform_update'})),
]